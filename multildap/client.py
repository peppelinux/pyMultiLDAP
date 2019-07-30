import copy
import importlib
import ldap3
import logging
import json
import re

from . decorators import timeout
from ldap3.core.exceptions import LDAPMaximumRetriesError


logger = logging.getLogger(__name__)


class LdapClient(object):

    def __init__(self, LDAP_SRV_CONF):
        self.conf = LDAP_SRV_CONF
        self.conn = None
        self.server = None
        self.strategy = LDAP_SRV_CONF['connection']['client_strategy']

    def get_response(self, message_id=None, timeout=10):
        if self.strategy in (ldap3.REUSABLE,
                             ldap3.ASYNC):
            # message_id for async strategy
            results = self.conn.get_response(message_id, timeout=timeout)
        else:
            results = self.conn.entries
        return results

    def set_search_filter(self, search_filter):
        self.conf['search']['search_filter'] = search_filter

    def connect(self):
        logger.info('Connecting to {}...'.format(self.conf['server']['host']))
        try:
            self.server = ldap3.Server(**self.conf['server'])
            self.conn = ldap3.Connection(self.server, **self.conf['connection'])
        except LDAPMaximumRetriesError as excp:
            logger.error("Error: {}".format(excp))

    def set_strategy(self, strategy_type):
        if self.conn and strategy_type == self.conn.strategy_type:
            return
        self.conf['connection']['client_strategy'] = strategy_type
        self.connect()
        self.strategy = strategy_type

    def ensure_connection(self):
        search_kwargs = copy.deepcopy(self.conf['search'])
        search_kwargs['size_limit'] = 1
        search_kwargs['connect_timeout'] = self.conf['server']['connect_timeout']
        if self.conn and not self.conn.closed:
            try:
                self.conn.search(**search_kwargs)
            except Exception as excp:
                logger.debug('Connection error: {}...'.format(excp))
                self.connect()
        else:
            self.connect()

    # @timeout(3)
    def search(self, **kwargs):
        self.ensure_connection()
        _kwargs = kwargs if kwargs else self.conf['search']
        timeout = kwargs.get('timeout')
        result = self.conn.search(**_kwargs)
        logger.debug('result [{}]: {}'.format(self.conf['connection']['client_strategy'],
                                              result))
        if timeout:
            return self.get_response(result, timeout=timeout)
        else:
            return self.get_response(result)

    def _decode_elements(self, attr_dict):
        return {k:[e.decode(self.conf['encoding']) if isinstance(e, bytes) else e for e in v]
                for k,v in attr_dict.items() }

    def _as_object(self, res):
        return type('', (object,), list(res.values())[0])()

    def _as_json(self, res):
        return json.dumps(res, indent=2)

    def _as_ldif(self, res):
        ldifs = []
        # import pdb; pdb.set_trace()
        for dn in res:
            ldif = ['dn: {}'.format(dn)]
            for attr in res[dn]:
                if isinstance(res[dn][attr], list):
                    for value in res[dn][attr]:
                        ldif.append('{}: {}'.format(attr, value))
                else:
                    ldif.append('{}: {}'.format(attr, res[dn][attr]))
            ldifs.append('\n'.join(ldif))
        return '\n\n'.join(ldifs)

    def _as_dict(self, res):
        if isinstance(res, dict): return res
        result = dict()
        if not res: return result
        if self.strategy in (ldap3.SYNC, ldap3.RESTARTABLE):
            for entry in res:
                result[entry.entry_dn] = entry.entry_attributes_as_dict
        else:
            # E.g.
            # r[0] = entries,
            # r[1] = {'type': 'searchResDone', 'message': '', 'referrals': None, 'result': 0, 'dn': '', 'description': 'success'}
            for entry in res[0]:
                if not result.get(entry['dn']):
                    result[entry['dn']] = dict()
                result[entry['dn']] = self._decode_elements(entry['raw_attributes'])
        return result

    @staticmethod
    def extract_dn_suffix(from_dn):
        from_dn = re.split("uid=[a-zA-Z0-9\.\-\:\@]*,", from_dn)[1]
        return from_dn

    def _apply_rewrites(self, entries):
        rewritten_entries = {}
        for dn in entries:
            for rule_index in range(len(self.conf['rewrite_rules'])):
                # this, otherwise multiple rules on
                # the same dn will not be overwrited...
                if rewritten_entries.get(dn):
                    entry = rewritten_entries[dn]
                else:
                    entry = entries[dn]
                rewritten_entries[dn] = self.apply_attr_rewrite(entry,
                                                                rule_index)

        if self.conf.get('rewrite_dn_to') and rewritten_entries:
            repl = self.conf['rewrite_dn_to']
            from_dn = self.extract_dn_suffix(dn)
            return { k.replace(from_dn, repl): v for k,v in entries.items()}

        return rewritten_entries

    def get(self, search=None, size_limit=0, format=None, attributes=None):
        _kwargs = copy.copy(self.conf['search'])
        _kwargs['size_limit'] = size_limit
        _kwargs['search_filter'] = search if search else self.conf['search']['search_filter']
        _kwargs['attributes'] = attributes if attributes else self.conf['search']['attributes']
        res = self.search(**_kwargs)
        if not res: return
        entries = self._as_dict(res)

        # Rewrite rules detection
        # TODO: Specialize a private method here :)
        if self.conf.get('rewrite_rules'):
            entries = self._apply_rewrites(entries)
        # END Rewrite rules detection

        # format
        if format:
            if format == 'dict': return entries
            method = '_as_{}'.format(format)
            if hasattr(self, method):
                entries = getattr(self, method)(entries)
        else:
            logger.debug(("[Warning] rewrite rules can only "
                          "be applied with a defined format"))
        return entries

    def apply_attr_rewrite(self, attributes, package_index):
        rule = self.conf['rewrite_rules'][package_index]
        package = importlib.import_module(rule['package'])
        logger.debug('[Rewrite Rule] Apply {}'.format(rule))
        func = getattr(package, rule['name'])
        new_attrs = func(attributes, encoding=self.conf['encoding'],
                         **rule['kwargs'])
        return new_attrs

    # @timeout(3)
    def authenticate(self, user, password, new_connection=False):
        if not self.conf.get('allow_authentication'):
            msg = 'Authentication disabled for [{}]'
            logger.debug(msg.format(self.conf['server']['host']))
            return
        if not self.conn:
            self.ensure_connection()
        _kwargs = copy.copy(self.conf['connection'])
        _kwargs['user'] = user
        _kwargs['password'] = password
        status = False
        try:
            if new_connection:
                server = ldap3.Server(**self.conf['server'])
                status = ldap3.Connection(server, **_kwargs)
            else:
                status = self.conn.rebind(user, password)
            return status
        except Exception as excp:
            msg = 'Authentication error: {}'.format(excp)
            logger.error(msg)
            return status

    def __str__(self):
        return '{} - {} - {}'.format(self.conf['server']['host'],
                                     self.conf['search']['search_base'],
                                     self.conf['search']['search_filter'])

    def __repr__(self):
        return self.__str__()
