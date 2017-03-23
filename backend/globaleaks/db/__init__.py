# -*- coding: UTF-8
# Database routines
# ******************
import os
import sys
import traceback

from cyclone.util import ObjectDict
from storm import exceptions
from twisted.internet.defer import inlineCallbacks

from globaleaks import models, security, DATABASE_VERSION, FIRST_DATABASE_VERSION_SUPPORTED
from globaleaks.db.appdata import db_update_appdata, db_fix_fields_attrs
from globaleaks.handlers.admin import files
from globaleaks.models import config, l10n, User, Tenant
from globaleaks.models.config import NodeFactory, NotificationFactory, PrivateFactory
from globaleaks.models.l10n import EnabledLanguage
from globaleaks.orm import transact, transact_sync
from globaleaks.settings import GLSettings
from globaleaks.utils.utility import log


def get_db_file(db_path):
    for i in reversed(range(0, DATABASE_VERSION + 1)):
        file_name = 'glbackend-%d.db' % i
        db_file_path = os.path.join(db_path, file_name)
        if os.path.exists(db_file_path):
            return (i, db_file_path)

    return (0, '')


def db_create_tables(store):
    with open(GLSettings.db_schema) as f:
        create_queries = ''.join(f.readlines()).split(';')
        for create_query in create_queries:
            try:
                store.execute(create_query + ';')
            except exceptions.OperationalError as exc:
                log.err("OperationalError in [%s]" % create_query)
                log.err(exc)


@transact_sync
def init_db(store, use_single_lang=False):
    db_create_tables(store)
    appdata_dict = db_update_appdata(store)

    log.debug("Performing database initialization...")
    first_tenant = Tenant()
    first_tenant.label = "localhost:8082"
    store.add(first_tenant)

    config.system_cfg_init(store)

    if not use_single_lang:
        EnabledLanguage.add_all_supported_langs(store, appdata_dict)
    else:
        EnabledLanguage.add_new_lang(store, u'en', appdata_dict)

    with open(os.path.join(GLSettings.client_path, 'data/logo.png'), 'r') as logo_file:
        data = logo_file.read()
        files.db_add_file(store, data, u'logo')

    with open(os.path.join(GLSettings.client_path, 'data/favicon.ico'), 'r') as favicon_file:
        data = favicon_file.read()
        files.db_add_file(store, data, u'favicon')


def update_db():
    """
    This function handles update of an existing database
    """
    from globaleaks.db import migration

    db_version, db_file_path = get_db_file(GLSettings.db_path)

    if db_version is 0:
        return

    GLSettings.initialize_db = False

    log.msg("Found an already initialized database version: %d" % db_version)

    if db_version >= FIRST_DATABASE_VERSION_SUPPORTED and db_version < DATABASE_VERSION:
        log.msg("Performing schema migration from version %d to version %d" % (db_version, DATABASE_VERSION))
        try:
            migration.perform_schema_migration(db_version)
        except Exception as exception:
            log.msg("Migration failure: %s" % exception)
            log.msg("Verbose exception traceback:")
            etype, value, tback = sys.exc_info()
            log.msg('\n'.join(traceback.format_exception(etype, value, tback)))
            return -1

        log.msg("Migration completed with success!")

    else:
        log.msg('Performing data update')
        # TODO on normal startup this line is run. We need better control flow here.
        migration.perform_data_update(os.path.abspath(os.path.join(GLSettings.db_path, 'glbackend-%d.db' % DATABASE_VERSION)))


def db_get_tracked_files(store):
    """
    returns a list the basenames of files tracked by InternalFile and ReceiverFile.
    """
    ifiles = list(store.find(models.InternalFile).values(models.InternalFile.file_path))
    rfiles = list(store.find(models.ReceiverFile).values(models.ReceiverFile.file_path))
    wbfiles = list(store.find(models.WhistleblowerFile).values(models.WhistleblowerFile.file_path))

    return [os.path.basename(files) for files in list(set(ifiles + rfiles + wbfiles))]


@transact_sync
def sync_clean_untracked_files(store):
    """
    removes files in GLSettings.submission_path that are not
    tracked by InternalFile/ReceiverFile.
    """
    tracked_files = db_get_tracked_files(store)
    for filesystem_file in os.listdir(GLSettings.submission_path):
        if filesystem_file not in tracked_files:
            file_to_remove = os.path.join(GLSettings.submission_path, filesystem_file)
            try:
                log.debug("Removing untracked file: %s" % file_to_remove)
                security.overwrite_and_remove(file_to_remove)
            except OSError:
                log.err("Failed to remove untracked file" % file_to_remove)


def db_refresh_exception_delivery_list(store):
    """
    Constructs a list of (email_addr, public_key) pairs that will receive errors from the platform.
    If the email_addr is empty, drop the tuple from the list.
    """
    notif_fact = NotificationFactory(store)
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
    node_ro = ObjectDict(NodeFactory(store).admin_export())

    GLSettings.memory_copy = node_ro

    GLSettings.memory_copy.accept_tor2web_access = {
        'admin': node_ro.tor2web_admin,
        'custodian': node_ro.tor2web_custodian,
        'whistleblower': node_ro.tor2web_whistleblower,
        'receiver': node_ro.tor2web_receiver,
        'unauth': node_ro.tor2web_unauth
    }

    enabled_langs = models.l10n.EnabledLanguage.list(store)
    GLSettings.memory_copy.languages_enabled = enabled_langs

    notif_fact = NotificationFactory(store)
    notif_ro = ObjectDict(notif_fact.admin_export())

    GLSettings.memory_copy.notif = notif_ro

    if GLSettings.developer_name:
        GLSettings.memory_copy.notif.source_name = GLSettings.developer_name

    tenants = store.find(Tenant) # TODO(tid_me) Must be removed
    GLSettings.memory_copy.tenant_map = {t.label: t.id for t in tenants}
    GLSettings.memory_copy.first_tenant_id = GLSettings.memory_copy.tenant_map['localhost:8082']

    db_refresh_exception_delivery_list(store)

    GLSettings.memory_copy.private = ObjectDict(PrivateFactory(store).mem_copy_export())


@transact
def refresh_memory_variables(*args):
    return db_refresh_memory_variables(*args)

@transact_sync
def sync_refresh_memory_variables(*args):
    return db_refresh_memory_variables(*args)
