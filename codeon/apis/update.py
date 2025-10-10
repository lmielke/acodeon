# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\update.py
from colorama import Fore, Style
from codeon.updater import Updater
from codeon.helpers.collections import dict_to_table_v


def main(*args, api='update', **kwargs):
    """
    Continuously runs the update process, collecting a status dict for each run.
    """
    update_results = []
    updater = Updater(*args, api=api, **kwargs)
    # loop unitl all updates are processed
    cnt = 0
    while r := updater(*args, api=api, **kwargs):
        print(f"{dict_to_table_v('DONE API UPDATE.MAIN', r.status_dict)}")
        update_results.append(r.status_dict)
        cnt += 1

    if update_results:
        print(
            f"\n{Fore.GREEN}Success: "
            f"Completed {len(update_results)} updates.{Style.RESET_ALL}"
        )
    else:
        print(f"\n{Fore.YELLOW}No updates were applied.{Style.RESET_ALL}")

    return update_results