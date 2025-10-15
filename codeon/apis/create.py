# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\create.py
from codeon.updater import Updater
from colorama import Fore, Style


def main(*args, api='create', **kwargs):
    """
    Main entry point for the 'create' API.
    """
    r = Updater(*args, api=api, **kwargs)(*args, api=api, **kwargs)
    print(f"{Fore.GREEN}create.main:{Fore.RESET} {r.status_dict = }")
    return r.status_dict