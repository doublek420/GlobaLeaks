# -*- coding: utf-8 -*-

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import files
from globaleaks.tests import helpers


class TestFileInstance(helpers.TestHandler):
    _handler = files.FileInstance

    @inlineCallbacks
    def test_post(self):
        handler = self.request({}, role='admin')

        yield handler.post(u'antani')

    @inlineCallbacks
    def test_delete(self):
        handler = self.request({}, role='admin')
        yield handler.delete(u'antani')

        # TODO(tid_me) assumes tid=1 exists
        tid = 1
        img = yield files.get_file_by_key(tid, u'antani')
        self.assertEqual(img, '')
