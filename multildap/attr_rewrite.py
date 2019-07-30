import copy
import re


def decode_iterables(ite, encoding='utf-8'):
    return [e.decode(encoding) if isinstance(e, bytes) else e for e in ite]


def regexp_replace(attrs, regexp='', sub='', encoding='utf-8'):
    d = dict()
    for k,v in attrs.items():
        items = decode_iterables(v, encoding)
        d[k] = [re.sub(regexp, sub, e, re.I) for e in items]
    return d


def replace(attrs, from_str='', to_str='', to_attrs=[], encoding='utf-8'):
    """
    to_attrs -> limits only to specified attributes
    """
    d = dict()
    for k,v in attrs.items():
        items = decode_iterables(v, encoding)
        d[k] = [e.replace(from_str, to_str) for e in items]
    return d

def append(attrs, value='', to_attrs=[], encoding='utf-8'):
    """
    to_attrs -> limits only to specified attributes
    """
    d = dict()
    for k,v in attrs.items():
        items = decode_iterables(v, encoding)
        if value not in d[k]:
            d[k] = v + value
    return d


def add_static_attribute(attrs, name='email', value='', **kwargs):
    if name in attrs and isinstance(attrs[name], list):
        attrs[name].append(value)
    else:
        attrs[name] = [value]
    return attrs


def copy_attribute_value(attrs, from_attr='email', to_attr='',
                         suffix='', prefix='', **kwargs):
    if not from_attr in attrs: return attrs
    v = attrs[from_attr][0] if isinstance(attrs[from_attr], list) else attrs[from_attr]
    value = '{}{}{}'.format(prefix, v, suffix)
    if to_attr in attrs and isinstance(attrs[from_attr], list):
        attrs[to_attr].append(value)
    else:
        attrs[to_attr] = [value]
    return attrs


def map_from_dict(attrs, from_attr='email', to_attr='',
                  suffix='', prefix='', dict_map={}, **kwargs):
    """map from_attr to an external dict_map, if match
       create a new attr or add to an existent one (to_attr).
    """
    # TODO
    pass
