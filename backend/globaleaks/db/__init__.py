# -*- coding: UTF-8
# Database routines
# ******************
import os
import sys
import traceback

from storm import exceptions
from twisted.internet.defer import inlineCallbacks

from globaleaks import models, security, DATABASE_VERSION, FIRST_DATABASE_VERSION_SUPPORTED
from globaleaks.db.appdata import load_appdata, db_update_appdata
from globaleaks.handlers.admin import files, tenant
from globaleaks.models import config, l10n, User
from globaleaks.models.config import NotificationFactory
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

    appdata = load_appdata()

    db_update_appdata(store, appdata)

    root_tenant = {'label': 'localhost:8082'}
    tenant.db_create_tenant(store, root_tenant, use_single_lang)

    log.debug("Performing database initialization...")


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
