#import gevent

#from gevent import monkey; monkey.patch_all()
from gevent.server import StreamServer

from client import LdapClient
from settings import LDAP_CONNECTIONS


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
        print("< {}".format(line))
    rfileobj.close()

server = StreamServer(('127.0.0.1', 1234), handle) # creates a new server
server.serve_forever() # start accepting new connections
