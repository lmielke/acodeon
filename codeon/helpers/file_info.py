# C:\Users\lars\python_venvs\packages\acodeon\codeon\helpers\file_info.py

import os
from dataclasses import dataclass, field
from colorama import Fore, Style
import codeon.settings as sts

# C:\Users\lars\python\venvs\packages\acodeon\codeon\helpers\file_info.py
@dataclass
class UpdatePaths:
    """
    Manages and validates paths for refactoring operations.
    Input paths are overwritten with their resolved, absolute paths upon initialization.
    """

    # --- Inputs (will be overwritten with resolved paths) ---
    source_path: str
    op_codes_path: str | None = None
    hard: bool = False
    project_dir: str = field(default_factory=os.getcwd)
    pg_name: str = "default_package"

    # --- Derived Paths ---
    ch_id: str = field(init=False)
    target_path: str = field(init=False)
    log_dir: str = field(init=False)
    op_code_dir: str = field(init=False)
    is_valid: bool = field(init=False, default=False)

    def __post_init__(self, *args, **kwargs):
        """Generates a ch_id and resolves all necessary paths."""
        self.ch_id = sts.time_stamp()
        self.source_path = self._find_source_path(self.source_path)
        self._mk_target_dirs()
        self.target_path = self._derive_target_path()
        self.op_codes_path = self._find_op_code_file(self.op_codes_path)
        self.is_valid = self._validate()

    def _find_source_path(self, raw_path: str, *args, max_depth: int = 5, **kwargs) -> str | None:
        """Locates the full source path, searching from the project root."""
        if not raw_path: return None
        if os.path.isabs(raw_path) and os.path.isfile(raw_path):
            return raw_path

        parts = raw_path.replace("/", os.sep).split(os.sep)
        search_filename, search_dirs = parts[-1], parts[:-1]

        for root, dirs, files in os.walk(self.project_dir):
            if root[len(self.project_dir) :].count(os.sep) > max_depth:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not any(ign in d for ign in sts.ignore_dirs)]
            if search_filename in files:
                if not search_dirs or root.endswith(os.path.join(*search_dirs)):
                    return os.path.join(root, search_filename)
        return None

    def _mk_target_dirs(self, *args, **kwargs) -> None:
        """Creates the log and op-code directories based on package name."""
        self.log_dir = os.path.join(sts.update_logs_dir, self.pg_name)
        self.op_code_dir = os.path.join(self.log_dir, sts.update_logs_op_code_files_dir_name)
        os.makedirs(self.op_code_dir, exist_ok=True)

    def _derive_target_path(self, *args, **kwargs) -> str | None:
        """Determines the final output path for the modified file."""
        if not self.source_path: return None
        if self.hard: return self.source_path
        temp_dir = os.path.join(self.log_dir, sts.update_logs_temp_dir_name)
        os.makedirs(temp_dir, exist_ok=True)
        return os.path.join(temp_dir, os.path.basename(self.source_path))

    def _find_op_code_file(self, raw_path: str | None, *args, **kwargs) -> str | None:
        """Finds the op-code file, prioritizing a raw path over discovery."""
        if raw_path and os.path.isfile(raw_path):
            return raw_path
        if not self.source_path: return None
        expected_name = os.path.basename(self.source_path)
        expected_path = os.path.join(self.op_code_dir, expected_name)
        return expected_path if os.path.isfile(expected_path) else None

    def _validate(self, *args, **kwargs) -> bool:
        """Validates that source and op-code files exist for the 'update' phase."""
        if not self.source_path:
            print(f"{Fore.RED}Error:{Style.RESET_ALL} Source file not found.")
            return False
        if not self.op_codes_path:
            path_hint = os.path.join(self.op_code_dir, os.path.basename(self.source_path or ""))
            print(f"{Fore.RED}Error:{Style.RESET_ALL} Op-code file not found. Expected at: {path_hint}")
            return False
        return True