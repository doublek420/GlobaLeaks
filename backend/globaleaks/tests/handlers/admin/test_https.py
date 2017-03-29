import os

import twisted
from twisted.internet.defer import inlineCallbacks
from OpenSSL import crypto, SSL

from globaleaks.handlers.admin import https
from globaleaks.models.config import PrivateFactory
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.settings import GLSettings

from globaleaks.tests import helpers
from globaleaks.tests.utils import test_tls


@transact
def set_dh_params(store, dh_params):
    PrivateFactory(store, 1).set_val('https_dh_params', dh_params)


class TestFileHandler(helpers.TestHandler):
    _handler = https.FileHandler

    @inlineCallbacks
    def setUp(self):
        yield super(TestFileHandler, self).setUp()

        self.valid_setup = test_tls.get_valid_setup()
        yield set_dh_params(self.valid_setup['dh_params'])

    @inlineCallbacks
    def is_set(self, name, is_set):
        handler = self.request(role='admin', handler_cls=https.ConfigHandler)

        yield handler.get()
        resp = self.responses[-1]

        self.assertEqual(resp['files'][name]['set'], is_set)

    @transact
    def set_enabled(self, store):
        PrivateFactory(store, 1).set_val('https_enabled', True)
        GLSettings.memory_copy.private.https_enabled = True

    @inlineCallbacks
    def test_priv_key_file(self):
        n = 'priv_key'

        yield self.is_set(n, False)

        # Try to upload an invalid key
        bad_key = 'donk donk donk donk donk donk'
        handler = self.request({'name': 'priv_key', 'content': bad_key}, role='admin')
        yield self.assertFailure(handler.post(n), errors.ValidationError)

        # Upload a valid key
        good_key = self.valid_setup['key']
        handler = self.request({'name': 'priv_key', 'content': good_key}, role='admin')
        yield handler.post(n)
        yield self.is_set(n, True)

        was_generated = self.responses[-1]['files']['priv_key']['gen']
        self.assertFalse(was_generated)

        handler = self.request(role='admin')
        yield self.assertFailure(handler.get(n), errors.MethodNotImplemented)

        # Test key generation
        yield handler.put(n)
        yield self.is_set(n, True)

        was_generated = self.responses[-1]['files']['priv_key']['gen']
        self.assertTrue(was_generated)

        # Try delete actions
        yield handler.delete(n)
        yield self.is_set(n, False)

    @inlineCallbacks
    def test_cert_file(self):
        n = 'cert'

        yield self.is_set(n, False)
        yield https.PrivKeyFileRes.create_file(self.valid_setup['key'])

        # Test bad cert
        body = {'name': 'cert', 'content': 'bonk bonk bonk'}
        handler = self.request(body, role='admin')
        yield self.assertFailure(handler.post(n), errors.ValidationError)

        # Upload a valid cert
        body = {'name': 'cert', 'content': self.valid_setup[n]}
        handler = self.request(body, role='admin')
        yield handler.post(n)
        yield self.is_set(n, True)

        handler = self.request(role='admin')
        yield handler.get(n)
        content = self.responses[-1]
        self.assertEqual(content, self.valid_setup[n])

        # Finally delete the cert
        yield handler.delete(n)
        yield self.is_set(n, False)

    @inlineCallbacks
    def test_chain_file(self):
        n = 'chain'

        yield self.is_set(n, False)
        yield https.PrivKeyFileRes.create_file(self.valid_setup['key'])
        yield https.CertFileRes.create_file(self.valid_setup['cert'])

        body = {'name': 'chain', 'content': self.valid_setup[n]}
        handler = self.request(body, role='admin')

        yield handler.post(n)
        yield self.is_set(n, True)

        handler = self.request(role='admin')
        yield handler.get(n)
        content = self.responses[-1]
        self.assertEqual(content, self.valid_setup[n])

        yield handler.delete(n)
        yield self.is_set(n, False)

    @inlineCallbacks
    def test_file_res_disabled(self):
        yield self.set_enabled()

        handler = self.request(role='admin')
        for n in ['priv_key', 'cert', 'chain', 'csr']:
            self.assertRaises(errors.FailedSanityCheck, handler.delete, n)
            self.assertRaises(errors.FailedSanityCheck, handler.put, n)
            handler = self.request({'name': n, 'content':''}, role='admin')
            self.assertRaises(errors.FailedSanityCheck, handler.post, n)
            self.assertRaises(errors.FailedSanityCheck, handler.get, n)


class TestConfigHandler(helpers.TestHandler):
    _handler = https.ConfigHandler

    @inlineCallbacks
    def test_all_methods(self):
        valid_setup = test_tls.get_valid_setup()

        yield set_dh_params(valid_setup['dh_params'])
        yield https.PrivKeyFileRes.create_file(valid_setup['key'])
        yield https.CertFileRes.create_file(valid_setup['cert'])
        yield https.ChainFileRes.create_file(valid_setup['chain'])

        handler = self.request(role='admin')

        yield handler.get()
        self.assertTrue(len(self.responses[-1]['status']['msg']) > 0)

        # Config is ready to go. So launch the subprocesses.
        yield handler.post()
        yield handler.get()
        self.assertTrue(self.responses[-1]['enabled'])

        self.test_reactor.pump([50])

        # TODO improve resilience of shutdown. The child processes will complain
        # loudly as they die.
        yield handler.put()
        yield handler.get()
        self.assertFalse(self.responses[-1]['enabled'])


class TestCSRHandler(helpers.TestHandler):
    _handler = https.CSRFileHandler

    @inlineCallbacks
    def test_post(self):
        n = 'csr'

        valid_setup = test_tls.get_valid_setup()
        yield set_dh_params(valid_setup['dh_params'])
        yield https.PrivKeyFileRes.create_file(valid_setup['key'])

        d = {
           'commonname': 'notreal.ns.com',
           'country': 'it',
           'province': 'regione',
           'city': 'citta',
           'company': 'azienda',
           'department': 'reparto',
           'email': 'indrizzio@email',
        }

        body = {'name': 'csr', 'content': d}
        handler = self.request(body, role='admin')
        yield handler.post(n)

        yield handler.get(n)

        csr_pem = self.responses[-1]

        pem_csr = crypto.load_certificate_request(SSL.FILETYPE_PEM, csr_pem)

        comps = pem_csr.get_subject().get_components()
        self.assertIn(('CN', 'notreal.ns.com'), comps)
        self.assertIn(('C', 'IT'), comps)
        self.assertIn(('L', 'citta'), comps)
