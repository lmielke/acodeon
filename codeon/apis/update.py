# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\update.py

import os
from dataclasses import asdict
from colorama import Fore, Style

import codeon.settings as sts
from codeon.engine import RefactorEngine
from codeon.helpers.file_info import UpdatePaths
import codeon.contracts as contracts
from codeon.helpers.collections import temp_chdir


def _log_result(*args, status: bool, target_path: str, hard: bool, source_path: str, **kwargs):
    """Prints the final result of the transformation to the console."""
    if not status:
        print(f"\n{Fore.RED}Transformation failed.{Style.RESET_ALL}")
        return
    print(f"\n{Fore.GREEN}Transformation complete.{Style.RESET_ALL}")
    if hard:
        print(f"  Overwritten: {source_path}")
    else:
        print(f"  Original:    {source_path}")
        print(f"  Modified:    {target_path}")

def _archive_op_code_file(*args, op_codes_path: str, ch_id: str, **kwargs):
    """Renames the used op-code file by prepending 'op_[ch_id]_'."""
    if not op_codes_path or not os.path.exists(op_codes_path):
        return

    dir, fname = os.path.split(op_codes_path)
    if fname.startswith("op_"):
        return

    new_fname = f"op_{ch_id}_{fname}"
    try:
        os.rename(op_codes_path, os.path.join(dir, new_fname))
    except OSError as e:
        print(f"{Fore.RED}Error archiving op-code file: {e}{Style.RESET_ALL}")


def _update(*args, work_dir:str=None, **kwargs):
    """Orchestrates the refactoring process using a single, unified kwargs dict."""
    if work_dir is None:
        kwargs = contracts.checks(*args, api='update', **kwargs)
    path_fields = UpdatePaths.__dataclass_fields__.keys()
    paths = UpdatePaths(**{k: v for k, v in kwargs.items() if k in path_fields})
    if not paths.is_valid:
        return None
    with temp_chdir(kwargs.get('work_dir')):
        # continue updating
        kwargs.update(asdict(paths))
        if status := RefactorEngine(*args, **kwargs).run(*args, **kwargs):
            _archive_op_code_file(*args, **kwargs)
        else:
            print(f"{Fore.RED}Error: Transformation failed. No changes were made.{Style.RESET_ALL}")
        _log_result(*args, status=status, **kwargs)
    return status

# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\update.py

def _updates(*args, **kwargs):
    """
    Continuously runs the update process until no more op-code files are found.
    """
    update_cnt = 0
    # The walrus operator (:=) assigns the result of _update to 'status'
    # and the loop continues as long as 'status' is not None or False.
    while status := _update(*args, **kwargs):
        update_cnt += 1
    if update_cnt > 0:
        print(f"\n{Fore.GREEN}Success: Completed {update_cnt} updates.{Style.RESET_ALL}")

    return update_cnt > 0  # Return True if any updates were made, False otherwise


def main(*args, **kwargs):
    """Main entry point for the 'update' API."""
    return _updates(*args, **kwargs)