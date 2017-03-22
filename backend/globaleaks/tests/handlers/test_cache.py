# -*- coding: utf-8 -*-
from twisted.internet.defer import inlineCallbacks

from globaleaks.orm import transact
from globaleaks.rest.apicache import GLApiCache
from globaleaks.tests import helpers


class TestGLApiCache(helpers.TestGL):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGL.setUp(self)

        GLApiCache.invalidate_all()
        GLApiCache.add_tenant(1)

    @staticmethod
    @transact
    def mario(store, arg1, arg2, arg3):
        return arg1 + " " + arg2 + " " + arg3

    @inlineCallbacks
    def test_get(self):
        self.assertTrue("passante_di_professione" not in GLApiCache.per_tenant_cache[1])
        pdp_it = yield GLApiCache.get(1, "passante_di_professione", "it", self.mario, "come", "una", "catapulta!")
        pdp_en = yield GLApiCache.get(1, "passante_di_professione", "en", self.mario, "like", "a", "catapult!")
        self.assertTrue("passante_di_professione" in GLApiCache.per_tenant_cache[1])
        self.assertTrue("it" in GLApiCache.per_tenant_cache[1]['passante_di_professione'])
        self.assertTrue("en" in GLApiCache.per_tenant_cache[1]['passante_di_professione'])
        self.assertEqual(pdp_it, "come una catapulta!")
        self.assertEqual(pdp_en, "like a catapult!")

    @inlineCallbacks
    def test_set(self):
        self.assertTrue("passante_di_professione" not in GLApiCache.per_tenant_cache[1])
        pdp_it = yield GLApiCache.get(1, "passante_di_professione", "it", self.mario, "come", "una", "catapulta!")
        self.assertTrue("passante_di_professione" in GLApiCache.per_tenant_cache[1])
        self.assertTrue(pdp_it == "come una catapulta!")
        yield GLApiCache.set(1, "passante_di_professione", "it", "ma io ho visto tutto!")
        self.assertTrue("passante_di_professione" in GLApiCache.per_tenant_cache[1])
        pdp_it = yield GLApiCache.get(1, "passante_di_professione", "it", self.mario, "already", "cached")
        self.assertEqual(pdp_it, "ma io ho visto tutto!")

    @inlineCallbacks
    def test_invalidate(self):
        self.assertTrue("passante_di_professione" not in GLApiCache.per_tenant_cache[1])
        pdp_it = yield GLApiCache.get(1, "passante_di_professione", "it", self.mario, "come", "una", "catapulta!")
        self.assertTrue("passante_di_professione" in GLApiCache.per_tenant_cache[1])
        self.assertEqual(pdp_it, "come una catapulta!")
        yield GLApiCache.invalidate(1, "passante_di_professione")
        self.assertTrue("passante_di_professione" not in GLApiCache.per_tenant_cache[1])
