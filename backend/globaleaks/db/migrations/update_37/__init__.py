# -*- coding: UTF-8

from storm.expr import And
from storm.locals import Bool, Int, Reference, ReferenceSet, Unicode, Storm, JSON


from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models.validators import shorttext_v, longtext_v, \
    shortlocal_v, longlocal_v, shorturl_v, longurl_v, natnum_v, range_v
from globaleaks.models import *
from globaleaks.models.config_desc import GLConfig
from globaleaks.utils.utility import datetime_now

from urlparse import urlparse

class Config_v_36(Storm):
    __storm_table__ = 'config'
    __storm_primary__ = ('var_group', 'var_name')

    cfg_desc = GLConfig
    var_group = Unicode()
    var_name = Unicode()
    value = JSON()
    customized = Bool(default=False)

    def __init__(self, group=None, name=None, value=None, cfg_desc=None, migrate=False):
        """
        :param value:    This input is passed directly into set_v
        :param migrate:  Added to comply with models.Model constructor which is
                         used to copy every field returned by storm from the db
                         from an old_obj to a new one.
        :param cfg_desc: Used to specify where to look for the Config objs descripitor.
                         This is used in mig 34.
        """
        if cfg_desc is not None:
            self.cfg_desc = cfg_desc

        if migrate:
            return

        self.var_group = unicode(group)
        self.var_name = unicode(name)

        self.set_v(value)

    @staticmethod
    def find_descriptor(config_desc_root, var_group, var_name):
        d = config_desc_root.get(var_group, {}).get(var_name, None)
        if d is None:
            raise ValueError('%s.%s descriptor cannot be None' % (var_group, var_name))

        return d

    def set_v(self, val):
        desc = self.find_descriptor(self.cfg_desc, self.var_group, self.var_name)
        if val is None:
            val = desc._type()
        if isinstance(desc, config_desc.Unicode) and isinstance(val, str):
            val = unicode(val)
        if not isinstance(val, desc._type):
            raise ValueError("Cannot assign %s with %s" % (self, type(val)))
        if desc.validator is not None:
            desc.validator(self, self.var_name, val)

        if self.value is None:
            self.value = {'v': val}

        elif self.value['v'] != val:
            self.customized = True
            self.value = {'v': val}

    def get_v(self):
        return self.value['v']

    def __repr__(self):
        return "<Config: %s.%s>" % (self.var_group, self.var_name)


class ConfigL10N_v_36(Storm):
    __storm_table__ = 'config_l10n'
    __storm_primary__ = ('lang', 'var_group', 'var_name')

    lang = Unicode()
    var_group = Unicode()
    var_name = Unicode()
    value = Unicode()
    customized = Bool(default=False)

    def __init__(self, lang_code=None, group=None, var_name=None, value='', migrate=False):
        if migrate:
            return

        self.lang = unicode(lang_code)
        self.var_group = unicode(group)
        self.var_name = unicode(var_name)
        self.value = unicode(value)

    def __repr__(self):
      return "<ConfigL10N %s::%s.%s::'%s'>" % (self.lang, self.var_group,
                                               self.var_name, self.value[:5])

    def set_v(self, value):
        value = unicode(value)
        if self.value != value:
            self.value = value
            self.customized = True

    def reset(self, new_value):
        self.set_v(new_value)
        self.customized = False

    @classmethod
    def retrieve_rows(cls, store, tid, lang_code, var_group):
        selector = And(cls.var_group == var_group,
                       cls.lang == unicode(lang_code))
        return [r for r in store.find(cls, selector)]

    @classmethod
    def _where_is(cls, tid, lang_code, var_group, var_name):
        return And(cls.lang == unicode(lang_code),
                   cls.var_group == var_group,
                   cls.var_name == unicode(var_name))


class ShortURL_v_36(ModelWithID):
    __storm_table__ = 'shorturl'
    shorturl = Unicode(validator=shorturl_v)
    longurl = Unicode(validator=longurl_v)


class CustomTexts_v_36(Model):
    __storm_table__ = 'customtexts'
    lang = Unicode(primary=True, validator=shorttext_v)
    texts = JSON()


class MigrationScript(MigrationBase):
    def generic_migration_function(self, model_name):
        old_objects = self.store_old.find(self.model_from[model_name])

        for old_obj in old_objects:
            new_obj = self.model_to[model_name](migrate=True)

            for _, v in new_obj._storm_columns.iteritems():
                if v.name == 'tid' and model_name in ['Config', 'ConfigL10N', 'CustomTexts', 'ShortUrl']:
                    new_obj.tid = 1
                else:
                    self.migrate_model_key(old_obj, new_obj, v.name)

            self.store_new.add(new_obj)

    def epilogue(self):
        self.store_new.add(tenant.Tenant({'label': 'antani'}))
