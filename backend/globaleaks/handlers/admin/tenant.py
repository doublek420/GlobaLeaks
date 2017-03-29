# -*- coding: UTF-8
#
#   tenant
#   *****
# Implementation of the Tenant handlers
#
import os
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.db.appdata import load_appdata
from globaleaks.handlers.admin import files
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import File, Tenant, config
from globaleaks.models.l10n import EnabledLanguage
from globaleaks.orm import transact
from globaleaks.rest import requests
from globaleaks.memory import db_refresh_memory_variables
from globaleaks.settings import GLSettings
from globaleaks.utils.utility import log


def serialize_tenant(tenant):
    return {
        'id': tenant.id,
        'label': tenant.label
    }


def db_create_tenant(store, desc, use_single_lang=False):
    appdata = load_appdata()

    tenant = Tenant(desc)
    store.add(tenant)
    store.flush()

    config.db_create_config(store, tenant.id)

    EnabledLanguage.enable_language(store, tenant.id, u'en', appdata)

    for t in [(u'logo', 'data/logo.png'),
              (u'favicon', 'data/favicon.ico')]:
        with open(os.path.join(GLSettings.client_path, t[1]), 'r') as logo_file:
            files.db_add_file(store, tenant.id, logo_file.read(), t[0])

    log.debug("Creating %s" % tenant)

    return tenant


@transact
def get_tenant_list(store):
    return [serialize_tenant(tenant) for tenant in store.find(Tenant)]


@transact
def create_tenant(store, request):
    tenant = db_create_tenant(store, request)

    db_refresh_memory_variables(store)
    return serialize_tenant(tenant)


@transact
def delete_tenant(store, tenant_id):
    Tenant.delete(store, tenant_id)
    db_refresh_memory_variables(store)


class TenantCollection(BaseHandler):
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def get(self):
        """
        Return the list of registered tenants
        """
        response = yield get_tenant_list()

        self.write(response)

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def post(self):
        """
        Create a new tenant
        """
        request = self.validate_message(self.request.body, requests.AdminTenantDesc)

        response = yield create_tenant(request)

        self.set_status(201) # Created
        self.write(response)


class TenantInstance(BaseHandler):
    @inlineCallbacks
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    def delete(self, tenant_id):
        """
        Delete the specified tenant.
        """
        tenant_id = int(tenant_id)
        if tenant_id == self.request.current_tenant_id:
            raise Exception('System will not delete the current tenant.')

        yield delete_tenant(tenant_id)
