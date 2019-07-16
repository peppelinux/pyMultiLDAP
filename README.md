pyLDAP
-----

This tool was written to handle multiple LDAP sources for data aggregations tasks.


### Setup
Configure multiple connections and search paramenters in `settings.py`.

Install dependencies
````
pip install -r requirements
````

#### LdapClient Class usage
````
from client import LdapClient
from settings import LDAP_CONNECTIONS

lc = LdapClient(LDAP_CONNECTIONS['SAMVICE'])

# get all the results
lc.get()
````

#### client.py usage with logging and runtime search override

See `run_test.py`.

Difference between `.search` and `.get`:
    - *search* relyies on connection configuration and returns result as is;
    - *get* handles custom search filter and can retrieve result as dictionary or json format

````
import copy
import logging

from client import LdapClient
from settings import LDAP_CONNECTIONS


# logging
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
````

#### Results in json format
````
import copy

for i in LDAP_CONNECTIONS:
    lc = LdapClient(LDAP_CONNECTIONS[i])
    print('# Results from: {} ...'.format(lc))

    # get all as defined search_filter configured in settings connection
    # but in json format
    r = lc.get(format='json')
    print(r) if r else ''

    # set a custom search as method argument
    r = lc.get(search="(&(sn=de marco)(schacPersonalUniqueId=*DMRGPP345tg86H))")
    print(r+',') if r else ''

    print('# End {}'.format(i))
````

#### ldap_asycio.py example
````
time python ldap_aio.py
````

#### TODO

- [settings.py] Add a modifier function to remap and rewrite attributes.
