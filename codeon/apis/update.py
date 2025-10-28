# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\update.py
import os
from colorama import Fore, Style
from codeon.updater import Updater
from codeon.helpers.collections import temp_chdir
import codeon.helpers.printing as printing


def update(*args, **kwargs):
    """
    Continuously runs the update process, collecting a status dict for each run.
    """
    print(f"{Fore.MAGENTA}## API.UPDATE ##\nwith {os.getcwd() = }{Fore.RESET}")
    update_results = []
    updater = Updater(*args, **kwargs)
    # loop unitl all updates are processed
    r = updater(*args, **kwargs)
    printing.pretty_dict('update.main.result', r)

def main(*args, work_dir:str=os.getcwd(), **kwargs):
    """
    Continuously runs the update process, collecting a status dict for each run.
    """
    if work_dir == os.getcwd():
        print(f"{Fore.YELLOW}WARNING: cwd == {work_dir = } {Fore.RESET}")
    with temp_chdir(work_dir):
        update(*args, work_dir=work_dir, **kwargs)
