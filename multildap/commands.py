import copy
import logging

from multildap.client import LdapClient


logger = logging.getLogger(__name__)


# https://docs.oracle.com/javase/jndi/tutorial/ldap/models/exceptions.html
_CODE_NOSUCHOBJECTEXISTS = 32
_CODE_NOTIMPLEMENTED = 53
_CODE_TIMEOUT = 3
_CODE_OPERATIONERROR = 1
_CODE_INVALIDCREDENTIAL = 49

# RESPONSE TEMPLATES
_ENTRY_TMPL = """{ldifs}"""
_RESULT_TMPL = """

RESULT
code: {code}
info: {text}
"""


class LDAPUnrecognizesCommandAttributes(Exception):
    pass


class LdapCommand(object):

    def __init__(self, ldap_command):
        """
        ldap_command = ['SEARCH', {**attr_kwargs}]
        """
        self.type = ldap_command[0].lower()
        for k,v in ldap_command[1].items():
            setattr(self, k, int(v) if v.isdigit() else v)
        self.command = 'process_{}'.format(self.type)
        logging.debug('LDAPCommand: {}'.format(ldap_command))

    def process(self, ldapclients=[]):
        """
        The commands - except unbind - should output:
              RESULT
              code: <integer>
              matched: <matched DN>
              info: <text>
        where  only RESULT is mandatory, and then close the socket.  The search
        RESULT should be preceded by the entries in  LDIF  format,  each  entry
        followed  by  a  blank  line.   Lines starting with `#' or `DEBUG:' are
        ignored.
        """
        response = ''
        if self.type == 'unbind':
                return ''
        if hasattr(self, self.command):
            try:
                response = getattr(self, self.command.lower())(ldapclients)
            except Exception as excp:
                return _RESULT_TMPL.format(**{'code':_CODE_OPERATIONERROR,
                                              'text': excp})
        else:
            code = _CODE_NOTIMPLEMENTED
            text = 'LDAP command [{}] non implemented yet'.format(self.command,
                                                                  self.type)
        return response


    def process_search(self, ldapclients):
        """
        SEARCH
        msgid: <message id>
        <repeat { "suffix:" <database suffix DN> }>
        base: <base DN>
        scope: <0-2, see ldap.h>
        deref: <0-3, see ldap.h>
        sizelimit: <size limit>
        timelimit: <time limit>
        filter: <filter>
        attrsonly: <0 or 1>
        attrs: <"all" or space-separated attribute list>
        <blank line>
        """
        ldifs = []
        for ldapclient in ldapclients:
            attributes = self.attrs if self.attrsonly else ldapclient.conf['search']['attributes']

            if self.filter == '(objectClass=*)':
                self.filter = ldapclient.conf['search']['search_filter']
                logger.info('FILTER rewritten from {} to {}'.format('(objectClass=*)',
                                                                    self.filter))

            # detect if this search came from a BIND, restrict search to useronly changing the filter
            if self.suffix != ldapclient.conf['search']['search_base']:
                new_filter = '({})'.format(self.binddn.split(',')[0])
                logger.debug('FILTER rewritten from {} to {}'.format(self.filter,
                                                                     new_filter))
                self.filter = new_filter
                # ldapclient.ensure_connection()

            result = ldapclient.get(search = self.filter,
                                    size_limit = self.sizelimit,
                                    attributes = attributes,
                                    format='ldif')
            if result:
                ldifs.append(result)
                logger.debug('SEARCH {} found in {}'.format(self.filter,
                                                            ldapclient))
            else:
                ldifs.append('')
                logger.debug('SEARCH {} not found in {}'.format(self.filter,
                                                                ldapclient))

        ldif = ''.join(ldifs)
        entry_dict = {'ldifs': ldif,
                      #'msgid': self.msgid
                      }

        # produce RESULT data
        result_dict = {
                        #'msgid': self.msgid,
                       'code': 0 if ldifs else _CODE_NOSUCHOBJECTEXISTS,
                       'text': '{} bytes fetched'.format(len(ldif))}

        # TODO: wait for a coherent slapd-sock documentation
        response = ''.join((_ENTRY_TMPL.format(**entry_dict),
                            _RESULT_TMPL.format(**result_dict)))
        return response


    def process_bind(self, ldapclients):
        """
        BIND
        msgid: <message id>
        <repeat { "suffix:" <database suffix DN> }>
        dn: <DN>
        method: <method number>
        credlen: <length of <credentials>>
        cred: <credentials>
        <blank line>
        """
        result = 0
        for ldapclient in ldapclients:
            try:
                username = getattr(self, 'dn')
                from_dn = ldapclient.extract_dn_suffix(username)
                target_username = username.replace(from_dn,
                                                   ldapclient.conf['search']['search_base'])
                logger.info('Authentication: rewrite {} to {} on {}'.format(username,
                                                                            target_username,
                                                                            ldapclient))
                result = ldapclient.authenticate(target_username,
                                                 getattr(self, 'cred'))
                if result:
                    code = 0
                    text = 'Authentication successfull on {}'.format(ldapclient.conf['server']['host'])
                    break
                else:
                    code = _CODE_INVALIDCREDENTIAL
                    text = 'Invalid credentials [allow_create: {}]'.format(ldapclient.conf.get('allow_autentication'))
            except Exception as excp:
                text = '{}'.format(excp)
                code = _CODE_OPERATIONERROR

        result_dict = {'code': code,
                       'text': text
                       #'msgid': self.msgid,
                       }
        response = _RESULT_TMPL.format(**result_dict)
        return response

    def process_unbind(self, ldapclient):
        """
        UNBIND
        msgid: <message id>
        <repeat { "suffix:" <database suffix DN> }>
        <blank line>
        """
        return '\n'
