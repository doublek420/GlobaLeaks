# -*- coding: UTF-8
#
#   user
#   *****
# Implementation of the User model functionalities
#
from twisted.internet.defer import inlineCallbacks

from globaleaks import models, security
from globaleaks.db import db_refresh_exception_delivery_list
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import parse_pgp_options, user_serialize_user
from globaleaks.orm import transact
from globaleaks.rest import requests, errors
from globaleaks.rest.apicache import GLApiCache
from globaleaks.settings import GLSettings
from globaleaks.utils.structures import fill_localized_keys
from globaleaks.utils.utility import log, datetime_now


def db_create_admin_user(store, request, language):
    """
    Creates a new admin
    Returns:
        (dict) the admin descriptor
    """
    user = db_create_user(store, request, language)

    log.debug("Created new admin")

    db_refresh_exception_delivery_list(store)

    return user

@transact
def create_admin_user(store, request, language):
    return user_serialize_user(db_create_admin_user(store, request, language), language)


def db_create_custodian_user(store, request, language):
    """
    Creates a new custodian
    Returns:
        (dict) the custodian descriptor
    """
    user = db_create_user(store, request, language)

    log.debug("Created new custodian")

    return user


@transact
def create_custodian_user(store, request, language):
    return user_serialize_user(db_create_custodian_user(store, request, language), language)


def db_create_receiver(store, request, language):
    """
    Creates a new receiver
    Returns:
        (dict) the receiver descriptor
    """
    user = db_create_user(store, request, language)

    fill_localized_keys(request, models.Receiver.localized_keys, language)

    receiver = models.Receiver(request)

    # set receiver.id user.id
    receiver.id = user.id

    store.add(receiver)

    contexts = request.get('contexts', [])
    for context_id in contexts:
        context = store.find(models.Context, id=context_id).one()
        if not context:
            raise errors.ContextIdNotFound
        context.receivers.add(receiver)

    log.debug("Created new receiver")

    return receiver

@transact
def create_receiver_user(store, request, language):
    receiver = db_create_receiver(store, request, language)
    return user_serialize_user(receiver.user, language)


def db_create_user(store, request, language):
    fill_localized_keys(request, models.User.localized_keys, language)

    user = models.User({
        'username': request['username'],
        'role': request['role'],
        'state': u'enabled',
        'deletable': request['deletable'],
        'name': request['name'],
        'description': request['description'],
        'public_name': request['public_name'] if request['public_name'] != '' else request['name'],
        'language': language,
        'password_change_needed': request['password_change_needed'],
        'mail_address': request['mail_address']
    })

    if request['username'] == '':
        user.username = user.id

    password = request['password']
    if len(password) == 0:
        password = GLSettings.memory_copy.default_password

    user.salt = security.generateRandomSalt()
    user.password = security.hash_password(password, user.salt)

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)

    store.add(user)

    return user


def db_admin_update_user(store, user_id, request, language):
    """
    Updates the specified user.
    raises: globaleaks.errors.UserIdNotFound` if the user does not exist.
    """
    user = store.find(models.User, id=user_id).one()
    if not user:
        raise errors.UserIdNotFound

    fill_localized_keys(request, models.User.localized_keys, language)

    user.update(request)

    password = request['password']
    if len(password) > 0:
        user.password = security.hash_password(password, user.salt)
        user.password_change_date = datetime_now()

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)

    if user.role == 'admin':
        db_refresh_exception_delivery_list(store)

    return user


@transact
def admin_update_user(store, user_id, request, language):
    return user_serialize_user(db_admin_update_user(store, user_id, request, language), language)


def db_get_user(store, user_id):
    """
    raises :class:`globaleaks.errors.UserIdNotFound` if the user does
    not exist.
    Returns:
        (dict) the user
    """
    user = store.find(models.User, id=user_id).one()
    if not user:
        raise errors.UserIdNotFound

    return user


@transact
def get_user(store, user_id, language):
    user = db_get_user(store, user_id)
    return user_serialize_user(user, language)


def db_get_admin_users(store):
    return [user_serialize_user(user, GLSettings.memory_copy.default_language)
            for user in store.find(models.User,models.User.role == u'admin')]


@transact
def delete_user(store, user_id):
    user = db_get_user(store, user_id)

    if not user.deletable:
        raise errors.UserNotDeletable

    store.remove(user)


@transact
def get_user_list(store, language):
    """
    Returns:
        (list) the list of users
    """
    users = store.find(models.User)
    return [user_serialize_user(user, language) for user in users]


class UsersCollection(BaseHandler):
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def get(self):
        """
        Return all the users.

        Parameters: None
        Response: adminUsersList
        Errors: None
        """
        response = yield get_user_list(self.request.language)

        self.write(response)

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def post(self):
        """
        Create a new user

        Request: AdminUserDesc
        Response: AdminUserDesc
        Errors: InvalidInputFormat, UserIdNotFound
        """
        request = self.validate_message(self.request.body,
                                        requests.AdminUserDesc)

        if request['role'] == 'receiver':
            response = yield create_receiver_user(request, self.request.language)
        elif request['role'] == 'custodian':
            response = yield create_custodian_user(request, self.request.language)
        elif request['role'] == 'admin':
            response = yield create_admin_user(request, self.request.language)
        else:
            raise errors.InvalidInputFormat

        GLApiCache.invalidate(self.request.current_tenant_id)

        self.set_status(201) # Created
        self.write(response)


class UserInstance(BaseHandler):
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def get(self, user_id):
        """
        Get the specified user.

        Parameters: user_id
        Response: AdminUserDesc
        Errors: InvalidInputFormat, UserIdNotFound
        """
        response = yield get_user(user_id, self.request.language)

        self.write(response)

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def put(self, user_id):
        """
        Update the specified user.

        Parameters: user_id
        Request: AdminUserDesc
        Response: AdminUserDesc
        Errors: InvalidInputFormat, UserIdNotFound
        """
        request = self.validate_message(self.request.body, requests.AdminUserDesc)

        response = yield admin_update_user(user_id, request, self.request.language)
        GLApiCache.invalidate(self.request.current_tenant_id)

        self.set_status(201)
        self.write(response)

    @inlineCallbacks
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    def delete(self, user_id):
        """
        Delete the specified user.

        Parameters: user_id
        Request: None
        Response: None
        Errors: InvalidInputFormat, UserIdNotFound
        """
        yield delete_user(user_id)

        GLApiCache.invalidate(self.request.current_tenant_id)
