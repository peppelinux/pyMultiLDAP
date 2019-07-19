#! /usr/bin/env python

from twisted.application import service, internet
from twisted.internet import protocol
from ldaptor.config import LDAPConfig
from ldaptor.protocols.ldap.merger import MergedLDAPServer

application = service.Application("LDAP Merger")

configs = [LDAPConfig(serviceLocationOverrides={"": ('host1.unical.it', 389)}),
           LDAPConfig(serviceLocationOverrides={"": ('host2.unical.it', 636)})
           ]
use_tls = [True, True]
factory = protocol.ServerFactory()
factory.protocol = lambda: MergedLDAPServer(configs, use_tls)
mergeService = internet.TCPServer(3899, factory)
mergeService.setServiceParent(application)
