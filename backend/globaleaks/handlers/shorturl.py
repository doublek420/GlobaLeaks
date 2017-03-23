from storm.expr import And
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact


@transact
def translate_shorturl(store, tid, shorturl):
    shorturl = store.find(models.ShortURL, And(models.ShortURL.shorturl == shorturl,
                                               models.ShortURL.tid == tid)).one()
    if not shorturl:
        return '/'

    return shorturl.longurl


class ShortUrlInstance(BaseHandler):
    """
    This handler implement the platform url shortener
    """
    handler_exec_time_threshold = 30

    @BaseHandler.transport_security_check('unauth')
    @BaseHandler.unauthenticated
    @inlineCallbacks
    def get(self, shorturl):
        longurl = yield translate_shorturl(self.request.current_tenant_id, shorturl)
        self.redirect(longurl)
