from twisted.internet.defer import inlineCallbacks

from globaleaks.db.appdata import load_appdata
from globaleaks.handlers.admin.node import admin_serialize_node
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import get_user_settings
from globaleaks.memory import db_refresh_memory_variables
from globaleaks.models.config import NotificationFactory, PrivateFactory
from globaleaks.models.l10n import NotificationL10NFactory
from globaleaks.models.properties import iso_strf_time
from globaleaks.orm import transact
from globaleaks.rest import requests
from globaleaks.security import parse_pgp_key
from globaleaks.settings import GLSettings
from globaleaks.utils.mailutils import sendmail
from globaleaks.utils.sets import disjoint_union
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import log


def parse_pgp_options(notif, request):
    """
    Used for parsing PGP key infos and fill related notification configurations.

    @param notif: the notif orm object
    @param request: the dictionary containing the pgp infos to be parsed
    @return: None
    """
    pgp_key_public = request['exception_email_pgp_key_public']
    remove_key = request['exception_email_pgp_key_remove']

    k = None
    if not remove_key and pgp_key_public != '':
        k = parse_pgp_key(pgp_key_public)

    if k is not None:
        notif.set_val('exception_email_pgp_key_public', k['public'])
        notif.set_val('exception_email_pgp_key_fingerprint', k['fingerprint'])
        notif.set_val('exception_email_pgp_key_expiration', iso_strf_time(k['expiration']))
    else:
        notif.set_val('exception_email_pgp_key_public', '')
        notif.set_val('exception_email_pgp_key_fingerprint', '')
        notif.set_val('exception_email_pgp_key_expiration', '')


def admin_serialize_notification(store, language):
    tid = 1
    config_dict = NotificationFactory(store, tid).admin_export()

    cmd_flags = {
        'reset_templates': False,
        'exception_email_pgp_key_remove': False,
        'smtp_password': '',
    }

    conf_l10n_dict = NotificationL10NFactory(store, tid).localized_dict(language)

    return disjoint_union(config_dict, cmd_flags, conf_l10n_dict)


def db_get_notification(store, language):
    return admin_serialize_notification(store, language)


@transact
def get_notification(store, language):
    return db_get_notification(store, language)


@transact
def update_notification(store, request, language):
    tid = 1
    notif_l10n = NotificationL10NFactory(store, tid)
    notif_l10n.update(request, language)

    if request.pop('reset_templates'):
        appdata = load_appdata()
        notif_l10n.reset_templates(appdata)

    smtp_pw = request.pop('smtp_password', u'')
    if smtp_pw != u'':
        PrivateFactory(store, 1).set_val('smtp_password', smtp_pw)

    notif = NotificationFactory(store, 1)
    notif.update(request)

    parse_pgp_options(notif, request)

    # Since the Notification object has been changed refresh the global copy.
    db_refresh_memory_variables(store)

    return admin_serialize_notification(store, language)


class NotificationInstance(BaseHandler):
    """
    Manage Notification settings (account details and template)
    """

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def get(self):
        """
        Parameters: None
        Response: AdminNotificationDesc
        Errors: None (return empty configuration, at worst)
        """
        notification_desc = yield get_notification(self.request.language)
        self.write(notification_desc)

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def put(self):
        """
        Request: AdminNotificationDesc
        Response: AdminNotificationDesc
        Errors: InvalidInputFormat

        Changes the node notification settings.
        """
        request = self.validate_message(self.request.body,
                                        requests.AdminNotificationDesc)

        response = yield update_notification(request, self.request.language)

        self.set_status(202)
        self.write(response)


class NotificationTestInstance(BaseHandler):
    """
    Send Test Email Notifications to the admin that clicked the button.
    This post takes no arguments and generates an empty response to both
    successful and unsucessful requests. Understand that this handler blocks
    its thread until both the db query and the SMTP round trip return.
    """
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def post(self):
        """
        Parameters: None
        Response: None
        """
        user = yield get_user_settings(self.current_user.user_id,
                                     GLSettings.memory_copy.default_language)

        language = user['language']

        yield get_notification(language)

        data = {}
        data['type'] = 'admin_test_static'
        data['node'] = yield admin_serialize_node(language)
        data['notification'] = yield get_notification(language)

        subject, body = Templating().get_mail_subject_and_body(data)

        send_to = user['mail_address']

        log.debug("Attempting to send test email to: %s" % send_to)
        # If sending the email fails the exception mail address will be mailed.
        # If the failure is due to a bad SMTP config that will fail too, but it
        # doesn't hurt to try!
        try:
            yield sendmail(send_to, subject, body)
        except Exception as e:
            log.debug("Sending to admin failed. Trying an exception mail")
            raise e
