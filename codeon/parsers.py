# parsers.py

# codeon/refactor/parsers.py
"""
Contains parsers for converting source and delta files into structured data.
- CSTSource: Parses a Python source file into a LibCST tree.
- CSTDelta: Parses an 'op-code' file into a list of executable operations.
"""
# C:\Users\lars\python_venvs\packages\acodeon\parsers.py

import re
import textwrap
import libcst as cst
from typing import Optional
from codeon.op_codes import OpCodes
from colorama import Fore, Style


class CSTDelta:
    op_code_match = r"(#--.*?--#)(.*?)(?=#--|$)"

    def __init__(self, *args, op_codes_path: str, **kwargs):
        self.path = op_codes_path
        with open(self.path, encoding="utf-8") as f:
            self.source = f.read()

    def _parse_body(self, code: str) -> Optional[cst.CSTNode]:
        code = textwrap.dedent(code.replace("\u00a0", " ")).strip()
        if not code:
            return None
        try:
            return cst.parse_module(code).body[0]
        except (cst.ParserSyntaxError, IndexError):
            return None

    def _validate_operation(
        self, *, header: str, body_node: Optional[cst.CSTNode]
    ) -> OpCodes:
        """Tries to create and validate an OpCodes object. Halts on failure."""
        try:
            return OpCodes(node=body_node).parse_string(header=header)
        except ValueError as e:
            print(f"{Fore.RED}FATAL ERROR in op-code file:{Style.RESET_ALL}\n  {e}")
            print(f"  Header: '{header}'")
            print("Halting execution.")
            exit(1)

    def parse(self, *args, **kwargs) -> list[OpCodes]:
        ops = []
        op_finder = re.compile(self.op_code_match, re.DOTALL)
        for header, body in op_finder.findall(self.source):
            body_node = self._parse_body(body)
            op = self._validate_operation(header=header.strip(), body_node=body_node)
            ops.append(op)
        return ops


class CSTSource:
    """Parses a source Python file into a CST Module."""

    def __init__(self, *args, source_path: str, **kwargs):
        self.path = source_path
        with open(self.path, encoding="utf-8") as f:
            self.source = f.read()

    def parse(self, *args, **kwargs) -> cst.Module:
        """Returns the parsed CST tree of the source file."""
        return cst.parse_module(self.source)