# entry_point.py
# this is an example api for codeon

import codeon.settings as sts
from codeon.prompter import Prompter

def prompt(*args, **kwargs):
    p = Prompter(*args, **kwargs)
    return p(*args, **kwargs)

def main(*args, **kwargs):
    """
    All entry points must contain a main function like main(*args, **kwargs)
    """
    return prompt(*args, **kwargs)