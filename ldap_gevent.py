import gevent
from gevent import monkey; monkey.patch_all()

from client import LdapClient
from settings import LDAP_CONNECTIONS

result_set = []
LDAP_SERVERS = [LdapClient(conf) for conf in LDAP_CONNECTIONS.values()]

jobs = [gevent.spawn(conn.get) for conn in LDAP_SERVERS]
gevent.joinall(jobs, timeout=2)
for job in jobs:
    print(job.value)
