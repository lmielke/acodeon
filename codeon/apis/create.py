# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\create.py
from codeon.updater import Updater


def main(*args, **kwargs):
    """Main entry point for the 'create' API."""
    return Updater(*args, **kwargs).run(*args, **kwargs)