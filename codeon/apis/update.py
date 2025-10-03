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


def _update(*args, work_dir: str = None, **kwargs):
    """Orchestrates the refactoring process, returning a status dictionary."""
    if work_dir is None:
        kwargs = contracts.checks(*args, api="update", **kwargs)
        work_dir = kwargs['work_dir']
    print(f"{Fore.GREEN}{kwargs = }{Fore.RESET}")
    path_fields = UpdatePaths.__dataclass_fields__.keys()
    paths = UpdatePaths(**{k: v for k, v in kwargs.items() if k in path_fields})
    if not paths.is_valid:
        return None
    with temp_chdir(work_dir):
        kwargs.update(asdict(paths))
        print(f"{Fore.YELLOW}{kwargs = }{Fore.RESET}")
        status_dict = RefactorEngine(*args, **kwargs).run(*args, **kwargs)
        if status_dict:
            _archive_op_code_file(*args, **kwargs)
        else:
            print(
                f"{Fore.RED}Error: Transformation failed. "
                f"No changes were made.{Style.RESET_ALL}"
            )

        # _log_result expects a boolean status for its console output
        _log_result(*args, status=bool(status_dict), **kwargs)

    return status_dict


def _updates(*args, **kwargs):
    """
    Continuously runs the update process, collecting a status dict for each run.
    """
    update_results = []
    # The walrus operator (:=) assigns the result of _update to 'status_dict'
    # and the loop continues as long as it's not None.
    while status_dict := _update(*args, **kwargs):
        update_results.append(status_dict)

    if update_results:
        print(
            f"\n{Fore.GREEN}Success: "
            f"Completed {len(update_results)} updates.{Style.RESET_ALL}"
        )
    else:
        print(f"\n{Fore.YELLOW}No updates were applied.{Style.RESET_ALL}")

    return update_results  # Return list of status dicts

def main(*args, **kwargs):
    """Main entry point for the 'update' API."""
    return _updates(*args, **kwargs)