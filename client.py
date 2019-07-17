import copy
import ldap3
import logging
import json


logger = logging.getLogger(__name__)


class LdapClient(object):

    def __init__(self, LDAP_SRV_CONF):
        self.conf = LDAP_SRV_CONF
        self.conn = None
        self.strategy = LDAP_SRV_CONF['connection']['client_strategy']
        ldap3.set_config_parameter('DEFAULT_SERVER_ENCODING',
                                   LDAP_SRV_CONF['encoding'])

    def get_response(self, message_id=None):
        if self.conf['connection']['client_strategy'] in (ldap3.REUSABLE,
                                                          ldap3.ASYNC):
            # message_id for async stragegy
            results = self.conn.get_response(message_id)
        else:
            results = self.conn.entries
        return results

    def ensure_connection(self):
        search_kwargs = copy.deepcopy(self.conf['search'])
        search_kwargs['size_limit'] = 1
        if not self.conn or not self.conn.search(**search_kwargs):
            logger.info('Connecting to {}...'.format(self.conf['server']['host']))
            server = ldap3.Server(**self.conf['server'])
            self.conn = ldap3.Connection(server, **self.conf['connection'])


    def search(self, **kwargs):
        self.ensure_connection()
        _kwargs = kwargs if kwargs else self.conf['search']
        result = self.conn.search(**_kwargs)
        logger.debug('result [{}]: {}'.format(self.conf['connection']['client_strategy'],
                                              result))
        return self.get_response(result)

    def _as_json(self, r):
        result = []
        if not r: return result
        if self.strategy in (ldap3.SYNC, ldap3.RESTARTABLE):
            for entry in r:
                result.append(entry.entry_to_json())
        else:
            for entry in r[0]:
                d = {k:[e.decode(self.conf['encoding']) for e in v]
                     for k,v in entry['raw_attributes'].items()}
                out = json.dumps(d, indent=2)
                result.append(out)
        return ','.join(result)

    def get(self, search=None, size_limit=0, format=None):
        _kwargs = copy.copy(self.conf['search'])
        _kwargs['size_limit'] = size_limit
        _kwargs['search_filter'] = search if search else self.conf['search']['search_filter']
        r = self.search(**_kwargs)
        if not r: return
        #logger.debug(json.dumps(r[1]))
        # format
        if format:
            method = '_as_{}'.format(format)
            if hasattr(self, method):
                return getattr(self, method)(r)
        else:
            return r[0]

    def __str__(self):
        return '{} - {} - {}'.format(self.conf['server']['host'],
                                     self.conf['search']['search_base'],
                                     self.conf['search']['search_filter'])

    def __repr__(self):
        return self.__str__()
