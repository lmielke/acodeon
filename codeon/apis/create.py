# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\create.py
from codeon.updater import Updater


def main(*args, api='create', **kwargs):
    """
    Main entry point for the 'create' API.
    """
    r = Updater(*args, api=api, **kwargs)(*args, api=api, **kwargs)
    print(f"{r.status_dict = }")
    return r.status_dict