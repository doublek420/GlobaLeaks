from cyclone.util import ObjectDict

from globaleaks import LANGUAGES_SUPPORTED_CODES
from globaleaks.models import config, l10n, Tenant, User
from globaleaks.orm import transact, transact_sync
from globaleaks.settings import GLSettings


def db_refresh_exception_delivery_list(store):
    """
    Constructs a list of (email_addr, public_key) pairs that will receive errors from the platform.
    If the email_addr is empty, drop the tuple from the list.
    """
    notif_fact = config.NotificationFactory(store, 1)
    error_addr = notif_fact.get_val('exception_email_address')
    error_pk = notif_fact.get_val('exception_email_pgp_key_public')

    lst = [(error_addr, error_pk)]

    results = store.find(User, User.role==unicode('admin')) \
                   .values(User.mail_address, User.pgp_key_public)

    lst.extend([(mail, pub_key) for (mail, pub_key) in results])
    trimmed = filter(lambda x: x[0] != '', lst)
    GLSettings.memory_copy.notif.exception_delivery_list = trimmed


def db_refresh_memory_variables(store):
    """
    This routine loads in memory few variables of node and notification tables
    that are subject to high usage.
    """
    tid=1
    node_ro = ObjectDict(config.NodeFactory(store, tid).admin_export())

    GLSettings.memory_copy = node_ro

    GLSettings.memory_copy.accept_tor2web_access = {
        'admin': node_ro.tor2web_admin,
        'custodian': node_ro.tor2web_custodian,
        'whistleblower': node_ro.tor2web_whistleblower,
        'receiver': node_ro.tor2web_receiver,
        'unauth': node_ro.tor2web_unauth
    }

    if node_ro['wizard_done']:
        enabled_langs = l10n.EnabledLanguage.list(store, tid)
    else:
        enabled_langs = LANGUAGES_SUPPORTED_CODES

    GLSettings.memory_copy.languages_enabled = enabled_langs

    notif_fact = config.NotificationFactory(store, 1)
    notif_ro = ObjectDict(notif_fact.admin_export())

    GLSettings.memory_copy.notif = notif_ro

    if GLSettings.developer_name:
        GLSettings.memory_copy.notif.source_name = GLSettings.developer_name

    tenants = store.find(Tenant) # TODO(tid_me) Must be removed
    GLSettings.memory_copy.tenant_map = {t.label: t.id for t in tenants}

    # TODO(tid_me) change .get() to hard lookup
    GLSettings.memory_copy.first_tenant_id = GLSettings.memory_copy.tenant_map.get('localhost:8082', None)

    db_refresh_exception_delivery_list(store)

    GLSettings.memory_copy.private = ObjectDict(config.PrivateFactory(store, 1).mem_copy_export())


@transact
def refresh_memory_variables(*args):
    return db_refresh_memory_variables(*args)


@transact_sync
def sync_refresh_memory_variables(*args):
    return db_refresh_memory_variables(*args)
