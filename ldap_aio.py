# https://www.pythonsheets.com/notes/python-asyncio.html
import asyncio

from client import LdapClient
from settings import LDAP_CONNECTIONS

result_set = []
LDAP_SERVERS = []

async def get_result(lc):
    await asyncio.sleep(0.001)
    return lc.get()

async def get_server(CONF):
    return LdapClient(CONF)

async def ensure_connection(lc):
    lc.ensure_connection()

async def connect(lc_id: int):
    CONF = list(LDAP_CONNECTIONS.keys())[lc_id]
    lc = await get_server(LDAP_CONNECTIONS[CONF])
    # LDAP_SERVERS.append(lc)
    print('Connectign and gathering {} [{}]'.format(lc, CONF))
    await ensure_connection(lc)
    try:
        result = await get_result(lc)
        result_set.extend(result[0])
        print('Get {} results from {}'.format(len(result[0]), lc))
    except Exception as e:
        print('-- Fail to connect to {} [{}]'.format(lc, CONF))
        print(e)

async def main():
    await asyncio.gather(*(connect(n) for n in range(len(LDAP_CONNECTIONS.keys()))))
    print('Done')

if __name__ == '__main__':
    asyncio.run(main())
    print(len(result_set))
