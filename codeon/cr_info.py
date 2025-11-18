# C:\Users\lars\python_venvs\packages\acodeon\codeon\cr_info.py

import os, re, shutil, yaml
from dataclasses import dataclass, field, asdict
from colorama import Fore, Style
from codeon.helpers.printing import logprint, Color, MODULE_COLORS
MODULE_COLORS["cr_info"] = Color.MAGENTA

import codeon.settings as sts
import codeon.helpers.collections as collections
import codeon.helpers.printing as printing

# C:\Users\lars\python\venvs\packages\acodeon\codeon\helpers\file_info.py
@dataclass
class CrData:
    """
    Manages and validates paths for refactoring operations.
    Input paths are overwritten with their resolved, absolute paths upon initialization.
    """

    # Inputs include a source and cr instructions
    source_path: str | None = None
    update_source: str | None = None
    update_source_type: str = 'string' # ['file', 'string']
    work_dir: str | None = None
    work_file_name: str | None = None
    pg_name: str | None = None
    project_dir: str = field(default_factory=os.getcwd)
    hot: bool = False
    cr_id: str | None = None
    # Process controll parameter
    api: str = "create" # package cr_op from provided api (mandatory)
    pg_op: str | None = None # package cr_op from cr-header in file (mandatory)
    current_phase: str | None = None # current phase of the cr process
    entry_phase: str | None = None # can be other phase, i.e. json, integration
    up_to_phase: str = sts.phases[-1] # phase to process up to
    cr_implemented: bool = False
    # CR content representations
    string: str | None = None
    prompt_string: str | None = None
    json_string: str | None = None
    integration_string: str | None = None
    # Derived Paths
    temp_dir: str | None = None
    prompt_path: str | None = None
    prompt_file_exists: bool = False
    json_path: str | None = None
    json_file_exists: bool = False
    integration_path: str | None = None
    integration_file_exists: bool = False
    processing_path: str | None = None
    processing_file_exists: bool = False
    restore_path: str | None = None
    restore_file_exists: bool = False
    log_path: str | None = None
    error_path: str | None = None


    def __post_init__(self, *args, **kwargs):
        """Generates a cr_id and resolves all necessary paths."""
        # print(f"{Fore.MAGENTA}CrData.__post_init__ in :{Fore.RESET} {self.pg_name = }")
        if not self.cr_id: self.get_cr_id(*args, **kwargs)
        # print(f"{Fore.MAGENTA}CrData.__post_init__ middle :{Fore.RESET} {self.pg_name = }")
        self.update_data(*args, **kwargs)
        self.mk_cr_dirs(*args, **kwargs)
        self.load_cr_info(*args, **kwargs)
        # print(f"{Fore.MAGENTA}CrData.__post_init__ out :{Fore.RESET} {self.pg_name = }")

    @staticmethod
    def fields(*args, **kwargs):
        assert kwargs, logprint(f"No kwargs provided!", level='error')
        return {k: v for k, v in kwargs.items() if k in CrData.__dataclass_fields__}

    def get_cr_id(self, *args, cr_id:str=sts.session_time_stamp, **kwargs) -> str:
        # when the cr_id is provided as part of a file path, we extract it
        for n, p in self.paths_to_dict(*args, **kwargs).items():
            if file_info := collections.match_file_info(p):
                valid_cr_id, valid_file_name = self._validate_file_info(file_info)
                if valid_cr_id:
                    if self.cr_id:
                        assert file_info.get('cr_id') == self.cr_id, logprint(
                        f"Missmatch {n = }: {file_info = } vs {self.cr_id = }", level='error')
                    cr_id = file_info.get('cr_id')
                    if valid_file_name:
                        self.update_source_type = 'file'
                    break
        self.cr_id = cr_id

    def _validate_file_info(self, file_info, *args, **kwargs) -> dict:
        # Example: file_info = {'cr_id': '2025-10-29-13-23-25', 'file_name': 'codeon.py'}
        valid_cr_id, valid_file_name = False, False
        try:
            cr_id = file_info.get('cr_id')
            if cr_id in sts.test_cr_ids:
                logprint(f"using test {cr_id = }!", level='info')
            else:
                sts.to_dt(cr_id)
            valid_cr_id = True
        except Exception as e:
            logprint(f"{cr_id = } is not a valid datetime!", level='warning')
        try:
            file_name = file_info.get('file_name')
            name, ext = os.path.splitext(file_name)
            if name and (ext in sts.cr_file_name_exts):
                valid_file_name = True
        except Exception as e:
            pass
        return valid_cr_id, valid_file_name

    def get_entry_phase(self, *args, **kwargs) -> str:
        # if entry_phase is provided we start from there
        if self.current_phase is None and self.entry_phase is not None:
            self.current_phase = self.entry_phase
            return self.current_phase
        # otherwise we check which outputs already exist to determine the entry_phase
        for i, phase in enumerate(sts.phases):
            # print(f"{Fore.MAGENTA}CrData.get_entry_phase:{Fore.RESET} Checking {phase = }")
            par_name = f"{phase}_file_exists"
            if getattr(self, par_name):
                if self.entry_phase is None:
                    # the first confirmed (provided) object defines the entry phase
                    self.entry_phase = phase
                self.current_phase = phase
        return self.current_phase

    def mk_cr_dirs(self, *args, **kwargs) -> None:
        """Creates the log and change-request directories based on package name."""
        for n, (_d, _n) in sts.cr_paths.items():
            _dir = _d(self.pg_name)
            if not os.path.isdir(_dir):
                logprint(f"Creating dir: {_dir = }", level='info')
                os.makedirs(_dir, exist_ok=True)

    def load_cr_info(self, *args, verbose:int=0, **kwargs):
        if not self.log_path:
            return
        else:
            self.log_file_exists = True
            with open(self.log_path, 'r') as f:
                cr_info = yaml.safe_load(f)
        self.update_data(*args, **cr_info)

    def log_cr_info(self, *args, verbose:int=0, **kwargs):
        if not self.log_path:
            return
        else:
            with open(self.log_path, 'w') as f: f.write(yaml.dump(self.to_dict()))
            self.log_file_exists = True


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
                    logprint(f"Found {file_name = } at {root = }", level='info')
                return os.path.join(root, file_name), file_name
            dirs[:] = [d for d in dirs if not ignored(d)]
        return False, file_name

    def paths_to_dict(self, *args, **kwargs) -> dict:
        paths = {p: getattr(self, p) for p in self.cr_paths}
        if self.work_file_name:
            paths['work_file_name'] = self.work_file_name
        if self.source_path:
            paths['source_path'] = self.source_path
        if self.update_source_type == 'file':
            paths['update_source'] = self.update_source
        printing.pretty_dict('CrData.paths_to_dict', paths)
        return paths

    @property
    def cr_paths(self, *args, **kwargs):
        return [p for p in self.__dataclass_fields__ if p.endswith('_path')]

    def create_cr_paths(self, *args, work_file_name:str=None, source_path:str=None, pg_name:str=None, **kwargs):
        # printing.pretty_dict('CrData.create_cr_paths \tin', self.to_dict(), color=Fore.CYAN)
        self.work_file_name = self.work_file_name if self.work_file_name is not None else work_file_name
        self.source_path = self.source_path if self.source_path is not None else source_path
        self.pg_name = self.pg_name if self.pg_name is not None else pg_name
        if self.work_file_name is None and self.source_path:
            self.work_file_name = os.path.basename(self.source_path)
        if self.work_file_name is None and self.source_path is None:
            logprint(f"unknown work_file_name and source_path", level='warning')
        elif (self.work_file_name is not None) and not os.path.exists(str(self.source_path)):
            self.source_path, self.work_file_name = CrData.find_file_path(
                                                            self.work_file_name, *args,
                                                            project_dir = self.project_dir,
                                                            work_dir = self.work_dir,
                                                    )
        if self.pg_name is not None and self.work_file_name is not None:
            self.set_cr_paths(*args, **kwargs)
            self.find_cr_files(*args, **kwargs)

    def set_cr_paths(self, *args, **kwargs):
        # sets all cr paths based on pg_name, work_file_name, and cr_id
        self.temp_dir = sts.temp_dir(self.pg_name)
        for p in self.cr_paths:
            if getattr(self, p) is not None:
                continue
            # may require cleanup by source_path
            assert p in sts.cr_paths, \
            logprint(f"Name {p = } not in {sts.cr_paths.keys()}", level='error')
            _dir, f_name = sts.cr_paths.get(p)
            path = os.path.join(_dir(self.pg_name), f_name(self.work_file_name, self.cr_id))
            setattr(self, p, path)
        # If source_path is not found, then it does not exist yet, hence create operation.
        if self.source_path == False and self.integration_path is not None:
            self.source_path = self.integration_path
        if self.error_path is not None:
            sts.error_path = self.error_path

    def find_cr_files(self, *args, **kwargs) -> str | None:
        """Finds the cr_*_files, prioritizing a raw path over discovery."""
        for p in self.cr_paths:
            _path = getattr(self, p)
            setattr(self, f"{p.replace('path', 'file_name')}_exists", os.path.isfile(str(_path)))

    @staticmethod
    def _hot_restore_dirs(self, *args, **kwargs) -> None:
        """
        Runs a restore if a git reset --hot did not work.
        """
        print(f"{Fore.MAGENTA}Restoring package from backup...{Style.RESET_ALL}")
        print(  f"{Fore.MAGENTA}Before running restore, backup the existing {Fore.RESET}"
                f"{self.project_dir = }")
        confim = input(f"{Fore.YELLOW}Restore will overwrite {self.project_dir = }! "
                        f"(y/n): {Style.RESET_ALL}")
        if confim.lower() == 'y':
            shutil.rmtree(self.project_dir)
        shutil.copytree(sts.cr_restore_dir(self.pg_name), self.project_dir)

    def update_data(self, *args, **kwargs):
        """
        Updates all data fields (CrData.__dataclass_fields__) from kwargs provided.
        """
        # printing.pretty_dict('CrData.update_data', self.to_dict(), color=Fore.CYAN)
        # printing.pretty_dict('CrData.update_data', kwargs, color=Fore.BLUE)
        for k, v in kwargs.items():
            if k in self.__dataclass_fields__ and v is not None:
                # print(f"{Fore.MAGENTA}CrData.update_data:{Fore.RESET} Setting {k = } to {v = }")
                setattr(self, k, v)
        self.create_cr_paths(*args, **kwargs)
        self.get_entry_phase(*args, **kwargs)
        self.validate_cr(*args, **kwargs)
        self.log_cr_info(*args, **kwargs)
        return self.to_dict()

    def to_dict(self) -> dict:
        return asdict(self)

    def validate_cr(self, *args, **kwargs):
        # the existing cr_files define the current_phase, so
        # if the current_phase is inital and update_source_type is True, then something must be wrong
        if self.current_phase == 'inital' and self.update_source_type:
            print(  f"{Fore.RED}CrData.validate_cr ERROR: {self.update_source_type = } --> "
                    f"work_file_name: {self.cr_id}_{self.work_file_name} should exist "
                    f"somewhere, but could not be found, check {self.cr_id = }!{Style.RESET_ALL}")
            exit(1)
        # if current_phase is inital then a json_string or intgetration_string must be provided
        # currently only json_string is implemented (might come both in code_string)
        if self.current_phase == 'inital' and not self.json_string and not self.prompt_string:
            print(  f"{Fore.RED}CrData.validate_cr ERROR: {self.current_phase = } --> "
                    f"json_string or cr_..._path must be provided!{Style.RESET_ALL}")
            exit(1)