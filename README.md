pyLDAP
-----

Configure connections and search paramenters in `settings.py`.


## client.py usage
````
from client import LdapClient
from settings import LDAP_CONNECTIONS

lc = LdapClient(LDAP_CONNECTIONS['SAMVICE'])

# get all the results
lc.get()
````
## client.py usage with loggin and runtime search override
````
import copy
import logging

from client import LdapClient
from settings import LDAP_CONNECTIONS

def repr_result(r):
    if r:
        for i in r[0]: print(i)

logger = logging.getLogger('ldap_client')
logger.setLevel(logging.DEBUG)
stdout = logging.StreamHandler()
stdout.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout.setFormatter(formatter)
logger.addHandler(stdout)

lc = LdapClient(LDAP_CONNECTIONS['SAMVICE'])
kwargs = copy.copy(lc.conf)
kwargs['search']['search_filter'] = "(&(sn=de medici)(givenName=aurora))"
r = lc.search(**kwargs['search'])
# repr_result(r)

# like wildcard
kwargs['search']['search_filter'] = "(&(sn=de marco)(schacPersonalUniqueId=*DMRGPP19M45D7845D))"
r = lc.search(**kwargs['search'])
repr_result(r)
````

## Result in json format
````
# other
import copy
import logging

for i in LDAP_CONNECTIONS:
    lc = LdapClient(LDAP_CONNECTIONS[i])
    print('# Results from: {} ...'.format(lc))
    kwargs = copy.copy(lc.conf)
    r = lc.get(search="(&(sn=aie*)(givenName=isa*))")
    print(r+',') if r else []

    # like wildcard
    r = lc.get(search="(&(sn=de marco)(schacPersonalUniqueId=*DMRGPP345tg86H))")
    print(r+',') if r else []

    kwargs['search']['search_filter'] = "(&(sn=de marco))"
    r = lc.search(**kwargs['search'])

    print('# End {}'.format(i))



````

## ldap_asycio.py example
````
time python ldap_aio.py
````
