import copy
import logging
import sys

from importlib import util as importlib_util
from multildap.client import LdapClient

spec = importlib_util.spec_from_file_location("settings", "settings.py")
settings = importlib_util.module_from_spec(spec)
spec.loader.exec_module(settings)


for i in settings.LDAP_CONNECTIONS.values():
    lc = LdapClient(i)
    # print('# Results from: {} ...'.format(lc))
    # kwargs = copy.copy(lc.conf)
    # r = lc.get(search="(&(sn=aie*)(givenName=isa*))")
    # print(r)

    # like wildcard
    # r = lc.get(search="(&(sn=de marco)(schacPersonalUniqueId=*DMRGPP83*))")
    # print(r)

    # using search method with overload of configuration
    #kwargs['search']['search_filter'] = "(&(sn=de marco))"
    #r = lc.search(**kwargs['search'])

    lc.set_strategy('RESTARTABLE')
    print('# ', lc.strategy)
    print('# as DICT')
    r = lc.get(format='dict')
    print(r) if r else ''
    print()

    r = lc.get(format='json')
    print('# as JSON')
    print(r) if r else ''
    print()

    lc.set_strategy('REUSABLE')
    print('# ', lc.strategy)
    print('# as DICT')
    r = lc.get(format='dict')
    print(r) if r else ''
    print()

    r = lc.get(format='json')
    print('# as JSON')
    print(r) if r else ''
    print()

    # get result in original format
    # this won't apply rewrite rules
    print('# as ORIGNAL')
    r = lc.get()
    print(r) if r else ''
    print()

    print('# as LDIF')
    r = lc.get(format='ldif')
    print(r) if r else ''
    print()

    print('# End')
