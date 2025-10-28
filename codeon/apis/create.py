# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\create.py
from codeon.updater import Updater
from colorama import Fore, Style
import codeon.helpers.printing as printing

def main(*args, api='create', **kwargs):
    """
    Main entry point for the 'create' API.
    """
    r = Updater(*args, api=api, **kwargs)(*args, api=api, **kwargs)
    printing.pretty_dict('create.main.result', r)
    return r