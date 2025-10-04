# parsers.py

import re
import textwrap
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

import libcst as cst
from colorama import Fore, Style

from codeon.cr_headers import UnitCrHeads, PackageCrHeads, OP_M, CRTypes


class CSTParserBase(ABC):
    """Base class for CST parsers that read and prepare a source file."""

    def __init__(self, *args, **kwargs):
        self.source_text = ""
        self.V = Validations()
        self.body = None

    def __call__(self, *args, **kwargs):
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

    module_cr_finder = re.compile(r"(#-- cr_op:.*?--#)(.*?)(?=#--|$)", re.DOTALL)
    package_cr_finder = re.compile(r"^(#--- cr_op:.*?---#)", re.MULTILINE)

    def parse(self, *args, **kwargs) -> tuple:
        """Parses both package and unit cr-headers from the source text."""
        self.V.validate_package_cr_header(self.source_text, *args, **kwargs)
        package_op = self._extract_package_op(*args, **kwargs)
        module_ops = self._extract_module_ops(*args, **kwargs)
        return package_op, module_ops

    def _extract_package_op(self, *args, **kwargs) -> Optional[PackageCrHeads]:
        """Finds and parses a single package cr-header, if present."""
        if match := self.package_cr_finder.search(self.source_text):
            op = PackageCrHeads()
            op(head=match.group(1).strip())
            return op
        return None

    def _extract_module_ops(self, *args, **kwargs ) -> List:
        """Extracts all module-level operations from the source text."""
        ops = []
        for head, body in self.module_cr_finder.findall(self.source_text):
            body_node = self._parse_body(body)
            op = UnitCrHeads()
            op(head=head.strip())
            validated_op = self.V._validate_op(op, head, body_node)
            ops.append((validated_op, body_node))
        return self.V._validate_ops(ops, *args, **kwargs)

    def _parse_body(self, code: str) -> Optional[cst.CSTNode]:
        code = textwrap.dedent(code.replace("\u00a0", " ")).strip()
        try:
            return cst.parse_module(code).body[0]
        except (cst.ParserSyntaxError, IndexError):
            return None


class Validations:

    def _validate_op(self, op: UnitCrHeads, head: str, node: Optional[cst.CSTNode], *args, **kwargs) -> UnitCrHeads:
        """Tries to create and validate an UnitCrHeads object. Halts on failure."""
        try:
            req_targets = {OP_M.IB, OP_M.IA, OP_M.RP, OP_M.RM}
            req_nodes = {OP_M.IB, OP_M.IA, OP_M.RP}

            if op.cr_op in req_targets and op.cr_type != CRTypes.IMPORT and not op.cr_anc:
                raise ValueError(f"Op '{op.cr_op.value}' requires a 'target'.")
            if op.cr_op in req_nodes and node is None:
                raise ValueError(f"Op '{op.cr_op.value}' requires a code block.")
            if op.cr_op == OP_M.RM and node is not None:
                raise ValueError("Op 'remove' must not have a code block.")
            return op
        except (ValueError, AttributeError) as e:
            print(f"{Fore.RED}FATAL ERROR in cr_integration_file:{Style.RESET_ALL}\n  {e}")
            print(f"  Header: '{head}'")
            print("Halting execution.")
            exit(1)

    def _validate_ops(self, ops: list, *args, api, verbose: int = 0, **kwargs):
        if not ops and api != 'create':
            print(f"{Fore.RED}parsers.Validations._validate_ops Error: "
                        f"No valid operations found in ops_file!{Fore.RESET}")
            return []
        if verbose:
            print(
                f"{Fore.GREEN}Parsed {len(ops)} ops from ops_file.{Style.RESET_ALL}"
            )
        return ops

    def validate_package_cr_header(self, source_text: str, *args, **kwargs) -> None:
        """Checks if the first non-empty line is a package cr_head."""
        stripped_source = source_text.strip()
        if not stripped_source:
            print(f"{Fore.RED}FATAL ERROR: cr_integration_file is empty.{Style.RESET_ALL}")
            exit(1)

        package_token = PackageCrHeads().start_token
        if not stripped_source.startswith(package_token):
            first_line = source_text.splitlines()[0].strip()
            print(
                f"{Fore.RED}FATAL ERROR: The first line of the cr_integration_file "
                f"must be a package cr_head.{Style.RESET_ALL}"
            )
            print(f"  Expected start: '{package_token}'")
            print(f"  Actual line:    '{first_line}'")
            exit(1)
