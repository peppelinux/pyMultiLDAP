"""
SATOSA microservice that uses an identifier asserted by
the home organization SAML IdP as a key to search an LDAP
directory for a record and then consume attributes from
the record and assert them to the receiving SP.
"""

from ldap3.core.exceptions import LDAPException
from multildap.client import LdapClient

from satosa.micro_services.base import ResponseMicroService
from satosa.logging_util import satosa_logging
from satosa.response import Redirect
from satosa.exception import SATOSAError

import copy
import importlib.util as importlib_util
import logging


logger = logging.getLogger(__name__)


class MultiLdapAttributeStore(ResponseMicroService):

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

        # cache
        self.attributes = {}

        # import settings and loads connections
        spec = importlib_util.spec_from_file_location("settings",
                                                      config['settings_path'])
        settings = importlib_util.module_from_spec(spec)
        spec.loader.exec_module(settings)

        self.config['connections'] = settings.LDAP_CONNECTIONS
        self.connections = {name: LdapClient(conf)
                            for name,conf in
                            settings.LDAP_CONNECTIONS.items()}

        msg = "MultiLDAP Attribute Store microservice initialized"
        satosa_logging(logger, logging.INFO, msg, None)
        for conn in self.connections:
            msg = "MultiLDAP connection to: {}".format(conn)
            satosa_logging(logger, logging.INFO, msg, None)


    def process(self, context, data):
        """
        Default interface for microservices. Process the input data for
        the input context.

        a typical data:
        {'auth_info':
            {'auth_class_ref': 'urn:oasis:names:tc:SAML:2.0:ac:classes:Password',
             'timestamp': '2019-07-31T08:23:04Z',
             'issuer': 'https://idp1.testunical.it/idp/metadata'},
         'requester': 'https://sp1.testunical.it/saml2/metadata/',
         'requester_name': [{'text': None, 'lang': 'en'}],
         'attributes': {'edupersontargetedid': ['971455391c5b7f87ccb1517c54da63ebb705338105900702b0dc27174f395d58'],
                        'edupersonprincipalname': ['mario@testunical.it'],
                        'edupersonscopedaffiliation': ['staff@testunical.it', 'member@testunical.it', 'member@altrodominio.it'],
                        ...
                        }}


        a typical context:
        {'_path': 'Saml2/acs/post',
 'cookie': 'SAML2_PROXY_STATE="_Td6WFoAAATm1rRGAgAhARYAAAB0L..."',
 'internal_data': {'metadata_store': <saml2.mdstore.MetadataStore object at 0x7f79bf5a1208>},
 'request': None,
 'request_authorization': '',
 'state': {'CONSENT': {'filter': ['registeredOffice',
                                  'mobilePhone',
                                  'digitalAddress',
                                   ...]
                       'requester_name': [{'lang': 'en',
                                           'text': 'https://sp1.testunical.it/saml2/metadata/'}]},
           'ROUTER': 'Saml2IDP',
           'SATOSA_BASE': {'requester': 'https://sp1.testunical.it/saml2/metadata/'},
           'SESSION_ID': 'urn:uuid:11878ccc-49d3-48df-92a5-7c8c5963d4d1',
           'Saml2IDP': {'relay_state': '/',
                        'resp_args': {'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
                                      'destination': 'https://sp1.testunical.it/saml2/acs/',
                                      'in_response_to': 'id-KMWPTSgjiBrMbx4zO',
                                      'name_id_policy': '<ns0:NameIDPolicy '
                                                        'xmlns:ns0="urn:oasis:names:tc:SAML:2.0:protocol" '
                                                        'AllowCreate="false" '
                                                        'Format="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent" '
                                                        '/>',
                                      'sp_entity_id': 'https://sp1.testunical.it/saml2/metadata/'}}},
 'target_backend': 'Saml2',
 'target_frontend': None,
 'target_micro_service': None}


        """
        if self.attributes:
            msg = "MultiLdapAttributeStore found previously fetched attributes"
            satosa_logging(logger, logging.INFO, msg, None)
            return ResponseMicroService.process(self, context, data)

        for name,lc in self.connections.items():
            search_attr = self.config['unique_attribute_to_match']
            ldapfilter = '({}={})'.format(search_attr, data.attributes[search_attr][0])
            msg = ("MultiLdapAttributeStore searches for {} in {}".format(search_attr, lc))
            satosa_logging(logger, logging.DEBUG, msg, None)
            identity = lc.get(search=ldapfilter, format='dict')
            if not identity: continue

            msg = "MultiLdapAttributeStore matches on {}".format(search_attr)
            satosa_logging(logger, logging.INFO, msg, None)

            for k,v in identity.items():
                if k not in self.attributes:
                    self.attributes[k] = v
                    msg = "MultiLdapAttributeStore created {}".format(k)
                    satosa_logging(logger, logging.DEBUG, msg, None)
                elif k in self.attributes and not v in self.attributes[k]:
                    self.attributes[k].append(v)
                    msg = "MultiLdapAttributeStore added {}".format(k)
                    satosa_logging(logger, logging.DEBUG, msg, None)

        data.attributes = copy.copy(self.attributes)
        return ResponseMicroService.process(self, context, data)

