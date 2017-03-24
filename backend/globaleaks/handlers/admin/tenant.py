# -*- coding: UTF-8
#
#   tenant
#   *****
# Implementation of the Tenant handlers
#
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.tenant import db_delete_tenant, db_create_tenant, db_get_tenant_list, Tenant
from globaleaks.orm import transact
from globaleaks.rest import requests
from globaleaks.db import db_refresh_memory_variables


def serialize_tenant(tenant):
    return {
        'id': tenant.id,
        'label': tenant.label
    }


@transact
def get_tenant_list(store):
    return [serialize_tenant(tenant) for tenant in db_get_tenant_list(store)]


@transact
def create_tenant(store, request):
    tenant = db_create_tenant(store, request)

    db_refresh_memory_variables(store)
    return serialize_tenant(tenant)


@transact
def delete_tenant(store, tenant_id):
    db_delete_tenant(store, tenant_id)
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
