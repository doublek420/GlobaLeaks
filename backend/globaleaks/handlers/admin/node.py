# -*- coding: UTF-8
#
#   /admin/node
#   *****
# Implementation of the code executed on handler /admin/node
#
import os

from storm.expr import In
from twisted.internet.defer import inlineCallbacks

from globaleaks import models, utils, LANGUAGES_SUPPORTED_CODES, LANGUAGES_SUPPORTED
from globaleaks.db.appdata import load_appdata
from globaleaks.handlers.base import BaseHandler
from globaleaks.memory import db_refresh_memory_variables
from globaleaks.models.config import NodeFactory, PrivateFactory
from globaleaks.models.l10n import EnabledLanguage, NodeL10NFactory
from globaleaks.orm import transact
from globaleaks.rest import errors, requests
from globaleaks.rest.apicache import GLApiCache
from globaleaks.settings import GLSettings
from globaleaks.utils.utility import log


def db_admin_serialize_node(store, language):
    tid=1
    node_dict = NodeFactory(store, tid).admin_export()

    # Contexts and Receivers relationship
    configured  = store.find(models.ReceiverContext).count() > 0
    custom_homepage = os.path.isfile(os.path.join(GLSettings.static_path, "custom_homepage.html"))

    misc_dict = {
        'version': PrivateFactory(store, tid).get_val('version'),
        'languages_supported': LANGUAGES_SUPPORTED,
        'languages_enabled': EnabledLanguage.list(store, 1),
        'configured': configured,
        'custom_homepage': custom_homepage,
    }

    l10n_dict = NodeL10NFactory(store, tid).localized_dict(language)

    return utils.sets.disjoint_union(node_dict, misc_dict, l10n_dict)


@transact
def admin_serialize_node(store, language):
    return db_admin_serialize_node(store, language)


def set_enabled_languages(store, tid, default_language, enabled_languages):
    cur_enabled_langs = EnabledLanguage.list(store, tid)
    new_enabled_langs = [unicode(l) for l in enabled_languages]

    if len(new_enabled_langs) < 1:
        raise errors.InvalidInputFormat("No languages enabled!")

    if default_language not in new_enabled_langs:
        raise errors.InvalidInputFormat("Invalid lang code for chosen default_language")

    appdata = None
    for lang in new_enabled_langs:
        if lang not in LANGUAGES_SUPPORTED_CODES:
            raise errors.InvalidInputFormat("Invalid lang code: %s" % lang)
        if lang not in cur_enabled_langs:
            if appdata is None:
                appdata = load_appdata()
            log.debug("Adding a new lang %s" % lang)
            EnabledLanguage.enable_language(store, tid, lang, appdata)

    to_remove = list(set(cur_enabled_langs) - set(new_enabled_langs))

    if len(to_remove):
        users = store.find(models.User, In(models.User.language, to_remove))
        for user in users:
            user.language = default_language

        for lang in to_remove:
            EnabledLanguage.delete(store, (tid, lang))


# TODO This cmd issues at least 3 SQL queries on node config.
def db_update_node(store, request, language):
    """
    Update and serialize the node infos

    :param store: the store on which perform queries.
    :param language: the language in which to localize data
    :return: a dictionary representing the serialization of the node
    """
    tid = 1
    set_enabled_languages(store, tid, request['default_language'], request['languages_enabled'])

    if language in request['languages_enabled']:
        node_l10n = NodeL10NFactory(store, tid)
        node_l10n.update(request, language)

    node = NodeFactory(store, tid)
    node.update(request)

    if request['basic_auth'] and request['basic_auth_username'] != '' and request['basic_auth_password']  != '':
        node.set_val('basic_auth', True)
        node.set_val('basic_auth_username', request['basic_auth_username'])
        node.set_val('basic_auth_password', request['basic_auth_password'])
    else:
        node.set_val('basic_auth', False)

    db_refresh_memory_variables(store)

    # TODO pass instance of db_update_node into admin_serialize
    return db_admin_serialize_node(store, language)


@transact
def update_node(*args):
    return db_update_node(*args)


class NodeInstance(BaseHandler):
    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def get(self):
        """
        Get the node infos.

        Parameters: None
        Response: AdminNodeDesc
        """
        node_description = yield admin_serialize_node(self.request.language)
        self.write(node_description)

    @BaseHandler.transport_security_check('admin')
    @BaseHandler.authenticated('admin')
    @inlineCallbacks
    def put(self):
        """
        Update the node infos.

        Request: AdminNodeDesc
        Response: AdminNodeDesc
        Errors: InvalidInputFormat
        """
        request = self.validate_message(self.request.body,
                                        requests.AdminNodeDesc)

        node_description = yield update_node(request, self.request.language)
        GLApiCache.invalidate(self.request.current_tenant_id)

        self.set_status(202) # Updated
        self.write(node_description)
