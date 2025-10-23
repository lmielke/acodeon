# C:\Users\lars\python_venvs\packages\acodeon\codeon\helpers\file_info.py

import os, shutil
from dataclasses import dataclass, field, asdict
from colorama import Fore, Style
import codeon.settings as sts
import codeon.helpers.printing as printing

# C:\Users\lars\python\venvs\packages\acodeon\codeon\helpers\file_info.py
@dataclass
class CrPaths:
    """
    Manages and validates paths for refactoring operations.
    Input paths are overwritten with their resolved, absolute paths upon initialization.
    """

    # --- Inputs (will be overwritten with resolved paths) ---
    source_path: str | None = None
    work_dir: str | None = None
    hard: bool = False
    project_dir: str = field(default_factory=os.getcwd)
    pg_name: str = ""
    api: str = "create"
    cr_id: str | None = None

    # --- Derived Paths ---
    work_file_name: str | None = None
    cr_prompt_path: str | None = None
    cr_json_path: str | None = None
    cr_integration_path: str | None = None
    cr_stage_path: str | None = None
    cr_restore_path: str | None = None
    temp_dir: str = sts.temp_dir(pg_name)
    cr_prompt_path_exists: bool = False
    cr_json_path_exists: bool = False
    cr_integration_path_exists: bool = False
    cr_stage_path_exists: bool = False
    cr_restore_path_exists: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    def __post_init__(self, *args, cr_id:str=None, **kwargs):
        """Generates a cr_id and resolves all necessary paths."""
        self.cr_id = cr_id if cr_id is not None else sts.time_stamp()
        if self.work_file_name is None and self.source_path:
            self.work_file_name = os.path.basename(self.source_path)
        self.create_cr_paths(*args, **kwargs)
        printing.pretty_dict('CrPaths.__post_init__', self.paths_to_dict(*args, **kwargs))

    def create_cr_paths(self, *args, **kwargs):
        self.source_path, self.work_file_name = CrPaths.find_file_path(
                                                    self.work_file_name, *args,
                                                    project_dir = self.project_dir,
                                                    work_dir = self.work_dir,
                                                    **kwargs)
        self.set_cr_paths(*args, **kwargs)
        self.mk_cr_dirs(*args, **kwargs)
        self.find_cr_files(*args, **kwargs)

    @staticmethod
    def find_file_path(search_file=None, *args, project_dir=None, work_dir=None, max_depth=5, verbose:int=0, **kwargs):
        if search_file is None:
            return None, None
        root_depth = project_dir.count(os.sep)
        file_name = os.path.basename(search_file)
        def ignored(d):
            d = d.strip()
            return any(d == i or d.endswith(i.strip('*')) for i in sts.ignore_dirs)
        for root, dirs, files in os.walk(project_dir, topdown=True):
            if ignored(os.path.basename(root)):
                dirs.clear()
                continue
            if root.count(os.sep) - root_depth >= max_depth:
                dirs.clear()
                continue
            if file_name in files:
                if verbose:
                    print(f"\nfile_info.find_file_path: Found {file_name = } at {root = }")
                return os.path.join(root, file_name), file_name
            dirs[:] = [d for d in dirs if not ignored(d)]
        return None, file_name

    @property
    def cr_paths(self, *args, **kwargs):
        return [p for p in self.__dataclass_fields__ if p.startswith('cr_') and p.endswith('_path')]

    def paths_to_dict(self, *args, **kwargs) -> dict:
        paths = {p: getattr(self, p) for p in self.cr_paths}
        if self.work_file_name:
            paths['work_file_name'] = self.work_file_name
        if self.source_path:
            paths['source_path'] = self.source_path
        printing.pretty_dict('CrPaths.paths_to_dict', paths)
        return paths

    def set_cr_paths(self, *args, **kwargs):
        if not self.work_file_name:
            return False
        # sets all cr paths based on pg_name, work_file_name, and cr_id
        for p in self.cr_paths:
            if getattr(self, p) is not None:
                continue
            _dir, f_name = sts.cr_paths.get(p)                    
            path = os.path.join(_dir(self.pg_name), f_name(self.work_file_name, self.cr_id))
            setattr(self, p, path)

    def mk_cr_dirs(self, *args, **kwargs) -> None:
        """Creates the log and change-request directories based on package name."""
        for p in self.cr_paths:
            cr_path = getattr(self, p)
            if cr_path is not None:
                _dir = os.path.dirname(cr_path)
                if not os.path.isdir(str(_dir)):
                    os.makedirs(_dir, exist_ok=True)

    def find_cr_files(self, *args, **kwargs) -> str | None:
        """Finds the cr_*_files, prioritizing a raw path over discovery."""
        for p in self.cr_paths:
            _path = getattr(self, p)
            if os.path.isfile(str(_path)):
                setattr(self, f"{p}_exists", True)

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
        shutil.copytree(sts.cr_restore_dir(self.pg_name), self.project_dir)
