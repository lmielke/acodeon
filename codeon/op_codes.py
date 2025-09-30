# C:\Users\lars\python_venvs\packages\acodeon\codeon\op_codes.py

import re
import libcst as cst
from enum import Enum
from typing import Optional


class OF(str, Enum):
    """Defines the set of valid operations for the refactoring engine."""

    INSERT_BEFORE = "insert_before"
    INSERT_AFTER = "insert_after"
    REPLACE = "replace"
    REMOVE = "remove"


class OPObjects(str, Enum):
    """Target object to perform the operation on."""

    IMPORT = "import"
    METHOD = "method"
    FUNCTION = "function"
    CLASS = "class"
    RAW = "raw"


class OpCodes:
    """An active object that parses, validates, and formats a single op-code operation."""

    _header_regex = re.compile(
        r"#--\s*op:\s*(?P<op>\w+)"
        r"(?:,\s*obj:\s*(?P<obj>\w+))?"
        r"(?:,\s*target:\s*(?P<target>.+?))?\s*--#"
    )

    def __init__(self, *args, node: Optional[cst.CSTNode] = None, **kwargs):
        self.node = node
        self.op_type: Optional[OF] = None
        self.obj: Optional[OPObjects] = None
        self.target: Optional[str] = None
        self.class_name: Optional[str] = None

    def parse_string(self, *args, header: str, **kwargs):
        """Parses and validates a raw op-code header string."""
        match = self._header_regex.match(header)
        if not match:
            raise ValueError(f"Invalid op-code header format: {header}")

        data = match.groupdict()
        self.op_type = OF(data["op"])
        obj_str = data.get("obj")
        self.obj = OPObjects(obj_str) if obj_str else None

        # The target string is now stripped of leading/trailing whitespace
        target_str = data.get("target")
        self.target = target_str.strip() if target_str else None

        is_method_like = self.target and "." in self.target
        if is_method_like:
            if not self.obj:
                raise ValueError(f"Missing 'obj' field for target '{self.target}'.")
            if self.obj == OPObjects.METHOD:
                self.class_name, self.target = self.target.split(".", 1)

        return self.validate(*args, **kwargs)

    def validate(self, *args, **kwargs):
        """Validates the parsed op-code for logical consistency."""
        ops_req_target = {OF.INSERT_BEFORE, OF.INSERT_AFTER, OF.REPLACE, OF.REMOVE}
        ops_req_node = {OF.INSERT_BEFORE, OF.INSERT_AFTER, OF.REPLACE}

        # Imports don't need a target, they are module-level
        if (
            self.op_type in ops_req_target
            and self.obj != OPObjects.IMPORT
            and not self.target
        ):
            raise ValueError(f"Op '{self.op_type.value}' requires a 'target'.")

        if self.op_type in ops_req_node and self.node is None:
            raise ValueError(f"Op '{self.op_type.value}' requires a code block.")

        if self.op_type == OF.REMOVE and self.node is not None:
            raise ValueError("Op 'remove' must not have a code block.")

        return self

    def create_marker(self, *args, ch_id: str, **kwargs) -> str:
        """Creates the formatted output marker string for insertion into code."""
        target_str = (
            f"{self.class_name}.{self.target}" if self.class_name else self.target
        )
        return (
            f"#-- op: {self.op_type.value}, obj: {self.obj.value if self.obj else 'None'}, "
            f"target: {target_str} --# chid: {ch_id}"
        )