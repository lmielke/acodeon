#--- cr_op: create, cr_type: file, cr_anc: creator.py, cr_id: 2025-10-08-16-12-30 ---#
import os, re, json, shutil, subprocess
import libcst as cst
from colorama import Fore, Style
from codeon.headers import OP_P
import codeon.settings as sts

from codeon.transformer import ApplyChangesTransformer
from codeon.parsers import CSTSource, CSTDelta


class JsonEngine:
    """
    Progressive JSON recovery: try strict first, then minimal safe repairs.
    WHY: tolerate LLM/paste noise while converging to valid JSON deterministically.
    """

    def __init__(self, *args, json_string: str, cr_json_path:bool=False, **kwargs):
        # two representations of the JSON: string and dict
        self.json_string = json_string
        self.data = None
        # json content after parsing
        self.cr_json_path, self.cr_json_file_exists = cr_json_path, False
        self.work_file_name = None
        self.content = None
        # list of strategies to try in order
        self.strategies = [
            self._strategy_strict_parse,
            self._strategy_find_json_block,
            self._strategy_fix_trailing_commas,
            self._strategy_fix_quotes_and_commas,
        ]

    def __call__(self, *args, **kwargs) -> dict | None:
        # if no json_string provided, skip processing (caller has to condition on this)
        if not self.json_string:
            return self
        self.parse(*args, **kwargs)
        if not self.data:
            return self
        # we also save the json to cr_json_path for reference
        self.cr_json_path, self.work_file_name = self.get_path(*args, **kwargs)
        self.write_json(*args, **kwargs)
        self.content = self.data.get(sts.json_content)
        return self

    def check_file_exists(self, *args, **kwargs) -> bool:
        if os.path.exists(str(self.cr_json_path)):
            print(f"{Fore.MAGENTA}JsonEngine.__call__: JSON path already exists, "
                        f"skipping parsing, loading instead.{Fore.RESET}")
            with open(self.cr_json_path, "r", encoding="utf-8") as f_json:
                self.json_string = f_json.read()

    def parse(self, *args, **kwargs) -> dict | None:
        for s in self.strategies:
            d = s(*args, **kwargs)
            if d is not None and d.get(sts.json_target):
                self.data = d

    def _strategy_strict_parse(self, *args, **kwargs) -> dict | None:
        try:
            return json.loads(self.json_string)
        except json.JSONDecodeError:
            return None

    def _strategy_find_json_block(self, *args, **kwargs) -> dict | None:
        m = re.search(r"\{[\s\S]*\}", self.json_string)
        if not m:
            return None
        prev = self.json_string
        self.json_string = m.group(0)
        d = self._strategy_strict_parse(*args, **kwargs)
        self.json_string = self.json_string if d is not None else prev
        return d

    def _strategy_fix_trailing_commas(self, *args, **kwargs) -> dict | None:
        cleaned = re.sub(r",\s*([\}\]])", r"\1", self.json_string)
        if cleaned == self.json_string:
            return None
        prev = self.json_string
        self.json_string = cleaned
        d = self._strategy_strict_parse(*args, **kwargs)
        self.json_string = self.json_string if d is not None else prev
        return d

    def _strategy_fix_quotes_and_commas(self, *args, **kwargs) -> dict | None:
        s = re.sub(r'(["\]\}])\s*\n\s*(["\[\{])', r"\1,\n\2", self.json_string)
        s = s.replace("'", '"')
        prev = self.json_string
        self.json_string = s
        d = self._strategy_strict_parse(*args, **kwargs)
        self.json_string = self.json_string if d is not None else prev
        return d

    def get_path(self, *args, pg_name:str, cr_id:str, **kwargs):
        # gets the path from json string
        work_file_name = self.data.get(sts.json_target)
        cr_json_path = os.path.join(
                                        sts.cr_jsons_dir(pg_name), 
                                        sts.cr_json_file_name(work_file_name, cr_id))
        return cr_json_path, work_file_name

    def write_json(self, *args, **kwargs):
        # we save the json into cr_json_path
        if os.path.exists(str(self.cr_json_path)):
            print(  f"{Fore.MAGENTA}JsonEngine.write_json: JSON file already exists as "
                    f"{os.path.basename(self.cr_json_path)}, "
                    f"skipping write."
                    f"\nNOTE: Consider writing a new CR, "
                    f"if you want to update.{Fore.RESET}")
        else:
            with open(self.cr_json_path, "w", encoding="utf-8") as f_json:
                f_json.write(self.json_string)
        self.cr_json_file_exists = sts.file_exists_default

class IntegrationEngine:
    """
    Handles cleaning and staging of the cr_integration_file content
    extracted from a JSON payload.
    WHY: Separates file staging/cleaning from JSON parsing.
    """

    def __init__(self, *args, work_file_name: str, content: str=None,
                            cr_integration_file_exists:bool=False,**kwargs):
        assert content or cr_integration_file_exists, (
                    f"{Fore.RED}IntegrationEngine.__init__:{Fore.RESET} "
                    f"either content or cr_integration_file_exists must be set.")
        self.raw_content = content
        self.work_file_name = work_file_name
        self.cleaned_content = None
        self.cr_integration_path = None
        self.cr_integration_file_exists = cr_integration_file_exists

    def __call__(self, *args, cr_id: str, pg_name: str, **kwargs ) -> "IntegrationEngine":
        if self.cr_integration_file_exists:
            print(f"{Fore.MAGENTA}IntegrationEngine.__call__: Integration path "
                        f"already exists, skipping integrating.{Fore.RESET}")
            return self
        self.cleaned_content = self._clean_content(*args, **kwargs)
        self._write_content(*args, **kwargs)
        return self

    def _clean_content(self, *args, **kwargs) -> str:
        """Removes markdown fences and pre-header text."""
        match = re.compile(sts.pg_header_regex, re.DOTALL).search(self.raw_content)
        content = (
            self.raw_content[match.start() :]
            if match
            else self.raw_content
        )
        content = re.compile(sts.md_fence_regex, re.MULTILINE ).sub("", content)
        return content.strip()

    def _write_content(self, *args, cr_integration_path:str, **kwargs):
        """Writes the cleaned content to the staged path."""
        with open(cr_integration_path, "w", encoding="utf-8") as f:
            f.write(self.cleaned_content)
        self.cr_integration_file_exists = sts.file_exists_default


class ProcessEngine:

    def __init__(self, *args, cr_processing_file_exists:bool=False, **kwargs):
        self.csts = CSTSource(*args, **kwargs)
        self.cstd = CSTDelta(*args, **kwargs)
        self.F = Validator_Formatter()
        self.cr_processing_path, self.cr_processing_file_exists = None, cr_processing_file_exists
        self.status_dict = {}

    def __call__(self, *args, work_dir, cr_integration_path, source_path, pg_op:str=None, 
        **kwargs):
        self.csts(*args, source_path=source_path,  **kwargs)
        self.cstd(*args, source_path=cr_integration_path, **kwargs)
        pg_op, cr_ops = self.cstd.body
        self.pg_op = pg_op.cr_op if pg_op else None
        tf = ApplyChangesTransformer(self.csts.body, cr_ops, *args, pg_op=pg_op, **kwargs)
        out_code = self.F(self.csts.body.visit(tf).code, *args, **kwargs)
        self._write_output(out_code, *args, source_path=source_path, **kwargs)
        return self

    def _write_output(self, code: str, *args, 
        source_path:str, cr_processing_path:str, cr_restore_path:str, hot:bool, **kwargs) -> bool:
        """Writes the final transformed code to the target file path."""
        with open(cr_processing_path, "w", encoding="utf-8") as f:
            f.write(code)
        # if source_file is overwritten we first backup the existing file for potential restore
        if hot and source_path:
            shutil.copyfile(source_path, cr_restore_path)
            # then we write the new code
            print(f"{Fore.MAGENTA}Updater._write_to source_path:{Fore.RESET} {source_path = }")
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(code)
            self.cleanup(cr_restore_path, *args, **kwargs)
            self.cr_restore_file_exists = sts.file_exists_default
        self.cr_processing_file_exists = sts.file_exists_default

    def cleanup(self, cr_restore_path:str, *args, **kwargs) -> None:
        _dir, _name = os.path.split(cr_restore_path)
        os.rename(cr_restore_path, os.path.join(_dir, f"#{_name}"))


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
