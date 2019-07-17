import copy
import re


def regexp_replace(attrs):
    return attrs

def replace(attrs, from_str='', to_str='', to_attrs=[]):
    """
    to_attrs -> limits only to specified attributes
    """
    d = dict()
    for k,v in attrs.items():
        if isinstance(v, str):
            d[k] = v.replace(from_str, to_str)
        elif isinstance(v, list):
            items = [e.decode('utf-8') if isinstance(e, bytes) else e for e in v]
            d[k] = [e.replace(from_str, to_str) for e in items]
    return d
