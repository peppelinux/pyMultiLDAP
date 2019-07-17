import copy
import re


def regexp_replace(attrs):
    return attrs

def replace(attrs, from_str='', to_str='', to_attrs=[], encoding='utf-8'):
    """
    to_attrs -> limits only to specified attributes
    """
    d = dict()
    for k,v in attrs.items():
        items = [e.decode(encoding) if isinstance(e, bytes) else e for e in v]
        d[k] = [e.replace(from_str, to_str) for e in items]
    return d
