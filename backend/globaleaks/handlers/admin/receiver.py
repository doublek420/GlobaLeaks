# -*- coding: UTF-8
#
#   /admin/receivers
#   *****
# Implementation of the code executed on handler /admin/receivers
#
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin.user import db_create_receiver
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import user_serialize_user
from globaleaks.orm import transact
from globaleaks.rest import errors, requests
from globaleaks.rest.apicache import GLApiCache
from globaleaks.settings import GLSettings
from globaleaks.utils.structures import fill_localized_keys, get_localized_values


def admin_serialize_receiver(receiver, language):
    """
    Serialize the specified receiver

    :param language: the language in which to localize data
    :return: a dictionary representing the serialization of the receiver
    """
    ret_dict = user_serialize_user(receiver.user, language)

    ret_dict.update({
        'can_delete_submission': receiver.can_delete_submission,
        'can_postpone_expiration': receiver.can_postpone_expiration,
        'can_grant_permissions': receiver.can_grant_permissions,
        'mail_address': receiver.user.mail_address,
        'configuration': receiver.configuration,
        'contexts': [c.id for c in receiver.contexts],
        'tip_notification': receiver.tip_notification,
        'presentation_order': receiver.presentation_order
    })

    return get_localized_values(ret_dict, receiver, receiver.localized_keys, language)


def db_get_usermodel_list(store, model, tid):
    return store.find(model, model.id == models.UserTenant.user_id,
                             models.UserTenant.tenant_id == tid)

def db_get_usermodel(store, model, tid, id):
    return store.find(model, model.id == id,
                             model.id == models.UserTenant.user_id,
                             models.UserTenant.tenant_id == tid).one()

@transact
def get_receiver_list(store, tid, language):
    """
    Returns:
        (list) the list of receivers
    """
    return [admin_serialize_receiver(receiver, language)
        for receiver in db_get_usermodel_list(store, models.Receiver, tid)]


@transact
def create_receiver(store, tid, request, language):
    request['tip_expiration_threshold'] = GLSettings.memory_copy.notif.tip_expiration_threshold
    receiver = db_create_receiver(store, tid, request, language)
    return admin_serialize_receiver(receiver, language)


@transact
def get_receiver(store, tid, receiver_id, language):
    return admin_serialize_receiver(db_get_usermodel(store, models.Receiver, tid, receiver_id), language)


@transact
def update_receiver(store, receiver_id, request, language):
    """
    Updates the specified receiver with the details.
    raises :class:`globaleaks.errors.ReceiverIdNotFound` if the receiver does
    not exist.
    """
    receiver = models.Receiver.get(store, receiver_id)
    if not receiver:
        raise errors.ReceiverIdNotFound

    fill_localized_keys(request, models.Receiver.localized_keys, language)

    contexts = request.get('contexts', [])

    receiver.contexts.clear()

    for context_id in contexts:
        context = models.Context.get(store, context_id)
        if not context:
            raise errors.ContextIdNotFound

        receiver.contexts.add(context)

    receiver.update(request)

    return admin_serialize_receiver(receiver, language)


class ReceiversCollection(BaseHandler):
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def get(self):
        """
        Return all the receivers.

        Parameters: None
        Response: adminReceiverList
        Errors: None
        """
        response = yield get_receiver_list(self.request.current_tenant_id,
                                           self.request.language)

        self.write(response)


class ReceiverInstance(BaseHandler):
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def get(self, receiver_id):
        """
        Get the specified receiver.

        Parameters: receiver_id
        Response: AdminReceiverDesc
        Errors: InvalidInputFormat, ReceiverIdNotFound
        """
        response = yield get_receiver(self.request.current_tenant_id,
                                      receiver_id,
                                      self.request.language)

        self.write(response)

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def put(self, receiver_id):
        """
        Update the specified receiver.

        Parameters: receiver_id
        Request: AdminReceiverDesc
        Response: AdminReceiverDesc
        Errors: InvalidInputFormat, ReceiverIdNotFound, ContextIdNotFound
        """
        request = self.validate_message(self.request.body, requests.AdminReceiverDesc)

        response = yield update_receiver(receiver_id, request, self.request.language)
        GLApiCache.invalidate(self.request.current_tenant_id)

        self.set_status(201)
        self.write(response)
