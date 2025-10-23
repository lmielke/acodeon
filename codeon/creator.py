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
        # two representations of the JSON: string and dict
        self.json_string = json_string
        self.data = None
        # json content after parsing
        self.json_path = None
        self.work_file_name = None
        self.content = None
        self.status = None
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
        # we also save the json to json_path for reference
        self.json_path, self.work_file_name = self.get_path(*args, **kwargs)
        self.write_json(*args, **kwargs)
        self.content = self.data.get(sts.json_content)
        self.status = True if self.json_path is not None else False
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

    def get_path(self, *args, pg_name:str, cr_id:str, **kwargs):
        # gets the path from json string
        work_file_name = self.data.get(sts.json_target)
        cr_json_path = os.path.join(
                                        sts.cr_jsons_dir(pg_name), 
                                        sts.cr_json_file_name(work_file_name, cr_id))
        return cr_json_path, work_file_name

    def write_json(self, *args, **kwargs):
        # we save the json into json_path
        with open(self.json_path, "w", encoding="utf-8") as f_json:
            f_json.write(self.json_string)

class IntegrationEngine:
    """
    Handles cleaning and staging of the cr_integration_file content
    extracted from a JSON payload.
    WHY: Separates file staging/cleaning from JSON parsing.
    """

    # Regex to find the mandatory package header
    pkg_header_re = re.compile(r"(#--- cr_op:.*?---#)", re.DOTALL)
    # Regex for markdown code fences (optional language specifier)
    md_fence_re = re.compile(
        r"^\s*```[a-zA-Z]*\n|(\n\s*```\s*$)", re.MULTILINE
    )

    def __init__(self, *args, content: str, work_file_name: str, **kwargs):
        self.raw_content = content
        self.work_file_name = work_file_name
        self.cleaned_content = None
        self.status = None

    def __call__(self, *args, cr_id: str, pg_name: str, **kwargs ) -> "IntegrationEngine":
        self.cleaned_content = self._clean_content(*args, **kwargs)
        self._write_content(*args, **kwargs)
        return self

    def _clean_content(self, *args, **kwargs) -> str:
        """Removes markdown fences and pre-header text."""
        match = self.pkg_header_re.search(self.raw_content)
        content = (
            self.raw_content[match.start() :]
            if match
            else self.raw_content
        )
        content = self.md_fence_re.sub("", content)
        return content.strip()

    def _write_content(self, *args, cr_integration_path:str, **kwargs):
        """Writes the cleaned content to the staged path."""
        print(f"{Fore.GREEN}IntegrationEngine writing: {cr_integration_path = }{Fore.RESET}")
        with open(cr_integration_path, "w", encoding="utf-8") as f:
            f.write(self.cleaned_content)