# C:\Users\lars\python_venvs\packages\acodeon\codeon\updater.py
import os
from dataclasses import asdict
from colorama import Fore, Style

import codeon.contracts as contracts
from codeon.helpers.collections import temp_chdir
from codeon.helpers.file_info import UpdatePaths
from codeon.creator import JsonEngine, CreateEngine
from codeon.engine import RefactorEngine


class Updater:
    """Orchestrates the create and update refactoring processes."""

    def __init__(self, *args, api: str, **kwargs):
        self.api = api

    def run(self, *args, **kwargs) -> dict | None:
        """Main execution flow for both 'create' and 'update' APIs."""
        kwargs = contracts.checks(*args, **kwargs)
        work_dir = kwargs["work_dir"]
        path_fields = UpdatePaths.__dataclass_fields__.keys()
        paths = UpdatePaths(**{k: v for k, v in kwargs.items() if k in path_fields})

        if not paths.is_valid and self.api == "update":
            return None

        status_dict = None
        with temp_chdir(work_dir):
            kwargs.update(asdict(paths))
            if self.api == "create":
                staged_path = self._stage_from_json(*args, **kwargs)
                if not staged_path:
                    return None
                path_updates = UpdatePaths._create_paths(staged_path, **kwargs)
                kwargs.update(path_updates)
                status_dict = CreateEngine(*args, **kwargs).run(*args, **kwargs)
            else:  # 'update' api
                status_dict = RefactorEngine(*args, **kwargs).run(*args, **kwargs)

        if status_dict:
            self._archive_cr_cr_file(*args, **kwargs)
        self._log_result(*args, status=bool(status_dict), **kwargs)
        return status_dict

    def _stage_from_json(self, *args, cr_integration_dir: str, verbose:int=0, **kwargs) -> str | None:
        """Parses a JSON string and writes the content to a temporary cr_integration_file."""
        data = JsonEngine().parse(*args, **kwargs)
        if not data:
            print(f"{Fore.RED}Failed to parse JSON string.{Style.RESET_ALL}")
            return None
        try:
            target_path = os.path.join(cr_integration_dir, data["target"])
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(data["code"])
            if verbose:
                print(f"{Fore.GREEN}Staged cr_integration_file: {target_path}{Style.RESET_ALL}")
            return target_path
        except (KeyError, IOError) as e:
            print(f"{Fore.RED}Failed to stage cr_integration_file: {e}{Style.RESET_ALL}")
            return None

    def _archive_cr_cr_file(self, *args, cr_integration_path: str, ch_id: str, **kwargs):
        """Renames the cr_integration_file by prepending 'cr_[ch_id]_'."""
        if not all([cr_integration_path, os.path.exists(cr_integration_path)]):
            return
        dir, fname = os.path.split(cr_integration_path)
        if not fname.startswith("cr_"):
            os.rename(cr_integration_path, os.path.join(dir, f"cr_{ch_id}_{fname}"))

    def _log_result(self, *args, status: bool, hard: bool, **kwargs):
        """Prints the final result to the console."""
        if not status:
            print(f"\n{Fore.RED}Transformation failed.{Style.RESET_ALL}")
            return
        print(f"\n{Fore.GREEN}Transformation complete.{Style.RESET_ALL}")
        if self.api == "update":
            source, target = kwargs.get("source_path"), kwargs.get("target_path")
            if hard:
                print(f"  Overwritten: {source}")
            else:
                print(f"  Original:    {source}\n  Modified:    {target}")