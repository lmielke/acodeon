# C:\Users\lars\python_venvs\packages\acodeon\codeon\updater.py
import os, shutil
from colorama import Fore, Style

import codeon.contracts as contracts
from codeon.helpers.collections import temp_chdir
from codeon.helpers.file_info import CrPaths
from codeon.parsers import CSTSource, CSTDelta
from codeon.headers import OP_P
from codeon.creator import JsonEngine, IntegrationEngine
from codeon.transformer import ApplyChangesTransformer
import codeon.settings as sts


class Updater:
    """Orchestrates the create and update refactoring processes."""

    def __init__(self, *args, api: str, **kwargs):
        self.api = api
        self.csts = CSTSource(*args, **kwargs)
        self.cstd = CSTDelta(*args, **kwargs)
        self.status_dict = {}
        self.cr_fields = lambda kwargs: {k: v for k, v in kwargs.items() if k in CrPaths.__dataclass_fields__}
        self.cr_paths = CrPaths(*args, api=api, **self.cr_fields(kwargs))
        self.F = Validator_Formatter()

    def __call__(self, *args, json_string:str=None, **kwargs) -> dict | None:
        """Main execution flow for both 'create' and 'update' APIs."""
        kwargs = contracts.update_params(*args, **kwargs)
        if kwargs.get('work_dir') is None:
            return None
        if json_string is not None:
            kwargs = self.create_from_json_source(*args, json_string=json_string, **kwargs)
        self.status_dict = self.process_cr(*args, **kwargs)
        if self.status_dict is None:
            return None
        self._log_result(*args, status=bool(self.status_dict), **kwargs)
        return self

    def create_from_json_source(self, *args, json_string:str, **kwargs):
        je = JsonEngine(*args, json_string=json_string, **kwargs)(*args, **kwargs)
        if je.status == (False or None):
            return {'status': 'JSON parsing failed or was empty'}
        # 2. Use IntegrationEngine to clean and stage the file
        kwargs.update({'cr_json_path': je.json_path, 'work_file_name': je.work_file_name})
        print(f"{je.work_file_name = }")
        kwargs.update(CrPaths(*args, **self.cr_fields(kwargs)).paths_to_dict())
        ie = IntegrationEngine(*args, content=je.content, **kwargs)(*args, **kwargs)
        return kwargs

    def process_cr(self, *args, work_dir, cr_integration_path, source_path, **kwargs):
        with temp_chdir(work_dir):
            self.csts(*args, source_path=source_path,  **kwargs)
            self.cstd(*args, source_path=cr_integration_path, **kwargs)
            package_op, cr_ops = self.cstd.body
            tf = ApplyChangesTransformer(self.csts.body, cr_ops, *args, package_op=package_op, **kwargs)
            out_code = self.F(self.csts.body.visit(tf).code, *args, **kwargs)
            self._write_output(out_code, *args, source_path=source_path, **kwargs)
        return {
                        'cr_id': kwargs.get('cr_id'),
                        'cr_ops': [op.to_dict() for op, node in cr_ops],
                        'source_path': source_path,
                        'cr_integration_path': cr_integration_path,
                        'package_op': str(package_op.cr_op),
        }

    def _log_result(self, *args, status: bool, hard: bool, **kwargs):
        """Prints the final result to the console."""
        if not status:
            print(f"\n{Fore.RED}Transformation failed.{Style.RESET_ALL}")
            return
        print(f"\n{Fore.GREEN}Transformation complete.{Style.RESET_ALL}")
        if self.api == "update":
            source, target = kwargs.get("source_path"), kwargs.get("source_path")
            if hard:
                print(f"  Overwritten: {source}")
            else:
                print(f"  Original:    {source}\n  Modified:    {target}")
    
    def _write_output(self, code: str, *args, 
        source_path:str, cr_stage_path:str, cr_restore_path:str, hard:bool, **kwargs) -> bool:
        """Writes the final transformed code to the target file path."""
        print(f"{Fore.GREEN}Updater._write_staging:{Fore.RESET} {source_path = }")
        with open(cr_stage_path, "w", encoding="utf-8") as f:
            f.write(code)
        # if source_file is overwritten we first backup the existing file for potential restore
        if hard and source_path:
            shutil.copyfile(source_path, cr_restore_path)
            # then we write the new code
            print(f"{Fore.MAGENTA}Updater._write_to source_path:{Fore.RESET} {source_path = }")
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(code)
            self.cleanup(cr_restore_path, *args, **kwargs)

    def cleanup(self, cr_restore_path:str, *args, **kwargs) -> None:
        _dir, _name = os.path.split(cr_restore_path)
        renamed = os.path.join(_dir, f"#{_name}")
        os.rename(cr_restore_path, renamed)

class Validator_Formatter:
    """
    Keeps output code and, if requested, formats via Black.
    WHY: Wire CLI flag reliably; avoid surprises if Black is absent.
    """

    def __init__(self, *args, **kwargs):
        self.out_code: str = ""

    def __call__(self, code: str, *args, use_black: bool = False, **kwargs) -> str:
        self.out_code = code
        if use_black:
            self._format_with_black(*args, **kwargs)
        return self.out_code

    def _format_with_black(self, *args, verbose: int = 0, **kwargs) -> None:
        import shutil, subprocess
        if not shutil.which("black"):
            if verbose >= 1:
                print("WARNING: --black set, but 'black' not found in PATH.")
            return
        try:
            p = subprocess.run(
                ["black", "-q", "-"],
                input=self.out_code,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if p.returncode == 0 and p.stdout:
                self.out_code = p.stdout
            elif verbose >= 1:
                print("WARNING: black returned non-zero; keeping unformatted code.")
        except Exception as e:
            if verbose >= 1:
                print(f"Error running black: {e}")
