# cr.py
# this is an example api for codeon

import codeon.settings as sts
import codeon.helpers.printing as printing
from codeon.codeon import Codeon

def cr(*args, verbose:int=0, **kwargs):
    code = Codeon(*args, verbose=verbose, **kwargs)
    r = code(*args, verbose=verbose, **kwargs)
    printing.pretty_dict("cr.result", r)
    return r

def main(*args, **kwargs):
    """
    All entry points must contain a main function like main(*args, **kwargs)
    """
    return cr(*args, **kwargs)