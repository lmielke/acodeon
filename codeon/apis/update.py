# C:\Users\lars\python_venvs\packages\acodeon\codeon\apis\update.py
from colorama import Fore, Style
from codeon.updater import Updater


def main(*args, **kwargs):
    """
    Continuously runs the update process, collecting a status dict for each run.
    """
    update_results = []
    updater = Updater(*args, **kwargs)

    while status_dict := updater.run(*args, **kwargs):
        update_results.append(status_dict)

    if update_results:
        print(
            f"\n{Fore.GREEN}Success: "
            f"Completed {len(update_results)} updates.{Style.RESET_ALL}"
        )
    else:
        print(f"\n{Fore.YELLOW}No updates were applied.{Style.RESET_ALL}")

    return update_results