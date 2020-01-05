pyMultiLDAP
-----

pyMultiLDAP can gather data from multiple LDAP servers, can do data aggregation and manipulation with rewrite rules.
pyMultiLDAP can act also as a proxy server, behind openldap's slapd-sock backend or any custom implementation.

### Features

- LDAP client to many servers as a single one;
- Custom functions to manipulate returning data (rewrite rules);
- Export data in python dictionary, json or ldiff format;
- Proxy Server, exposing a server daemon usable with [slapd-sock backend](https://www.openldap.org/software/man.cgi?query=slapd-sock).

pyMultiLDAP doesn't write to LDAP servers, it just handle readonly data.
It's also used to automate smart data processing on-the-fly.

See `example/settings.py.example` and `multildap/attr_rewrite.py` to understand how to configure and extend it.

### Tested on

- Debian9;
- Debian10.

### Setup
Configure multiple connections and search paramenters in `settings.py`.

Install
````
git clone https://github.com/peppelinux/pyMultiLDAP.git
cd pyMultiLDAP
pip install -r requirements
python3 setup.py install
````

or use pipy [WIP]

````
pip install pyMultiLDAP
````

#### LdapClient Class usage
````
from multildap.client import LdapClient
from settings import LDAP_CONNECTIONS

lc = LdapClient(LDAP_CONNECTIONS['SAMVICE'])

# get all the results
lc.get()

# apply a filter
lc.get(search="(&(sn=de marco)(schacPersonalUniqueId=*DMRGPP83*))")
````

##### Search and get

See `examples/run_test.py`.

Difference between `.search` and `.get`:
- *search* relyies on connection configuration and returns result as it come (raw);
- *get* handles custom search filter and retrieve result as dictionary, json, ldif or python object format. It also apply rewrite rules.

````
import copy

from multildap.client import LdapClient
from settings import LDAP_CONNECTIONS

lc = LdapClient(LDAP_CONNECTIONS['DEFAULT'])

kwargs = copy.copy(lc.conf)
kwargs['search']['search_filter'] = "(&(sn=de medici)(givenName=aurora))"
r = lc.search(**kwargs['search'])
````

#### Results in json format
````
from multildap.client import LdapClient
from . settings import LDAP_CONNECTIONS


for i in LDAP_CONNECTIONS:
    lc = LdapClient(LDAP_CONNECTIONS[i])
    print('# Results from: {} ...'.format(lc))

    # get all as defined search_filter configured in settings connection
    # but in json format
    r = lc.get(format='json')
    print(r)

    # set a custom search as method argument
    r = lc.get(search="(&(sn=de marco)(schacPersonalUniqueId=*DMRGPP345tg86H))", format='json')
    print(r)

    print('# End {}'.format(i))
````

#### Run the server

Network address
````
multildapd.py -conf settings.py -port 1234
````

Unix domain socket (for slapd-sock backend)
````
multildapd.py -conf ./settings.py -loglevel "DEBUG" -socket /var/run/multildap.sock -pid /var/run/multildap.pid -uid openldap
````

Dummy test without any ldap client connection configured, just to test slapd-sock:
````
multildapd.py -conf ./settings.py -dummy -loglevel "DEBUG" -socket /var/run/multildap.sock -pid /var/run/multildap.pid
````

Test Unix domain socket from cli
````
nc -U /tmp/multildap.sock
````

#### Interfacing it with OpenLDAP slapd-sock

The  [Slapd-sock](https://www.openldap.org/software/man.cgi?query=slapd-sock)
 backend  to  slapd  uses  an external program to handle
 queries. This makes it
 possible to have a pool of processes, which persist  between  requests.
 This  allows  multithreaded operation and a higher level of efficiency.
 Multildapd  listens  on  a  Unix  domain  socket and it must have  been  started  independently;

This  module  may  also  be  used  as  an  overlay on top of some other
 database.  Use as an overlay allows external actions to be triggered in
 response to operations on the main database.

#### Configure slapd-sock as database

Add the module.
````
ldapadd -Y EXTERNAL -H ldapi:/// <<EOF
dn: cn=module,cn=config
objectClass: olcModuleList
cn: module
olcModuleLoad: back_sock.la
EOF
````

Create the database.
````
ldapadd -Y EXTERNAL -H ldapi:/// <<EOF
dn: olcDatabase={4}sock,cn=config
objectClass: olcDbSocketConfig
olcDatabase: {4}sock
olcDbSocketPath: /var/run/multildap.sock
olcSuffix: dc=proxy,dc=testunical,dc=it
olcDbSocketExtensions: binddn peername ssf
EOF
````

Add an Overlay if you want to wrap an existing backend
````
ldapmodify -H ldapi:// -Y EXTERNAL <<EOF
dn: olcOverlay=sock,olcDatabase={1}mdb,cn=config
changetype: add
objectClass: olcConfig
objectClass: olcOverlayConfig
objectClass: olcOvSocketConfig
olcOverlay: sock
olcDbSocketPath: /var/run/multildap/multildap.sock
olcOvSocketOps: bind unbind search
olcOvSocketResps: search
EOF
````

Remember to configure an ACL otherwise only `ldapsearch -H ldapi:// -Y EXTERNAL` as root would fetch ldif.
Remember to add a space char `' '` after every olaAccess line, otherwise you'll get `Implementation specific error(80)`.

````
export BASEDC="dc=testunical,dc=it"

ldapadd -Y EXTERNAL -H ldapi:/// <<EOF
dn: olcDatabase={4}sock,cn=config
changeType: modify
replace: olcAccess
olcAccess: to *
 by dn.exact=gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth manage
 by * break
# the following permits self BIND by users
olcAccess: to dn.subtree="dc=proxy,$BASEDC"
 by self read
 by * break
# the following two permits SEARCH by idp and foreign auth system
olcAccess: to dn.subtree="ou=people,$BASEDC"
 by dn.children="ou=auth,$BASEDC" read
 by self read
 by * break
olcAccess: to dn.subtree="ou=people,$BASEDC"
 by dn.children="ou=idp,$BASEDC" read
 by self read
 by * break
olcAccess: to *
 by anonymous auth
 by * break
EOF
````

Authentication  (BIND) on top of the multildapd must be configured with attribute
`rewrite_dn_to` regarding every connections in the settings.py. If abstent the specified connection will be excluded from authentication.
TODO: _adopt openldap proxy authz statements_.

````
ldapsearch -H ldap://localhost:389 -D "uid=peppe,dc=proxy,dc=testunical,dc=it" -w thatsecret -b 'uid=peppe,dc=proxy,dc=unical,dc=it'
````

#### Hints

See databases currently installed:
- `ldapsearch -Y EXTERNAL -H ldapi:/// -b 'cn=config' -LLL  "olcDatabase=*"`;
- Use `client_strategy = RESTARTABLE` instead of `REUSABLE` in your settings.py for better performances;
- A Backend can not be deleted via ldapdelete/modify until OpenLDAP 2.5 will be released;
- Changing the socket path
````
ldapmodify -Y EXTERNAL -H ldapi:/// <<EOF
dn: olcDatabase={4}sock,cn=config
changetype: modify
replace: olcDbSocketPath
olcDbSocketPath: /var/run/multildap.sock
EOF
````
- Deploy a dummy socket listener with socat, just to debug incoming connection from slapd-sock.

````
socat -s UNIX-LISTEN:/tmp/slapd-sock,umask=000,fork EXEC:"$your_command"
````

#### Other slapd-sock resources:

- [slapsock](https://build.opensuse.org/package/show/home:stroeder:AE-DIR/python-slapdsock)
- [slapd-trigger](https://github.com/jclain/slapd-trigger)
- [ldap.h search scopes](https://github.com/openldap/openldap/blob/master/include/ldap.h#L581)
- [slapd-sock in OpenLDAP ML](https://www.openldap.org/cgi-bin/wilma_glimpse/openldap-technical?query=slapd-sock&Search=Search&errors=0&maxfiles=50&maxlines=10&.cgifields=lineonly&.cgifields=restricttofiles&.cgifields=filelist&.cgifields=partial&.cgifields=case)


#### Todo

- Example configuration with slapd's Proxy Authorization Rules (authzTo: dn.regex:^uid=[^,]*,dc=example,dc=com$);
- Only SEARCH, BIND and UNBIND is usable, other LDAP methods should be implemented;
