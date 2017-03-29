# -*- coding: UTF-8
#   backend
#   *******
# Here is the logic for creating a twisted service. In this part of the code we
# do all the necessary high level wiring to make everything work together.
# Specifically we create the cyclone web.Application from the API specification,
# we create a TCPServer for it and setup logging.
# We also set to kill the threadpool (the one used by Storm) when the
# application shuts down.

import os, sys

from twisted.application import internet, service
from twisted.internet import reactor, defer
from twisted.python import log as txlog, logfile as txlogfile

from globaleaks.db import init_db, sync_clean_untracked_files, \
    sync_refresh_memory_variables
from globaleaks.rest import api
from globaleaks.settings import GLSettings
from globaleaks import utils
from globaleaks.utils.utility import log, GLLogObserver
from globaleaks.utils.sock import listen_tcp_on_sock, reserve_port_for_ip
from globaleaks.workers.supervisor import ProcessSupervisor

# this import seems unused but it is required in order to load the mocks
import globaleaks.mocks.cyclone_mocks
import globaleaks.mocks.twisted_mocks


# Used by configure_tor_hs
import txtorcon
from txtorcon import TCPHiddenServiceEndpoint, build_local_tor_connection
from globaleaks.models.config import PrivateFactory, Config

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks.orm import transact_sync

@transact_sync
@inlineCallbacks
def configure_tor_hs(store):
    priv_key = PrivateFactory(store).get_val('tor_onion_priv_key')

    log.msg('Starting up tor connection')
    tor_conn = yield txtorcon.build_local_tor_connection(reactor)

    hs_loc = ('80 localhost:8082')
    if priv_key == '':
        log.msg('Creating new onion service')
        ephs = txtorcon.EphemeralHiddenService(hs_loc)
        yield ephs.add_to_tor(tor_conn.protocol)
        cfg = Config('private', 'tor_onion_priv_key', ephs.private_key)
        store.add(cfg)
    else:
        log.msg('Setting up existing onion service')
        ephs = txtorcon.EphemeralHiddenService(hs_loc, priv_key)
        yield ephs.add_to_tor(tor_conn.protocol)

    @inlineCallbacks
    def shutdown_hs():
        # TODO(nskelsey) Evaluate if it is worth cleaning up after the fact.
        log.msg('Shutting down onion service:%s' % ephs.hostname)
        yield ephs.remove_from_tor(tor_conn.protocol)

    reactor.addSystemEventTrigger('before', 'shutdown', shutdown_hs)
    log.msg('Added ephemeral service to tor: %s, %s' % (ephs.hostname, ephs.private_key))


def fail_startup(excep):
    log.err("ERROR: Cannot start GlobaLeaks. Please manually examine the exception.")
    log.err("EXCEPTION: %s" % excep)
    reactor.stop()


def pre_listen_startup():
    mask = 0
    if GLSettings.devel_mode:
        mask = 9000

    address = GLSettings.bind_address

    GLSettings.http_socks = []
    for port in GLSettings.bind_ports:
        port = port+mask if port < 1024 else port
        http_sock, fail = reserve_port_for_ip(GLSettings.bind_address, port)
        if fail is not None:
            log.err("Could not reserve socket for %s (error: %s)" % (fail[0], fail[1]))
        else:
            GLSettings.http_socks += [http_sock]

    https_sock, fail = reserve_port_for_ip(GLSettings.bind_address, 443+mask)
    if fail is not None:
        log.err("Could not reserve socket for %s (error: %s)" % (fail[0], fail[1]))
    else:
        GLSettings.https_socks = [https_sock]

    GLSettings.fix_file_permissions()
    #GLSettings.drop_privileges()
    #GLSettings.check_directories()

    if GLSettings.initialize_db:
        init_db()

    sync_clean_untracked_files()
    sync_refresh_memory_variables()


class GLService(service.Service):
    def startService(self):
        reactor.callLater(0, self.deferred_start)

    @defer.inlineCallbacks
    def deferred_start(self):
        try:
            yield self._deferred_start()
        except Exception as excep:
            fail_startup(excep)

    @defer.inlineCallbacks
    def _deferred_start(self):
        GLSettings.orm_tp.start()
        reactor.addSystemEventTrigger('after', 'shutdown', GLSettings.orm_tp.stop)
        GLSettings.api_factory = api.get_api_factory()

        yield configure_tor_hs()

        for sock in GLSettings.http_socks:
            listen_tcp_on_sock(reactor, sock.fileno(), GLSettings.api_factory)

        GLSettings.state.process_supervisor = ProcessSupervisor(GLSettings.https_socks,
                                                                '127.0.0.1',
                                                                GLSettings.bind_port)

        yield GLSettings.state.process_supervisor.maybe_launch_https_workers()

        GLSettings.start_jobs()

        print("GlobaLeaks is now running and accessible at the following urls:")

        if GLSettings.memory_copy.reachable_via_web:
            print("- http://%s:%d%s" % (GLSettings.bind_address, GLSettings.bind_port, GLSettings.api_prefix))
            if GLSettings.memory_copy.hostname:
                print("- http://%s:%d%s" % (GLSettings.memory_copy.hostname, GLSettings.bind_port, GLSettings.api_prefix))
        else:
            print("- http://127.0.0.1:%d%s" % (GLSettings.bind_port, GLSettings.api_prefix))

        if GLSettings.tor_address is not None:
            print("- http://%s%s" % (GLSettings.tor_address, GLSettings.api_prefix))


application = service.Application('GLBackend')

if not GLSettings.nodaemon and GLSettings.logfile:
    name = os.path.basename(GLSettings.logfile)
    directory = os.path.dirname(GLSettings.logfile)

    gl_logfile = txlogfile.LogFile(name, directory,
                                 rotateLength=GLSettings.log_file_size,
                                 maxRotatedFiles=GLSettings.num_log_files)

    application.setComponent(txlog.ILogObserver, GLLogObserver(gl_logfile).emit)

try:
    pre_listen_startup()

    service = GLService()
    service.setServiceParent(application)

except Exception as excep:
    fail_startup(excep)
    # Exit with non-zero exit code to signal systemd/system5
    sys.exit(55)
