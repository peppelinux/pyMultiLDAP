#import gevent

#from gevent import monkey; monkey.patch_all()
from gevent.server import StreamServer

from client import LdapClient
from settings import LDAP_CONNECTIONS

connections = []


def handle(socket, address):
    print('new connection from {}'.format(address))
    rfileobj = socket.makefile(mode='rb')
    while True:
        line = rfileobj.readline()
        if not line:
            print("client {} disconnected".format(address))
            break
        elif line.strip().lower() == b'quit':
            print("client {} quit".format(address))
            break
        elif line == b'\n': continue
        else:
            socket.sendall(b'recv: '+line)
            result = []
            dec_line = line.decode('utf-8').replace('\n', '')
            for conn in connections:
                conn.set_search_filter('({})'.format(dec_line))
                sf = conn.conf['search']['search_filter']
                socket.sendall(sf.encode())
                try:
                    result.append(conn.get(format='json'))
                except Exception as exp:
                    socket.sendall('{}\n'.format(exp).encode())
                res = ''.join(result) + '\n'
                socket.sendall(res.encode())
        print("< {}".format(line))
    rfileobj.close()

if __name__ == '__main__':
    connections = [LdapClient(conf) for conf in LDAP_CONNECTIONS.values()]
    
    # creates a new server
    server = StreamServer(('127.0.0.1', 1234), handle) 
    # start accepting new connections
    server.serve_forever() 
