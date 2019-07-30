#!/usr/bin/env python3

import gevent
#from gevent import monkey; monkey.patch_all()
import getpass
import logging
import logging.handlers
import os
import pwd
import signal
import sys

from gevent import socket as gsocket
from gevent.server import StreamServer
from ldap3.core.exceptions import (LDAPInvalidFilterError,
                                   LDAPMaximumRetriesError,
                                   LDAPSocketOpenError)
from multildap.client import LdapClient, logger as logger_client
from multildap.commands import (LdapCommand,
                                LDAPUnrecognizesCommandAttributes,
                                logger as logger_commands)
from time import time, sleep


logger = logging.getLogger('multildapd')


_CONN = []
_LOG_LDAP_REQUEST = 0
# a LDAP command cannot be more then ... lines
_LDAP_MAX_COMMAND_LINES = 13


def ldap_result(ldap_command):
    result = ''
    lc = LdapCommand(ldap_command)
    # how many seconds a request should takes?
    try:
        start = time()
        result = lc.process(ldapclients=_CONN)
        end = time()
        msg = '[{} {} -> {}bytes] elapsed in: {:.2f}'
        elapsed = msg.format(ldap_command[0],
                             lc.filter if hasattr(lc, 'filter') else lc.type,
                             len(result),
                             (end - start))
        logger.info(elapsed)
    except LDAPInvalidFilterError as exp:
        logger.error('Invalid filter: {}'.format(dec_line))
    except LDAPMaximumRetriesError as exp:
        end = time()
        msg = 'LDAP endpoint connection error [{0:.2f}s]: {1}'
        logger.critical(msg.format((end - start), exp))
    except LDAPSocketOpenError as exp:
        end = time()
        msg = 'LDAP endpoint connection error [{0:.2f}s]: {1}'
        logger.critical(msg.format((end - start), exp))
    except Exception as exp:
        logger.info('Error on handling connection: {}'.format(exp))
        # TODO: write error code to clients to interrupt wait
        # socket.sendall('{}\n'.format(exp).encode())

    #result = result.replace('ou=people,dc=testunical,dc=it', 'dc=proxy,dc=unical,dc=it')
    logger.debug('RESPONSE \n{}'.format(result))
    return result

def create_socket(args):
    # clean up previous socket
    if os.path.exists(args.socket):
        msg = 'Unlink and remove previous socket: {}'
        logger.info(msg.format(args.socket))
        os.unlink(args.socket)

    # logger.info('Create a socket {}'.format(args.socket))
    # creates a new server on a unix domain socket
    sock = gsocket.socket(gsocket.AF_UNIX,
                          gsocket.SOCK_STREAM)
    sock.setblocking(0)
    sock.bind(args.socket)

    # todo arg to change users
    user = pwd.getpwnam(getpass.getuser())

    # We would like to also set the user to "cmsuser" but only root
    # can do that. Therefore we limit ourselves to the group.
    os.chown(args.socket, os.getuid(), user.pw_gid)

    uid = pwd.getpwnam(args.uid).pw_uid
    os.chmod(args.socket, 0o660)
    os.chown(args.socket, uid, 0)

    backlog=33
    sock.listen(backlog)
    return sock


def reset_ldap_command():
    return [None, {}]


def handle_debug1(socket, address):
    rfileobj = socket.makefile(mode='rb')
    while 1:
        line = rfileobj.readline()
        if line == b'\n':
            result = """dn: uid=mario,dc=proxy,dc=unical,dc=it
uid: mario
mail: mario.rossi@unical.it
sn: rossi
cn: mario

dn: uid=peppe,dc=proxy,dc=unical,dc=it
uid: peppe
mail: peppe.grossi@unical.it
sn: rossi
cn: peppe

RESULT
code: 0
"""
            socket.sendall(result.encode())
            break
    rfileobj.close()


def handle(socket, address):
    if address:
        logger.info('new connection from {}'.format(address))
    else:
        logger.info('new local connection on unix domain socket')

    ldap_command = reset_ldap_command()
    result = None
    rfileobj = socket.makefile(mode='rb')
    while True:
        line = rfileobj.readline()
        if line == b'\n':
            logger.debug("END command submission".format(address))
            result = ldap_result(ldap_command)
            ldap_command = reset_ldap_command()
            socket.sendall(result.encode())
            result = None
            break
        elif not line:
            logger.info("client {} disconnected".format(address))
            break
        else:
            if _LOG_LDAP_REQUEST:
                logger.debug("Received: {}".format(line))

            dec_line = line.decode().replace('\n', '')

            # filter, security check
            if len(ldap_command[1].keys()) > _LDAP_MAX_COMMAND_LINES:
                raise LDAPUnrecognizesCommandAttributes(ldap_command)

            # store command type
            if not ldap_command[0]:
                ldap_command[0] = dec_line
                #continue

            # extract and store attribute one by one
            extr_attr = dec_line.split(': ')
            if len(extr_attr) == 2:
                cmd_key, cmd_value = extr_attr
                ldap_command[1][cmd_key] = cmd_value
                continue

    logger.debug('Disconnect')
    rfileobj.close()


def stop_app(pidfile, socket=None):
    # STOP PROCESS TASKS
    os.unlink(pidfile)
    if socket:
        os.unlink(args.socket)
    logger.info('Stopped')
    sys.exit(0)


if __name__ == '__main__':
    import argparse
    from importlib import util as importlib_util

    parser = argparse.ArgumentParser()
    parser.add_argument('-conf', required=True,
                        help="settings file where connection are configured")
    parser.add_argument('-bind', required=False, default="127.0.0.1",
                        help="127.0.0.1")
    parser.add_argument('-port', required=False, type=int,
                        help="settings file where connection are configured")
    parser.add_argument('-socket', required=False, default="/tmp/multildap.sock",
                        help="socket to listen to, default: /tmp/multildap.sock"),
    parser.add_argument('-pid', required=False, default="/tmp/multildap.pid",
                        help="socket to listen to, default: /tmp/multildap.pid"),
    parser.add_argument('-uid', required=False, default="openldap",
                        help="socket owner. E.g.: openldap or slapd uid"),
    parser.add_argument('-loglevel', required=False, choices=('INFO',
                                                              'DEBUG',
                                                              'ERROR',
                                                              'WARNING'),
                        default='DEBUG',
                        help="debug"),
    parser.add_argument('-logfile', required=False, #type=argparse.FileType('w'),
                        help="debug")
    parser.add_argument('-dummy', required=False, action="store_true",
                        help="debug")
    args = parser.parse_args()

    # import settings
    spec = importlib_util.spec_from_file_location("settings", args.conf)
    settings = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(settings)

    # logging
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
    if args.logfile:
        logfile = logging.handlers.RotatingFileHandler(filename=args.logfile, maxBytes=2000000, backupCount=100)
        logfile.setFormatter(formatter)
        logger.addHandler(logfile)
        logger_commands.addHandler(logfile)
        logger_client.addHandler(logfile)

    stdout = logging.StreamHandler()
    stdout.setFormatter(formatter)
    logger.setLevel(getattr(logging, args.loglevel))
    logger.addHandler(stdout)

    logger_commands.setLevel(getattr(logging, args.loglevel))
    logger_commands.addHandler(stdout)
    logger_commands.propagate = False

    logger_client.setLevel(getattr(logging, args.loglevel))
    logger_client.addHandler(stdout)
    logger_client.propagate = False

    # prevents double messages printing cause of propagation from handlers to ancestors
    logger.propagate = False

    if args.loglevel == 'DEBUG':
        _LOG_LDAP_REQUEST = 1

    # init ldap client objects globally
    _CONN = [LdapClient(conf) for conf in settings.LDAP_CONNECTIONS.values()]

    # create pid file
    pid = str(os.getpid())
    pidfile = args.pid
    if os.path.isfile(pidfile):
        logger.debug("{} already exists, exiting".format(pidfile))
        sys.exit()
    open(pidfile, 'w').write(pid)
    logger.info("Process run on pid: {}".format(pid))
    # end pidfile

    # register a signal
    sock = None
    gevent.signal(signal.SIGTERM, stop_app, **{'pidfile': pidfile,
                                               'socket': sock})
    gevent.signal(signal.SIGINT, stop_app, **{'pidfile': pidfile,
                                              'socket': sock})

    if args.port:
        # creates a new server on ip:port
        logger.info('Running server on {}:{}'.format(args.bind,
                                                     args.port))
        server = StreamServer((args.bind, args.port), handle)
    else:
        sock = create_socket(args)
        if args.dummy:
            server = StreamServer(sock, handle_debug1)
        else:
            server = StreamServer(sock, handle)


    # start accepting new connections
    server.serve_forever()
