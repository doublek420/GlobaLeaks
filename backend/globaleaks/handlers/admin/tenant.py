# -*- coding: UTF-8
#
#   tenant
#   *****
# Implementation of the Tenant handlers
#
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact
from globaleaks.rest import requests
from globaleaks.db import db_refresh_memory_variables


def serialize_tenant(tenant):
    return {
        'id': tenant.id,
        'label': tenant.label
    }


def db_get_tenant_list(store):
    tenants = store.find(models.Tenant)
    return [serialize_tenant(tenant) for tenant in tenants]


@transact
def get_tenant_list(store):
    return db_get_tenant_list(store)


@transact
def create_tenant(store, request):
    tenant = models.Tenant(request)
    store.add(tenant)

    db_refresh_memory_variables(store)
    return serialize_tenant(tenant)


@transact
def delete_tenant(store, tenant_id):
    tenant = store.find(models.Tenant, models.Tenant.id == tenant_id).one()
    if tenant:
        store.remove(tenant)

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
        yield delete_tenant(tenant_id)
