"""
SATOSA microservice that uses an identifier asserted by
the home organization SAML IdP as a key to search an LDAP
directory for a record and then consume attributes from
the record and assert them to the receiving SP.
"""

from ldap3.core.exceptions import LDAPException
from multildap.client import LdapClient

from satosa.micro_services.base import ResponseMicroService
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
        # use mongodb, using sp+user id as key
        #self.attributes = {}

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
        logger.info(msg)
        for conn in self.connections:
            msg = "MultiLDAP connection to: {}".format(conn)
            logger.info(msg)


    def process(self, context, data):

        # Use cache in mongoDB with cache duration of 5min
        #if self.attributes and self.config.get('attributes_cache', None):
            #logger.debug('Attr processor id: {}'.format(id(self)))
            #msg = "MultiLdapAttributeStore found previously fetched attributes"
            #logger.info(msg)
            #return ResponseMicroService.process(self, context, data)

        for name,lc in self.connections.items():
            search_attr = self.config['unique_attribute_to_match']

            # prevent exception on missing attr
            attr_value = data.attributes.get(search_attr, False)
            if not attr_value:
                msg = '{} not found in {}'.format(search_attr, lc)
                logger.debug(msg)
                continue
            if isinstance(attr_value, str):
                attr_value = [attr_value]

            msg = ("MultiLdapAttributeStore searches for {} in {}".format(search_attr, lc))
            logger.info(msg)

            ldapfilter = '({}{}{})'.format(search_attr,
                                           self.config['ldap_filter_operator'],
                                           attr_value[0])
            identity = lc.get(search=ldapfilter, format='dict')
            if not identity: continue

            msg = "MultiLdapAttributeStore matches on {}".format(search_attr)
            logger.info(msg)

            attributes = {}
            for k,v in identity.items():
                k = k.lower()
                if k not in attributes:
                    attributes[k] = v
                    msg = "MultiLdapAttributeStore created: {}".format([e for e in v.keys()])
                    logger.debug(msg)
                # TODO: check this update
                elif k in attributes:
                    attributes[k].update(v)

                data.attributes.update(copy.copy(attributes[k]))
                logger.debug( ''.format(data.attributes))

        return ResponseMicroService.process(self, context, data)
