# parsers.py

import re
import textwrap
from abc import ABC, abstractmethod
# Removed: from typing import Optional, List, Tuple

import libcst as cst
from colorama import Fore, Style

import codeon.settings as sts
# Updated: Import constants and classes from headers
from codeon.headers import UnitCrHeads, PackageCrHeads, CR_OPS, CR_TYPES


class CSTParserBase(ABC):
    """Base class for CST parsers that read and prepare a source file."""

    def __init__(self, *args, **kwargs):
        self.source_text = ""
        self.V = Validations()
        self.body = None

    def __call__(self, *args, **kwargs) -> None:
        self.read_source(*args, **kwargs)
        self.body = self.parse(*args, **kwargs)

    def read_source(self, *args, source_path: str, **kwargs) -> None:
        with open(source_path, encoding="utf-8") as f:
            self.source_text = f.read()

    def parse(self, *args, **kwargs) -> cst.Module:
        """Returns the parsed CST tree of the source_text file."""
        return cst.parse_module(self.source_text)


class CSTSource(CSTParserBase):
    """Parses a source_text Python file into a CST Module."""

    pass


class CSTDelta(CSTParserBase):
    """
    Parses an cr_integration_file for an optional package-level operation
    and a list of executable module-level operations.
    """

    def parse(self, *args, **kwargs) -> tuple:
        """Parses both package and unit cr-headers from the source text."""
        pg_op = self._extract_pg_op(*args, **kwargs)
        module_ops = self._extract_module_ops(*args, **kwargs)
        return pg_op, module_ops

    def _extract_pg_op(self, *args, **kwargs) -> PackageCrHeads | None:
        """
        Finds and parses a single package cr-header, if present.
        NOTE: We are matching with re.findall but only using the first match.
        """
        matches = re.compile(sts.pg_header_regex, re.MULTILINE).findall(self.source_text)
        if len(matches) != 1:
            # Must be exactly one package header. If not, return None/raise assert.
            # Choosing to assert based on existing code structure
            assert len(matches) == 1, "Expected exactly one package cr_op header in line 0."
        
        op = PackageCrHeads()
        op(head=matches[0].strip())
        return op

    def _extract_module_ops(self, *args, **kwargs) -> list:
        """Extracts all module-level operations from the source text."""
        ops = []
        for head, body in re.compile(sts.unit_header_regex, re.DOTALL).findall(self.source_text):
            body_node = self._parse_body(body)
            op = UnitCrHeads()
            op(head=head.strip())
            validated_op = self.V._validate_op(op, head, body_node)
            ops.append((validated_op, body_node))
        return self.V._validate_ops(ops, *args, **kwargs)

    def _parse_body(self, code: str) -> cst.CSTNode | None:
        code = textwrap.dedent(code.replace("\u00a0", " ")).strip()
        try:
            return cst.parse_module(code).body[0]
        except (cst.ParserSyntaxError, IndexError):
            return None


class Validations:

    def _validate_op(self, op: UnitCrHeads, head: str, node: cst.CSTNode, *args, **kwargs) -> UnitCrHeads:
        """Tries to create and validate an UnitCrHeads object. Halts on failure."""
        try:
            # Use string constants from headers.py/CR_OPS
            req_targets = CR_OPS
            req_nodes = tuple(op for op in CR_OPS if op != 'remove') # insert_before, insert_after, replace

            if op.cr_op in req_targets and op.cr_type != "import" and not op.cr_anc:
                raise ValueError(f"Op '{op.cr_op}' requires a 'cr_anc'.")
            if op.cr_op in req_nodes and node is None:
                raise ValueError(f"Op '{op.cr_op}' requires a code block.")
            if op.cr_op == "remove" and node is not None:
                raise ValueError("Op 'remove' must not have a code block.")
            return op
        except (ValueError, AttributeError) as e:
            print(
                f"{Fore.RED}FATAL ERROR in cr_integration_file:{Style.RESET_ALL}\n"
                f"Invalid cr_op header or body: '{head}'\n"
                f"{e}\n"
                f"Halting execution."
            )
            exit(1)

    def _validate_ops(self, ops: list, *args, api, verbose: int = 0, **kwargs) -> list:
        if not ops and api != 'create':
            print(  f"{Fore.RED}parsers.Validations._validate_ops Error: "
                    f"No valid operations found in ops_file!{Fore.RESET}")
            return []
        if verbose:
            print(f"{Fore.GREEN}Parsed {len(ops)} ops from ops_file.{Style.RESET_ALL}" )
        return ops