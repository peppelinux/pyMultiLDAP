import copy
import logging

from client import LdapClient
from settings import LDAP_CONNECTIONS


logger = logging.getLogger('ldap_client')
logger.setLevel(logging.DEBUG)
stdout = logging.StreamHandler()
stdout.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout.setFormatter(formatter)
logger.addHandler(stdout)

for i in LDAP_CONNECTIONS:
    lc = LdapClient(LDAP_CONNECTIONS[i])
    print('# Results from: {} ...'.format(lc))
    kwargs = copy.copy(lc.conf)
    r = lc.get(search="(&(sn=aie*)(givenName=isa*))")
    print(r+',') if r else []

    # like wildcard
    r = lc.get(search="(&(sn=de marco)(schacPersonalUniqueId=*DMRGPP83*))")
    print(r+',') if r else []

    kwargs['search']['search_filter'] = "(&(sn=de marco))"
    r = lc.search(**kwargs['search'])

    print('# End {}'.format(i))
