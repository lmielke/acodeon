# cr.py
# this is an example api for codeon

import codeon.settings as sts
from codeon.codeon import Codeon

def cr(*args, **kwargs):
    code = Codeon(*args, **kwargs)
    return code(*args, **kwargs)

def main(*args, **kwargs):
    """
    All entry points must contain a main function like main(*args, **kwargs)
    """
    return cr(*args, **kwargs)