#--- cr_op: create, cr_type: file, cr_anc: creator.py, cr_id: 2025-10-08-16-12-30 ---#
import os, re, json, shutil, subprocess
import libcst as cst
from colorama import Fore, Style
from codeon.headers import OP_P
import codeon.settings as sts


class JsonEngine:
    """
    Progressive JSON recovery: try strict first, then minimal safe repairs.
    WHY: tolerate LLM/paste noise while converging to valid JSON deterministically.
    """

    def __init__(self, *args, json_string: str, **kwargs):
        self.json_string = json_string
        self.data = None
        self.staged_path = None
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
        # we also save the json to json_path for reference
        self.json_path = self.backup_json(*args, **kwargs)
        # if data is found we save it to cr_integration_dir
        self.staged_path = self.stage_from_json(*args, **kwargs)
        return self

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

    def stage_from_json(self, *args, verbose: int = 0, **kwargs ) -> str | None:
        try:
                        
            cr_integration_file = self.test_path('staging', *args, **kwargs)
            if cr_integration_file == sts.exists_status:
                return sts.exists_status
            with open(cr_integration_file, "w", encoding="utf-8") as f:
                f.write(self.data[sts.json_content])
            if verbose:
                print(f"{Fore.GREEN}Staged: {Style.RESET_ALL}{cr_integration_file = }")
            return cr_integration_file
        except (KeyError, IOError) as e:
            print(f"{Fore.RED}Failed to stage cr_integration_file: "
                  f"{e}{Style.RESET_ALL}")
            return None

    def backup_json(self, *args, **kwargs):
        # we save the json into json_path
        json_path = self.test_path('json', *args, **kwargs)
        if json_path == sts.exists_status:
            return sts.exists_status
        with open(json_path, "w", encoding="utf-8") as f_json:
            f_json.write(self.json_string)
        return json_path

    def test_path(self, phase, *args, cr_id, pg_name, **kwargs):
        out_path = ""
        if phase == 'json':
            files_dir = sts.json_files_dir(pg_name)
            out_path = os.path.join(
                                        files_dir, 
                                        sts.json_file_name(self.data[sts.json_target], cr_id)
                                        )
            if os.path.exists(out_path):
                return sts.exists_status
        elif phase == 'staging':
            files_dir = sts.cr_integration_dir(pg_name)
            out_path = os.path.join(
                        files_dir, 
                        sts.cr_integration_archived_name(self.data[sts.json_target], cr_id)
                                )
            if os.path.exists(out_path):
                return sts.exists_status
            else:
                out_path = os.path.join(files_dir, self.data[sts.json_target])
                if os.path.exists(out_path):
                    return sts.exists_status
        os.makedirs(files_dir, exist_ok=True)
        return out_path