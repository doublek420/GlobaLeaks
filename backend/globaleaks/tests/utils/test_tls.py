import os

from twisted.trial.unittest import TestCase

from globaleaks.models.config import PrivateFactory
from globaleaks.orm import transact
from globaleaks.utils import tls

from globaleaks.tests import helpers

class TestKeyGen(TestCase):
    def test_dh_params(self):
        pass


def get_valid_setup():
    test_data_dir = os.path.join(helpers.DATA_DIR, 'https')

    valid_setup_files = {
        'key': 'priv_key.pem',
        'cert': 'cert.pem',
        'chain': 'chain.pem',
        'dh_params': 'dh_params.pem'
    }

    return {
        k : open(os.path.join(test_data_dir, 'valid', fname), 'r').read() \
            for k, fname in valid_setup_files.iteritems()
    }

@transact
def commit_valid_config(store):
    cfg = get_valid_setup()

    priv_fact = PrivateFactory(store, 1)
    priv_fact.set_val('https_dh_params', cfg['dh_params'])
    priv_fact.set_val('https_priv_key', cfg['key'])
    priv_fact.set_val('https_cert', cfg['cert'])
    priv_fact.set_val('https_chain', cfg['chain'])
    priv_fact.set_val('https_enabled', True)


class TestObjectValidators(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestObjectValidators, self).__init__(*args, **kwargs)
        self.test_data_dir = os.path.join(helpers.DATA_DIR, 'https')

        self.invalid_files = [
            'empty.txt',
            # Invalid pem string
            'noise.pem',
            # Raw bytes
            'bytes.out',
            # A certificate signing request
            'random_csr.pem',
            # Mangled ASN.1 RSA key
            'garbage_key.pem',
            # DER formatted key
            'rsa_key.der',
            # PKCS8 encrypted private key
            'rsa_key_monalisa_pass.pem'
        ]

        self.valid_setup = get_valid_setup()

    def setUp(self):
        self.cfg = {
            'key': '',
            'cert': '',
            'chain': '',
            'dh_params': '',
            'ssl_intermediate': '',
            'https_enabled': False,
        }

    def test_private_key_invalid(self):
        pkv = tls.PrivKeyValidator()

        self.cfg['ssl_dh'] = self.valid_setup['dh_params']

        for fname in self.invalid_files:
            p = os.path.join(self.test_data_dir, 'invalid', fname)
            with open(p, 'r') as f:
                self.cfg['ssl_key'] = f.read()
            ok, err = pkv.validate(self.cfg)
            self.assertFalse(ok)
            self.assertIsNotNone(err)

    def test_private_key_valid(self):
        pkv = tls.PrivKeyValidator()

        good_keys = [
            'priv_key.pem'
        ]

        self.cfg['ssl_dh'] = self.valid_setup['dh_params']

        for fname in good_keys:
            p = os.path.join(self.test_data_dir, 'valid', fname)
            with open(p, 'r') as f:
                self.cfg['ssl_key'] = f.read()
            ok, err = pkv.validate(self.cfg)
            self.assertTrue(ok)
            self.assertIsNone(err)

    def test_cert_invalid(self):
        crtv = tls.CertValidator()

        self.cfg['ssl_dh'] = self.valid_setup['dh_params']
        self.cfg['ssl_key'] = self.valid_setup['key']

        for fname in self.invalid_files:
            p = os.path.join(self.test_data_dir, 'invalid', fname)
            with open(p, 'r') as f:
                self.cfg['ssl_cert'] = f.read()
            ok, err = crtv.validate(self.cfg)
            self.assertFalse(ok)
            self.assertIsNotNone(err)

    def test_cert_valid(self):
        crtv = tls.CertValidator()

        good_certs = [
            'cert.pem'
        ]

        self.cfg['ssl_dh'] = self.valid_setup['dh_params']
        self.cfg['ssl_key'] = self.valid_setup['key']

        for fname in good_certs:
            p = os.path.join(self.test_data_dir, 'valid', fname)
            with open(p, 'r') as f:
                self.cfg['ssl_cert'] = f.read()
            ok, err = crtv.validate(self.cfg)
            self.assertTrue(ok)
            self.assertIsNone(err)

    def test_chain_invalid(self):
        chn_v = tls.ChainValidator()

        self.cfg['ssl_dh'] = self.valid_setup['dh_params']
        self.cfg['ssl_key'] = self.valid_setup['key']
        self.cfg['ssl_cert'] = self.valid_setup['cert']

        exceptions_from_validation = {'empty.txt'}

        for fname in self.invalid_files:
            p = os.path.join(self.test_data_dir, 'invalid', fname)
            with open(p, 'r') as f:
                self.cfg['ssl_intermediate'] = f.read()
            ok, err = chn_v.validate(self.cfg)
            if not fname in exceptions_from_validation:
                self.assertFalse(ok)
                self.assertIsNotNone(err)
            else:
                self.assertTrue(ok)
                self.assertIsNone(err)

    def test_chain_valid(self):
        chn_v = tls.ChainValidator()

        self.cfg['ssl_dh'] = self.valid_setup['dh_params']
        self.cfg['ssl_key'] = self.valid_setup['key']
        self.cfg['ssl_cert'] = self.valid_setup['cert']

        p = os.path.join(self.test_data_dir, 'valid', 'chain.pem')
        with open(p, 'r') as f:
            self.cfg['ssl_intermediate'] = f.read()

        ok, err = chn_v.validate(self.cfg)
        self.assertTrue(ok)
        self.assertIsNone(err)
