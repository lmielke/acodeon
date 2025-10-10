# C:\Users\lars\python_venvs\packages\acodeon\codeon\helpers\file_info.py

import os, shutil
from dataclasses import dataclass, field
from colorama import Fore, Style
import codeon.settings as sts

# C:\Users\lars\python\venvs\packages\acodeon\codeon\helpers\file_info.py
@dataclass
class CrPaths:
    """
    Manages and validates paths for refactoring operations.
    Input paths are overwritten with their resolved, absolute paths upon initialization.
    """

    # --- Inputs (will be overwritten with resolved paths) ---
    source_path: str | None = None
    cr_integration_path: str | None = None
    hard: bool = False
    project_dir: str = field(default_factory=os.getcwd)
    pg_name: str = "default_package"
    api: str = "create"
    cr_id: str | None = None

    # --- Derived Paths ---
    target_path: str = field(init=False)
    temp_dir: str = field(init=False)
    cr_integration_dir: str = field(init=False)
    files_exist: bool = field(init=False, default=False)


    def __post_init__(self, *args, cr_id:str=None, **kwargs):
        """Generates a cr_id and resolves all necessary paths."""
        self.cr_id = cr_id if cr_id is not None else sts.time_stamp()
        self.source_path, self.file_name = CrPaths._find_file_path(
                                                    self.source_path, *args,
                                                    project_dir = self.project_dir, **kwargs)
        self._create_restore_dirs(*args, **kwargs)
        self._mk_target_dirs()
        self.target_path = self._derive_target_path()
        self.cr_integration_path = self._find_cr_cr_file(self.cr_integration_path)
        self.files_exist = self._validate(*args, **kwargs)

    @staticmethod
    def _find_file_path(raw_path: str, *args, project_dir=project_dir, max_depth: int = 5, **kwargs) -> str | None:
        """Locates the full source path, searching from the project root."""
        if not raw_path: return None, None
        parts = raw_path.replace("/", os.sep).split(os.sep)
        search_filename, search_dirs = parts[-1], parts[:-1]
        for root, dirs, files in os.walk(project_dir):
            if root[len(project_dir) :].count(os.sep) > max_depth:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not any(ign in d for ign in sts.ignore_dirs)]
            if search_filename in files:
                return os.path.join(root, search_filename), search_filename
        return None, ""

    def _mk_target_dirs(self, *args, **kwargs) -> None:
        """Creates the log and change-request directories based on package name."""
        self.temp_dir = sts.temp_dir(self.pg_name)
        os.makedirs(self.temp_dir, exist_ok=True)
        self.cr_integration_dir = sts.cr_integration_dir(self.pg_name)
        os.makedirs(self.cr_integration_dir, exist_ok=True)

    def _create_restore_dirs(self, *args, **kwargs) -> None:
        """
        Creates the restore package directory if it doesn't exist.
        NOTE: first resolution action would be a 'git reset --hard'
        This will contain all package coding in case of a git reset not working.
        """
        os.makedirs(sts.restore_files_dir(self.pg_name), exist_ok=True)

    @staticmethod
    def _hard_restore_dirs(self, *args, **kwargs) -> None:
        """
        Runs a restore if a git reset --hard did not work.
        """
        print(f"{Fore.RED}Restoring package from backup...{Style.RESET_ALL}")
        print(  f"{Fore.RED}Before running restore, backup the existing {Fore.RESET}"
                f"{self.project_dir = }")
        confim = input(f"{Fore.YELLOW}Restore will overwrite {self.project_dir = }! "
                        f"(y/n): {Style.RESET_ALL}")
        if confim.lower() == 'y':
            shutil.rmtree(self.project_dir)
        shutil.copytree(sts.restore_files_dir(self.pg_name), self.project_dir)
        
    def _derive_target_path(self, *args, **kwargs) -> str | None:
        """Determines the final output path for the modified file."""
        if not self.source_path: return None
        if self.hard: return self.source_path
        return os.path.join(sts.stage_files_dir(self.pg_name), os.path.basename(self.source_path))

    def _find_cr_cr_file(self, raw_path: str | None, *args, **kwargs) -> str | None:
        """Finds the cr_integration_file, prioritizing a raw path over discovery."""
        if raw_path and os.path.isfile(raw_path):
            return raw_path
        if not self.source_path: return None
        expected_name = os.path.basename(self.source_path)
        expected_path = os.path.join(self.cr_integration_dir, expected_name)
        return expected_path if os.path.isfile(expected_path) else None

    @staticmethod
    def _create_paths(*args, hard, pg_name, package_dir, cr_id, **kwargs) -> str | None:
        """
        Determines the final output path for the modified file.
        """
        # json paths
        json_dir = sts.json_files_dir(pg_name)
        source_path, file_name = CrPaths._find_file_path(*args, **kwargs)
        json_path = os.path.join(json_dir, sts.json_file_name(file_name, cr_id))
        if hard:
            target_path = source_path
        else:
            target_path = os.path.join(sts.stage_files_dir(pg_name), file_name)
        return {   'json_dir': json_dir,
                    'json_path': json_path,
                    'target_path': target_path,
                    'source_path': source_path,
                    'cr_integration_path': os.path.join(sts.cr_integration_dir(pg_name), file_name)
        }

    def _validate(self, *args, **kwargs) -> bool:
        """Validates that source and cr_integration_files exist for the 'update' phase."""
        if not self.cr_integration_path:
            path_hint = os.path.join(self.cr_integration_dir, os.path.basename(self.source_path or ""))
            print(  f"{Fore.YELLOW}CR integration file not found.{Fore.RESET} "
                    f"Expected at: {path_hint.replace(os.path.expanduser('~'), '~')}")
            return False
        return True