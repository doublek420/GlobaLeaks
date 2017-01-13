import unittest
import os

from twisted.internet.defer import inlineCallbacks
from OpenSSL import crypto, SSL

from globaleaks.handlers.admin.config import tls, http_master
from globaleaks.tests import helpers


class TestCryptoFuncs(unittest.TestCase):

    def test_it_all(self):
        key_pair = tls.gen_RSA_key()

        d = {
         'CN': 'fakedom.blah.blah',
         'O': 'widgets-R-us',
        }

        csr = tls.gen_x509_csr(key_pair, d)
        pem_csr = crypto.dump_certificate_request(SSL.FILETYPE_PEM, csr)
        #print(pem_csr)

class TestHTTPSWorkers(unittest.TestCase):

    def test_launch_workers(self):
        d = {
            'cert': '',
            #'chain': '',
            #'dh': '',
            'priv_key': '',
        }

        for key in d.keys():
            with open(os.path.join(helpers.KEYS_PATH, 'https', key+'.pem')) as f:
                d[key] = f.read()

        res = http_master.launch_workers({}, d['priv_key'], d['cert'], '', '')
        import time; time.sleep(30)


class TestCertFileHandler(helpers.TestHandlerWithPopulatedDB):
    
    _handler = tls.CertFileHandler

    def test_post(self):
        # TODO TODO TODO 
        handler = self.request(d, role='admin')
        res = handler.post()
        # TODO TODO TODO



class TestCSRHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = tls.CSRConfigHandler

    @inlineCallbacks
    def test_post(self):
        d = {
           'commonname': 'notreal.ns.com',
           'country': 'IT',
           'province': 'regione',
           'city': 'citta',
           'company': 'azienda',
           'department': 'reparto',
           'email': 'indrizzio@email',
        }

        handler = self.request(d, role='admin')
        res = yield handler.post()

        csr_pem = self.responses[0]['csr_txt']

        pem_csr = crypto.load_certificate_request(SSL.FILETYPE_PEM, csr_pem)

        self.assertIn(('CN', 'notreal.ns.com'), 
                      pem_csr.get_subject().get_components())
                      
        # TODO assert CSR comes out all good
