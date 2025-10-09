# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\update.py
from colorama import Fore, Style
from codeon.updater import Updater


def main(*args, api='update', **kwargs):
    """
    Continuously runs the update process, collecting a status dict for each run.
    """
    update_results = []
    updater = Updater(*args, api=api, **kwargs)
    # loop unitl all updates are processed
    while r := updater(*args, api=api, **kwargs):
        update_results.append(r.status_dict)
        print(f"{Fore.CYAN}Update processed: {r.status_dict}{Style.RESET_ALL}")

    if update_results:
        print(
            f"\n{Fore.GREEN}Success: "
            f"Completed {len(update_results)} updates.{Style.RESET_ALL}"
        )
    else:
        print(f"\n{Fore.YELLOW}No updates were applied.{Style.RESET_ALL}")

    return update_results