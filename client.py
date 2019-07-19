import copy
import importlib
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
        if self.strategy in (ldap3.REUSABLE,
                             ldap3.ASYNC):
            # message_id for async stragegy
            results = self.conn.get_response(message_id)
        else:
            results = self.conn.entries
        return results

    def set_search_filter(self, search_filter):
        self.conf['search']['search_filter'] = search_filter
    
    def ensure_connection(self):
        search_kwargs = copy.deepcopy(self.conf['search'])
        search_kwargs['size_limit'] = 1
        if not self.conn or not self.conn.search(**search_kwargs):
            logger.info('Connecting to {}...'.format(self.conf['server']['host']))
            server = ldap3.Server(**self.conf['server'])
            self.conn = ldap3.Connection(server, **self.conf['connection'])

    def search(self, **kwargs):
        if self.strategy in (ldap3.REUSABLE, ldap3.ASYNC):
            self.ensure_connection()
        _kwargs = kwargs if kwargs else self.conf['search']
        result = self.conn.search(**_kwargs)
        logger.debug('result [{}]: {}'.format(self.conf['connection']['client_strategy'],
                                              result))
        return self.get_response(result)

    def _decode_elements(self, attr_dict):
        return {k:[e.decode(self.conf['encoding'] if isinstance(e, bytes) else e) for e in v]
                for k,v in attr_dict.items() }

    def _as_json(self, r):
        return json.dumps(r, indent=2)

    def _as_dict(self, res):
        if isinstance(res, dict): return res
        result = dict()
        if not res or not res[0]: return result
        if self.strategy in (ldap3.SYNC, ldap3.RESTARTABLE):
            for entry in res[0]:
                result[entry['dn']] = self._decode_elements(entry['raw_attributes'])
        else:
            for entry in res[0]:
                if not result.get(entry['dn']):
                    result[entry['dn']] = dict()
                result[entry['dn']] = self._decode_elements(entry['raw_attributes'])
        return result

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
        return rewritten_entries
    
    def get(self, search=None, size_limit=0, format=None):
        _kwargs = copy.copy(self.conf['search'])
        _kwargs['size_limit'] = size_limit
        _kwargs['search_filter'] = search if search else self.conf['search']['search_filter']
        r = self.search(**_kwargs)
        if not r: return
        entries = self._as_dict(r)

        # Rewrite rules detection
        # TODO: Specialize a private method here :)
        if self.conf.get('rewrite_rules'):
            entries = self._apply_rewrites(entries)
        # END Rewrite rules detection

        # format
        if format:
            method = '_as_{}'.format(format)
            if hasattr(self, method):
                entries = getattr(self, method)(entries)
        else:
            logger.debug(("[Warning] rewrite rules can only "
                          "be applied with a defined format"))
            entries = r[0]

        return entries

    def apply_attr_rewrite(self, attributes, package_index):
        rule = self.conf['rewrite_rules'][package_index]
        package = importlib.import_module(rule['package'])
        logger.debug('[Rewrite Rule] Apply {}'.format(rule))
        func = getattr(package, rule['name'])
        new_attrs = func(attributes, encoding=self.conf['encoding'],
                         **rule['kwargs'])
        return new_attrs

    def __str__(self):
        return '{} - {} - {}'.format(self.conf['server']['host'],
                                     self.conf['search']['search_base'],
                                     self.conf['search']['search_filter'])

    def __repr__(self):
        return self.__str__()
