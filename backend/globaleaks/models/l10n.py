# -*- coding: utf-8 -*-

from storm.expr import And, In
from storm.locals import Unicode, Storm, Bool

from globaleaks import LANGUAGES_SUPPORTED_CODES
from globaleaks.models import ModelWithTID
from globaleaks.rest import errors


class EnabledLanguage(ModelWithTID):
    __storm_table__ = 'enabledlanguage'
    __storm_primary__ = 'tid', 'name'

    name = Unicode()

    def __init__(self, tid=None, name=None, migrate=False):
        if migrate:
            return

        self.tid = tid
        self.name = unicode(name)

    def __repr__(self):
        return "<EnabledLang: %s>" % self.name

    @classmethod
    def list(cls, store, tid):
        return list(store.find(cls, cls.tid==tid).values(cls.name))

    @classmethod
    def enable_language(cls, store, tid, lang, appdata):
        store.add(cls(tid, lang))
        NotificationL10NFactory(store, tid).initialize(lang, appdata)
        NodeL10NFactory(store, tid).initialize(lang, appdata)


class ConfigL10N(ModelWithTID):
    __storm_table__ = 'config_l10n'
    __storm_primary__ = ('tid', 'lang', 'var_group', 'var_name')

    lang = Unicode()
    var_group = Unicode()
    var_name = Unicode()
    value = Unicode()
    customized = Bool(default=False)

    def __init__(self, tid=None, lang=None, var_group=None, var_name=None, value='', migrate=False):
        if migrate:
            return

        self.tid = tid
        self.lang = unicode(lang)
        self.var_group = unicode(var_group)
        self.var_name = unicode(var_name)
        self.value = unicode(value)

    def __repr__(self):
      return "<ConfigL10N %d %s::%s.%s::'%s'>" % (self.tid,
                                                  self.lang, self.var_group,
                                                  self.var_name, self.value[:5])

    def set_v(self, value):
        value = unicode(value)
        if self.value != value:
            self.value = value
            self.customized = True

    def reset(self, new_value):
        self.set_v(new_value)
        self.customized = False


class ConfigL10NFactory(object):
    localized_keys = frozenset()
    unmodifiable_keys = frozenset()

    def __init__(self, store, tid, var_group):
        self.model_class = ConfigL10N
        self.store = store
        self.tid = tid
        self.var_group = unicode(var_group)

        #TODO use lazy loading to optimize query performance

    def initialize(self, lang, l10n_data_src, keys=None):
        if keys is None:
            keys = self.localized_keys

        for key in keys:
            value = l10n_data_src[key][lang] if key in l10n_data_src else ''
            entry = self.model_class(self.tid, lang, self.var_group, key, value)
            self.store.add(entry)

    def localized_dict(self, lang):
        rows = self.store.find(self.model_class, lang = unicode(lang), var_group = self.var_group)
        return {c.var_name : c.value for c in rows if c.var_name in self.localized_keys}

    def update(self, request, lang):
        rows = self.store.find(self.model_class, lang = unicode(lang), var_group = self.var_group)
        c_map = {c.var_name : c for c in rows}

        for key in self.localized_keys - self.unmodifiable_keys:
            c_map[key].set_v(unicode(request[key]))

    def update_defaults(self, langs, l10n_data_src, reset=False):
        for lang in langs:
            old_keys = []

            for cfg in self.get_all(lang):
                old_keys.append(cfg.var_name)
                if cfg.var_name in self.localized_keys:
                    if (not cfg.customized or reset or cfg.var_name in self.unmodifiable_keys) and cfg.var_name in l10n_data_src:
                        cfg.value = l10n_data_src[cfg.var_name][lang]
                else:
                    self.store.remove(cfg)

            ConfigL10NFactory.initialize(self, lang, l10n_data_src,  list(set(self.localized_keys) - set(old_keys)))

    def get_all(self, lang):
        return self.store.find(self.model_class, lang=lang, var_group=self.var_group)

    def get_val(self, var_name, lang):
        cfg = self.store.find(ConfigL10N, lang=unicode(lang), var_group=unicode(self.var_group), var_name=unicode(var_name)).one()
        if cfg is None:
            raise errors.ModelNotFound('ConfigL10N:%s.%s' % (self.var_group, var_name))

        return cfg.value

    def set_val(self, var_name, lang, value):
        cfg = self.store.find(self.model_class, tid=self.tid, var_group=unicode(self.var_group), lang=unicode(lang), var_name=unicode(var_name)).one()
        cfg.set_v(unicode(value))


class NodeL10NFactory(ConfigL10NFactory):
    localized_keys = frozenset({
        'description',
        'presentation',
        'footer',
        'security_awareness_title',
        'security_awareness_text',
        'whistleblowing_question',
        'whistleblowing_button',
        'whistleblowing_receipt_prompt',
        'custom_privacy_badge_tor',
        'custom_privacy_badge_none',
        'header_title_homepage',
        'header_title_submissionpage',
        'header_title_receiptpage',
        'header_title_tippage',
        'contexts_clarification',
        'widget_comments_title',
        'widget_messages_title',
        'widget_files_title',
    })

    def __init__(self, store, tid):
        ConfigL10NFactory.__init__(self, store, tid, 'node')

    def initialize(self, lang, appdata_dict):
        l10n_data_src = appdata_dict['node']
        ConfigL10NFactory.initialize(self, lang, l10n_data_src)


class NotificationL10NFactory(ConfigL10NFactory):
    localized_keys = frozenset({
        'admin_anomaly_mail_title',
        'admin_anomaly_mail_template',
        'admin_anomaly_disk_low',
        'admin_anomaly_disk_medium',
        'admin_anomaly_disk_high',
        'admin_anomaly_activities',
        'admin_pgp_alert_mail_title',
        'admin_pgp_alert_mail_template',
        'admin_test_static_mail_template',
        'admin_test_static_mail_title',
        'pgp_alert_mail_title',
        'pgp_alert_mail_template',
        'tip_mail_template',
        'tip_mail_title',
        'file_mail_template',
        'file_mail_title',
        'comment_mail_template',
        'comment_mail_title',
        'message_mail_template',
        'message_mail_title',
        'tip_expiration_mail_template',
        'tip_expiration_mail_title',
        'tip_expiration_summary_mail_template',
        'tip_expiration_summary_mail_title',
        'receiver_notification_limit_reached_mail_template',
        'receiver_notification_limit_reached_mail_title',
        'identity_access_authorized_mail_template',
        'identity_access_authorized_mail_title',
        'identity_access_denied_mail_template',
        'identity_access_denied_mail_title',
        'identity_access_request_mail_template',
        'identity_access_request_mail_title',
        'identity_provided_mail_template',
        'identity_provided_mail_title',
        'export_template',
        'export_message_whistleblower',
        'export_message_recipient',
    })

    # These strings are not exposed in admin the interface for customization
    unmodifiable_keys = frozenset({
        'identity_access_authorized_mail_template',
        'identity_access_authorized_mail_title',
        'identity_access_denied_mail_template',
        'identity_access_denied_mail_title',
        'identity_access_request_mail_template',
        'identity_access_request_mail_title',
        'identity_provided_mail_template',
        'identity_provided_mail_title',
        'export_template',
        'export_message_whistleblower',
        'export_message_recipient',
        'admin_anomaly_mail_template',
        'admin_anomaly_mail_title',
        'admin_anomaly_activities',
        'admin_anomaly_disk_high',
        'admin_anomaly_disk_medium',
        'admin_anomaly_disk_low',
        'admin_test_static_mail_template',
        'admin_test_static_mail_title',
    })

    # These strings are modifiable via the admin/notification handler
    modifiable_keys = localized_keys - unmodifiable_keys

    def __init__(self, store, tid):
        ConfigL10NFactory.__init__(self, store, tid, 'notification')

    def initialize(self, lang, appdata_dict):
        l10n_data_src = appdata_dict['templates']
        ConfigL10NFactory.initialize(self, lang, l10n_data_src)

    def reset_templates(self, l10n_data_src):
        langs = EnabledLanguage.list(self.store, self.tid)
        self.update_defaults(langs, l10n_data_src, reset=True)


def update_defaults(store, tid, appdata):
    langs = EnabledLanguage.list(store, tid)
    NodeL10NFactory(store, tid).update_defaults(langs, appdata['node'])
    NotificationL10NFactory(store, tid).update_defaults(langs, appdata['templates'])
