pyMultiLDAP
-----

Handle multiple LDAP sources, do data aggregations and manipulation with rewrite rules.

### Why?
I developed this tool for manage data migrations from multiple LDAP server,
aggregate accounts, manipulate data before migrate them to an unique LDAP.
This tool can connect and do specialized query to many servers and apply custom functions to
manipulate datas.

This tool do not write to the destination LDAP server but permit us to handle data
in a way that could be very simple to produce ldif or json files.

See `settings.py.example` and `attr_rewrite.py` for understand how to configure and extend it.

### Setup
Configure multiple connections and search paramenters in `settings.py`.

Install dependencies
````
pip install -r requirements
# or
pip install ldap3
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
- *search* relyies on connection configuration and returns result as it come (raw);
- *get* handles custom search filter and retrieve result as dictionary or json format. It also apply rewrite rules.

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

lc = LdapClient(LDAP_CONNECTIONS['DEFAULT'])

kwargs = copy.copy(lc.conf)
kwargs['search']['search_filter'] = "(&(sn=de medici)(givenName=aurora))"
r = lc.search(**kwargs['search'])
````

#### Results in json format
````
import copy

from client import LdapClient
from settings import LDAP_CONNECTIONS


for i in LDAP_CONNECTIONS:
    lc = LdapClient(LDAP_CONNECTIONS[i])
    print('# Results from: {} ...'.format(lc))

    # get all as defined search_filter configured in settings connection
    # but in json format
    r = lc.get(format='json')
    print(r+',') if r else ''

    # set a custom search as method argument
    r = lc.get(search="(&(sn=de marco)(schacPersonalUniqueId=*DMRGPP345tg86H))")
    print(r)

    print('# End {}'.format(i))
````

#### ldap_asycio.py example
This is a WIP, probably also a multiprocess example will be done in the future.
````
time python ldap_aio.py
````
