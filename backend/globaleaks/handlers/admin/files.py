# -*- coding: utf-8 -*-
#
# /admin/files
#  *****
#
# API handling db files upload/download/delete
import base64
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.base import BaseHandler
from globaleaks.models import File
from globaleaks.orm import transact
from globaleaks.rest.apicache import GLApiCache


def db_add_file(store, tid, data, key = None):
    file_obj = None
    if key is not None:
        file_obj = store.find(File, tid=tid, key=key).one()

    if file_obj is None:
        file_obj = File()
        file_obj.tid = tid
        if key is not None:
            file_obj.key = key

        store.add(file_obj)

    file_obj.data = base64.b64encode(data)


@transact
def add_file(store, data, key = None):
    return db_add_file(store, data, key)


def db_get_file_by_key(store, tid, key):
    file_obj = store.find(File, tid=tid, key=key).one()
    return file_obj.data if file_obj is not None else ''


@transact
def get_file_by_key(store, tid, key):
    return db_get_file_by_key(store, tid, key)


@transact
def del_file(store, key):
    File.delete(store, key)


class FileInstance(BaseHandler):
    key = None

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def post(self, key):
        uploaded_file = self.get_file_upload()
        if uploaded_file is None:
            self.set_status(201)
            return

        try:
            yield add_file(uploaded_file['body'].read(), key)
        finally:
            uploaded_file['body'].close()

        GLApiCache.invalidate(self.request.current_tenant_id)

        self.set_status(201)

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def delete(self, key):
        yield del_file(key)

        GLApiCache.invalidate(self.request.current_tenant_id)
