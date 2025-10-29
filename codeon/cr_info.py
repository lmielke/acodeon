# C:\Users\lars\python_venvs\packages\acodeon\codeon\cr_info.py

import os, re, shutil, yaml
from dataclasses import dataclass, field, asdict
from colorama import Fore, Style
import codeon.settings as sts
import codeon.helpers.printing as printing

# C:\Users\lars\python\venvs\packages\acodeon\codeon\helpers\file_info.py
@dataclass
class CrData:
    """
    Manages and validates paths for refactoring operations.
    Input paths are overwritten with their resolved, absolute paths upon initialization.
    """

    # --- Inputs (will be overwritten with resolved paths) ---
    source_path: str | None = None
    is_cr_file: str = False # is true when source_path contains a cr_id
    work_dir: str | None = None
    hot: bool = False
    project_dir: str = field(default_factory=os.getcwd)
    pg_name: str | None = None
    api: str = "create" # package cr_op from provided api (mandatory)
    cr_id: str | None = None
    pg_op: str | None = None # package cr_op from cr-header in file (mandatory)
    current_phase: str | None = None # current phase of the cr process
    entry_phase: str | None = None # can be other phase, i.e. cr_json, cr_integration
    up_to_phase: str = sts.phases[-1] # phase to process up to
    cr_entry_source: str | None = None
    json_string: str | None = None
    cr_integration_string: str | None = None
    cr_prompt: str | None = None
    # --- Derived Paths ---
    work_file_name: str | None = None
    cr_prompt_path: str | None = None
    cr_prompt_file_exists: bool = False
    cr_json_path: str | None = None
    cr_json_file_exists: bool = False
    cr_integration_path: str | None = None
    cr_integration_file_exists: bool = False
    cr_processing_path: str | None = None
    cr_processing_file_exists: bool = False
    cr_restore_path: str | None = None
    cr_restore_file_exists: bool = False
    temp_dir: str | None = None
    cr_implemented: bool = False
    cr_log_path: str | None = None


    def __post_init__(self, *args, **kwargs):
        """Generates a cr_id and resolves all necessary paths."""
        # print(f"{Fore.MAGENTA}CrData.__post_init__ in :{Fore.RESET} {self.pg_name = }")
        if not self.cr_id: self.get_cr_id(*args, **kwargs)
        # print(f"{Fore.MAGENTA}CrData.__post_init__ middle :{Fore.RESET} {self.pg_name = }")
        self.update_data(*args, **kwargs)
        self.mk_cr_dirs(*args, **kwargs)
        self.load_cr_info(*args, **kwargs)
        # print(f"{Fore.MAGENTA}CrData.__post_init__ out :{Fore.RESET} {self.pg_name = }")

    def get_cr_id(self, *args, cr_id:str=sts.time_stamp(), **kwargs) -> str:
        # when the cr_id is provided as part of a file path, we extract it
        for n, p in self.paths_to_dict(*args, **kwargs).items():
            if re.search(sts.cr_id_regex, str(p)):
                fr_path = re.search(sts.cr_id_regex, str(p)).group(1)
                if self.cr_id is not None:
                    assert fr_path == self.cr_id, (
                                    f"{Fore.MAGENTA}file_info.get_cr_id ERROR: {Fore.RESET}"
                                    f"cr_id missmatch in {n}: {fr_path = } vs {self.cr_id = }"
                                    )
                cr_id = fr_path
                setattr(self, n, sts.rm_cr_prefix(p, cr_id))
                self.is_cr_file = True if cr_id else False
                break
        else:
            # we check if cr_id is a valid timestamp by converting it to datetime object
            try:
                if cr_id in sts.test_cr_ids:
                    print(f"{Fore.MAGENTA}file_info.get_cr_id Warning: "
                                f"using test {cr_id = }!{Fore.RESET}")
                else:
                    sts.to_dt(cr_id)
            except ValueError:
                print(f"{Fore.YELLOW}file_info.get_cr_id Warning: {cr_id = } is not "
                            f"a valid datetime!")
        self.cr_id = cr_id

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
                print(f"{Fore.MAGENTA}CrData.mk_cr_dirs:{Fore.RESET} Creating dir: {_dir = }")
                os.makedirs(_dir, exist_ok=True)

    def load_cr_info(self, *args, verbose:int=0, **kwargs):
        if not self.cr_log_path:
            return
        else:
            self.cr_log_file_exists = True
            with open(self.cr_log_path, 'r') as f:
                cr_info = yaml.safe_load(f)
        self.update_data(*args, **cr_info)

    def log_cr_info(self, *args, verbose:int=0, **kwargs):
        if not self.cr_log_path:
            return
        else:
            with open(self.cr_log_path, 'w') as f: f.write(yaml.dump(self.to_dict()))
            self.cr_log_file_exists = True

    def create_cr_paths(self, *args, work_file_name:str=None, source_path:str=None, pg_name:str=None, **kwargs):
        # printing.pretty_dict('CrData.create_cr_paths \tin', self.to_dict(), color=Fore.CYAN)
        self.work_file_name = self.work_file_name if self.work_file_name is not None else work_file_name
        self.source_path = self.source_path if self.source_path is not None else source_path
        self.pg_name = self.pg_name if self.pg_name is not None else pg_name
        if self.work_file_name is None and self.source_path:
            self.work_file_name = os.path.basename(self.source_path)
        if self.work_file_name is None and self.source_path is None:
            print(  f"{Fore.YELLOW}CrData.create_cr_paths Warning: "
                    f"unknown work_file_name and source_path.{Fore.RESET}")
        elif (self.work_file_name is not None) and not os.path.exists(str(self.source_path)):
            self.source_path, self.work_file_name = CrData.find_file_path(
                                                            self.work_file_name, *args,
                                                            project_dir = self.project_dir,
                                                            work_dir = self.work_dir,
                                                    )
        # print(f"{Fore.MAGENTA}CrData.create_cr_paths middle:{Fore.RESET} {self.pg_name = }, {self.work_file_name = } ")
        if self.pg_name is not None and self.work_file_name is not None:
            self.set_cr_paths(*args, **kwargs)
            self.find_cr_files(*args, **kwargs)
        # printing.pretty_dict('CrData.create_cr_paths\tout', self.to_dict(), color=Fore.CYAN)

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
                    print(f"\n{Fore.GREEN}file_info.find_file_path:{Fore.RESET} "
                                f"Found {file_name = } at {root = }")
                return os.path.join(root, file_name), file_name
            dirs[:] = [d for d in dirs if not ignored(d)]
        return False, file_name

    @property
    def cr_paths(self, *args, **kwargs):
        return [p for p in self.__dataclass_fields__ if p.startswith('cr_') and p.endswith('_path')]

    def paths_to_dict(self, *args, **kwargs) -> dict:
        paths = {p: getattr(self, p) for p in self.cr_paths}
        if self.work_file_name:
            paths['work_file_name'] = self.work_file_name
        if self.source_path:
            paths['source_path'] = self.source_path
        # printing.pretty_dict('CrData.paths_to_dict', paths)
        return paths

    def set_cr_paths(self, *args, **kwargs):
        # sets all cr paths based on pg_name, work_file_name, and cr_id
        self.temp_dir = sts.temp_dir(self.pg_name)
        # print(f"{Fore.MAGENTA}CrData.set_cr_paths:{Fore.RESET} {self.cr_paths = }")
        for p in self.cr_paths:
            # print(f"{Fore.MAGENTA}CrData.set_cr_paths:{Fore.RESET} Setting {p = }")
            if getattr(self, p) is not None:
                continue
            assert p in sts.cr_paths, print(f"{Fore.MAGENTA}CrData.set_cr_paths ERROR: {p = } "
                                            f"not in {sts.cr_paths.keys() = } {Fore.RESET}")
            _dir, f_name = sts.cr_paths.get(p)
            # print(f"{Fore.MAGENTA}{self.pg_name = }{Fore.RESET}")
            path = os.path.join(_dir(self.pg_name), f_name(self.work_file_name, self.cr_id))
            setattr(self, p, path)
        # If source_path is not found, then it does not exist yet, hence create operation.
        if self.source_path == False and self.cr_integration_path is not None:
            self.source_path = self.cr_integration_path

    def find_cr_files(self, *args, **kwargs) -> str | None:
        """Finds the cr_*_files, prioritizing a raw path over discovery."""
        for p in self.cr_paths:
            _path = getattr(self, p)
            setattr(self, f"{p.replace('path', 'file')}_exists", os.path.isfile(str(_path)))

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
        self.create_cr_paths(*args, **kwargs)
        self.get_entry_phase(*args, **kwargs)
        self.validate_cr(*args, **kwargs)
        self.log_cr_info(*args, **kwargs)
        return self.to_dict()

    def to_dict(self) -> dict:
        return asdict(self)

    def validate_cr(self, *args, **kwargs):
        printing.pretty_dict('CrData.validate_cr', self.to_dict(), color=Fore.CYAN)
        # the existing cr_files define the current_phase, so
        # if the current_phase is inital and is_cr_file is True, then something must be wrong
        if self.current_phase == 'inital' and self.is_cr_file:
            print(  f"{Fore.RED}CrData.validate_cr ERROR: {self.is_cr_file = } --> "
                    f"work_file_name: {self.cr_id}_{self.work_file_name} should exist "
                    f"somewhere, but could not be found, check {self.cr_id = }!{Style.RESET_ALL}")
            exit(1)
        # if current_phase is inital then a json_string or intgetration_string must be provided
        # currently only json_string is implemented (might come both in code_string)
        if self.current_phase == 'inital' and not self.json_string and not self.cr_prompt:
            print(  f"{Fore.RED}CrData.validate_cr ERROR: {self.current_phase = } --> "
                    f"json_string or cr_..._path must be provided!{Style.RESET_ALL}")
            exit(1)