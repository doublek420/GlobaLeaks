# -*- coding: utf-8 -*-
#
# admin/lang
#  **************
#
# Backend supports for jQuery File Uploader, and implementation of the
# file language statically uploaded by the Admin

# This code differs from handlers/file.py because files here are not tracked in the DB

from __future__ import with_statement

import json

from storm.expr import And
from twisted.internet.defer import inlineCallbacks

from globaleaks.models import CustomTexts
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact
from globaleaks.rest.apicache import GLApiCache


@transact
def get_custom_texts(store, tid, lang):
    texts = store.find(CustomTexts, And(CustomTexts.lang == lang,
                                        CustomTexts.tid == tid)).one()
    return texts.texts if texts is not None else {}


@transact
def update_custom_texts(store, tid, lang, texts):
    custom_texts = store.find(CustomTexts, And(CustomTexts.lang == unicode(lang),
                                               CustomTexts.tid == tid)).one()
    if custom_texts is None:
        custom_texts = CustomTexts()
        custom_texts.lang = lang
        custom_texts.tid = tid
        store.add(custom_texts)

    custom_texts.texts = texts


@transact
def delete_custom_texts(store, tid, lang):
    custom_texts = store.find(CustomTexts, And(CustomTexts.lang == unicode(lang),
                                               CustomTexts.tid == tid)).one()
    if custom_texts is not None:
        store.remove(custom_texts)


class AdminL10NHandler(BaseHandler):
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def get(self, lang):
        custom_texts = yield get_custom_texts(self.request.current_tenant_id, lang)

        self.write(custom_texts)

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def put(self, lang):
        request = json.loads(self.request.body)

        yield update_custom_texts(self.request.current_tenant_id, lang, request)

        GLApiCache.invalidate()

        self.set_status(202)  # Updated

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def delete(self, lang):
        yield delete_custom_texts(self.request.current_tenant_id, lang)

        GLApiCache.invalidate()
