# -*- encoding: utf-8 -*-

from storm.locals import Int, Bool, Unicode, DateTime, JSON

from globaleaks import __version__, DATABASE_VERSION, LANGUAGES_SUPPORTED_CODES
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import *


class Node_v_31(ModelWithUID):
    __storm_table__ = 'node'
    version = Unicode(default=unicode(__version__))
    version_db = Unicode(default=unicode(DATABASE_VERSION))
    name = Unicode(validator=shorttext_v, default=u'')
    basic_auth = Bool(default=False)
    basic_auth_username = Unicode(default=u'')
    basic_auth_password = Unicode(default=u'')
    public_site = Unicode(validator=shorttext_v, default=u'')
    hidden_service = Unicode(validator=shorttext_v, default=u'')
    receipt_salt = Unicode(validator=shorttext_v)
    languages_enabled = JSON(default=LANGUAGES_SUPPORTED_CODES)
    default_language = Unicode(validator=shorttext_v, default=u'en')
    default_timezone = Int(default=0)
    description = JSON(validator=longlocal_v, default=empty_localization)
    presentation = JSON(validator=longlocal_v, default=empty_localization)
    footer = JSON(validator=longlocal_v, default=empty_localization)
    security_awareness_title = JSON(validator=longlocal_v, default=empty_localization)
    security_awareness_text = JSON(validator=longlocal_v, default=empty_localization)
    maximum_namesize = Int(default=128)
    maximum_textsize = Int(default=4096)
    maximum_filesize = Int(default=30)
    tor2web_admin = Bool(default=True)
    tor2web_custodian = Bool(default=True)
    tor2web_whistleblower = Bool(default=False)
    tor2web_receiver = Bool(default=True)
    tor2web_unauth = Bool(default=True)
    allow_unencrypted = Bool(default=False)
    disable_encryption_warnings = Bool(default=False)
    allow_iframes_inclusion = Bool(default=False)
    submission_minimum_delay = Int(default=10)
    submission_maximum_ttl = Int(default=10800)
    can_postpone_expiration = Bool(default=False)
    can_delete_submission = Bool(default=False)
    can_grant_permissions = Bool(default=False)
    ahmia = Bool(default=False)
    allow_indexing = Bool(default=False)
    wizard_done = Bool(default=False)
    disable_submissions = Bool(default=False)
    disable_privacy_badge = Bool(default=False)
    disable_security_awareness_badge = Bool(default=False)
    disable_security_awareness_questions = Bool(default=False)
    disable_key_code_hint = Bool(default=False)
    disable_donation_panel = Bool(default=False)
    enable_captcha = Bool(default=True)
    enable_proof_of_work = Bool(default=True)
    enable_experimental_features = Bool(default=False)
    whistleblowing_question = JSON(validator=longlocal_v, default=empty_localization)
    whistleblowing_button = JSON(validator=longlocal_v, default=empty_localization)
    whistleblowing_receipt_prompt = JSON(validator=longlocal_v, default=empty_localization)
    simplified_login = Bool(default=True)
    enable_custom_privacy_badge = Bool(default=False)
    custom_privacy_badge_tor = JSON(validator=longlocal_v, default=empty_localization)
    custom_privacy_badge_none = JSON(validator=longlocal_v, default=empty_localization)
    header_title_homepage = JSON(validator=longlocal_v, default=empty_localization)
    header_title_submissionpage = JSON(validator=longlocal_v, default=empty_localization)
    header_title_receiptpage = JSON(validator=longlocal_v, default=empty_localization)
    header_title_tippage = JSON(validator=longlocal_v, default=empty_localization)
    widget_comments_title = JSON(validator=shortlocal_v, default=empty_localization)
    widget_messages_title = JSON(validator=shortlocal_v, default=empty_localization)
    widget_files_title = JSON(validator=shortlocal_v, default=empty_localization)
    landing_page = Unicode(default=u'homepage')
    contexts_clarification = JSON(validator=longlocal_v, default=empty_localization)
    show_small_context_cards = Bool(default=False)
    show_contexts_in_alphabetical_order = Bool(default=False)
    threshold_free_disk_megabytes_high = Int(default=200)
    threshold_free_disk_megabytes_medium = Int(default=500)
    threshold_free_disk_megabytes_low = Int(default=1000)
    threshold_free_disk_percentage_high = Int(default=3)
    threshold_free_disk_percentage_medium = Int(default=5)
    threshold_free_disk_percentage_low = Int(default=10)
    context_selector_type = Unicode(validator=shorttext_v, default=u'list')
    logo_id = Unicode()
    css_id = Unicode()


class User_v_31(ModelWithUID):
    __storm_table__ = 'user'
    creation_date = DateTime(default_factory=datetime_now)
    username = Unicode(validator=shorttext_v)
    password = Unicode()
    salt = Unicode()
    deletable = Bool(default=True)
    name = Unicode(validator=shorttext_v)
    description = JSON(validator=longlocal_v)
    role = Unicode()
    state = Unicode()
    last_login = DateTime(default_factory=datetime_null)
    mail_address = Unicode()
    language = Unicode()
    timezone = Int()
    password_change_needed = Bool(default=True)
    password_change_date = DateTime(default_factory=datetime_null)
    pgp_key_info = Unicode(default=u'')
    pgp_key_fingerprint = Unicode(default=u'')
    pgp_key_public = Unicode(default=u'')
    pgp_key_expiration = DateTime(default_factory=datetime_null)
    pgp_key_status = Unicode(default=u'disabled') # 'disabled', 'enabled'
    img_id = Unicode()


class Comment_v_31(ModelWithUID):
    __storm_table__ = 'comment'
    creation_date = DateTime(default_factory=datetime_now)
    internaltip_id = Unicode()
    author = Unicode()
    content = Unicode(validator=longtext_v)
    type = Unicode()
    new = Int(default=True)


class Message_v_31(ModelWithUID):
    __storm_table__ = 'message'
    creation_date = DateTime(default_factory=datetime_now)
    receivertip_id = Unicode()
    author = Unicode()
    content = Unicode(validator=longtext_v)
    type = Unicode()
    new = Int(default=True)


class MigrationScript(MigrationBase):
    def migrate_File(self):
        old_node = self.store_old.find(self.model_from['Node']).one()

        old_objs = self.store_old.find(self.model_from['File'])
        for old_obj in old_objs:
            new_obj = self.model_to['File']()

            for _, v in new_obj._storm_columns.iteritems():
                if v.name == 'id':
                    if getattr(old_obj, v.name) == old_node.logo_id:
                        new_obj.id = 'logo'
                    elif getattr(old_obj, v.name) == old_node.css_id:
                        new_obj.id = 'css'
                    else:
                        new_obj.id = old_obj.id

                    continue

                setattr(new_obj, v.name, getattr(old_obj, v.name))

            self.store_new.add(new_obj)

    def migrate_Comment(self):
        old_objs = self.store_old.find(self.model_from['Comment'])
        for old_obj in old_objs:
            new_obj = self.model_to['Comment']()
            for _, v in new_obj._storm_columns.iteritems():
                if v.name == 'author_id':
                    if old_obj.type == 'whistleblower':
                        continue

                    old_rtip_model = self.model_from['ReceiverTip']
                    old_rtips = self.store_old.find(old_rtip_model, old_rtip_model.internaltip_id == old_obj.internaltip_id)
                    if old_rtips.count() == 1:
                        new_obj.author_id = old_rtips.one().receiver.id
                    else:
                        old_user_model = self.model_from['User']
                        old_user = self.store_old.find(old_user_model, old_user_model.name == old_obj.author).one()
                        if old_user is not None:
                            new_obj.author_id = old_user.id

                    continue

                setattr(new_obj, v.name, getattr(old_obj, v.name))

            self.store_new.add(new_obj)

    def migrate_User(self):
        old_objs = self.store_old.find(self.model_from['User'])
        for old_obj in old_objs:
            new_obj = self.model_to['User']()
            for _, v in new_obj._storm_columns.iteritems():
                if v.name == 'public_name':
                    new_obj.public_name = old_obj.name
                    continue

                setattr(new_obj, v.name, getattr(old_obj, v.name))

            self.store_new.add(new_obj)
