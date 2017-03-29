# -*- coding: UTF-8

from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import *
from globaleaks.models.config import Config, NodeFactory, add_raw_config, del_config
from globaleaks.models.l10n import EnabledLanguage

from urlparse import urlparse


class MigrationScript(MigrationBase):
    def epilogue(self):
        nf = NodeFactory(self.store_new, 0)
        nf.model_class = self.model_from['Config']
        url = nf.get_val('public_site')
        o = urlparse(url)
        domain = o.hostname if not o.hostname is None else ''

        del_config(self.store_new, self.model_from['Config'], u'node', u'public_site')
        add_raw_config(self.store_new, self.model_from['Config'], u'node', u'hostname', domain != '', unicode(domain))

        url = nf.get_val('hidden_service')
        o = urlparse(url)
        domain = o.hostname if not o.hostname is None else ''

        del_config(self.store_new, self.model_from['Config'], u'node', u'hidden_service')
        add_raw_config(self.store_new, self.model_from['Config'], u'node', u'onionservice', domain != '', unicode(domain))

        add_raw_config(self.store_new, self.model_from['Config'], u'node', u'reachable_via_web', False, False)
        self.entries_count['Config'] += 1

        self.store_new.commit()
