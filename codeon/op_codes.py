# C:\Users\lars\python_venvs\packages\acodeon\codeon\op_codes.py

import os, re, yaml
from enum import Enum
from typing import Optional
from dataclasses import dataclass, asdict
from colorama import Fore, Style


@dataclass
class OP_CODE_FIELDS:
    OP_CODE: str = "op_code"
    OBJ: str = "obj"
    TARGET: str = "target"
    INSTALL: str = "install"

    def to_dict(self) -> dict:
        return asdict(self)


class OP_M(str, Enum):
    """Defines the set of valid module operations for the refactoring engine."""
    IB, IA, RP, RM = "insert_before", "insert_after", "replace", "remove"


class OP_P(str, Enum):
    """Defines the set of valid package (file system) operations."""
    UPDATE, CREATE, REMOVE = "update", "create", "remove"


class OP_S(str, Enum):
    """Defines the set of valid system operations."""
    INSTALL, UNINSTALL = "install", "uninstall"


class OPObjects(str, Enum):
    """Target object to perform the operation on."""
    IMPORT, METHOD, FUNCTION, CLASS, RAW, FILE = (
        "import", "method", "function", "class", "raw", "file"
    )


class OpCodes:
    """Represents the state of a parsed op-code header using YAML parsing."""

    def __init__(self, *args, **kwargs):
        """Initializes all potential op-code fields to None."""
        self.field_order = list(OP_CODE_FIELDS().to_dict().values())
        for field in self.field_order:
            setattr(self, field, None)
        self.start_token, self.end_token = "#-- ", " --#"
        self._enum_map = {"op_code": OP_M, "obj": OPObjects}

    def load_string(self, *args, head: str, **kwargs):
        """Loads and parses an op-code header string."""
        content_str = head[len(self.start_token) : -len(self.end_token)].strip()
        data = yaml.safe_load("\n".join(p.strip() for p in content_str.split(",")))
        assert isinstance(data, dict), "Parsed op-code header is not a dictionary."
        return self.parse_data(data, *args, **kwargs)

    def parse_data(self, data: dict, *args, **kwargs):
        """Validates and assigns data from a parsed dictionary to the instance."""
        unrecognized = {}
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, self.validate_value(key, value))
            else:
                unrecognized[key] = value
        return unrecognized

    def validate_value(self, key: str, value):
        """Validates a single value against its expected type or enum."""
        if key in self._enum_map:
            try:
                return self._enum_map[key](value)
            except ValueError:
                valid = [e.value for e in self._enum_map[key]]
                raise ValueError(f"Invalid value '{value}' for '{key}'. Use one of: {valid}")
        if key == "install" and not isinstance(value, bool):
            raise ValueError(f"Field 'install' must be a boolean (True/False).")
        return value

    def validate_state(self, *args, **kwargs):
        """
        Validates the cross field state of the instance. For example, when obj is an import, 
        then target must be a valid import statement.
        """
        if self.obj == OPObjects.IMPORT and self.target:
            import_pattern = r"^(import\s+\w+|from\s+\w+(\.\w+)*\s+import\s+\w+)$"
            if not re.match(import_pattern, self.target.strip()):
                raise ValueError(f"Invalid import statement in target: '{self.target}'")
        
    def to_dict(self, *args, **kwargs) -> dict:
        """Internal method to build a dictionary from the instance's state."""
        data = {}
        for field in self.field_order:
            value = getattr(self, field, None)
            if value is not None:
                data[field] = value.value if isinstance(value, Enum) else value
        return data

    def create_marker(self, *args, ch_id: str, **kwargs) -> str:
        """Creates the formatted output marker string from the instance's state."""
        marker_data = self.to_dict()
        if ch_id:
            marker_data['ch_id'] = ch_id
        parts = [f"{key}: {value}" for key, value in marker_data.items()]
        return f"{self.start_token}{', '.join(parts)}{self.end_token}"


class ModuleOpCodes(OpCodes):
    """Represents a module-level op-code with module-specific logic."""

    def __init__(self, *args, **kwargs):
        """Initializes by adding the class_name attribute."""
        super().__init__(*args, **kwargs)
        self.class_name: Optional[str] = None

    def __call__(self, *args, head: str, **kwargs):
        """Parses the header and derives the class name if applicable."""
        unrecognized = self.load_string(*args, head=head, **kwargs)
        assert not unrecognized, f"Unknown fields: {unrecognized}"
        self.validate_state(*args, **kwargs)
        self.derive_class_name(*args, **kwargs)

    def derive_class_name(self, *args, **kwargs):
        """Extracts class name from target string for method operations."""
        if self.target and "." in self.target and self.obj == OPObjects.METHOD:
            self.class_name, self.target = self.target.split(".", 1)
            # we add class_name to field_order before ch_id
        elif self.obj == OPObjects.CLASS and self.target:
            self.class_name = self.target
        else:
            self.class_name = None
        if self.class_name is not None:
            self.field_order.insert(-2, "class_name")


class PackageOpCodes(OpCodes):
    """Represents a package-level op-code for file operations."""

    def __init__(self, *args, **kwargs):
        """Initializes with package-specific tokens and enum maps."""
        super().__init__(*args, **kwargs)
        self.start_token, self.end_token = "#--- ", " ---#"
        self._enum_map = {"op_code": OP_P, "obj": OPObjects}

    def __call__(self, *args, head: str, **kwargs):
        """Parses the header and validates the state."""
        unrecognized = self.load_string(*args, head=head, **kwargs)
        assert not unrecognized, f"Unknown fields: {unrecognized}"
        self.validate_state(*args, **kwargs)

    def validate_state(self, *args, **kwargs):
        """Ensures the op-code is valid for a package operation."""
        super().validate_state(*args, **kwargs)
        if self.obj != OPObjects.FILE:
            raise ValueError(f"Package op-code must have 'obj: {OPObjects.FILE.value}'.")
        if not self.target or not isinstance(self.target, str):
            raise ValueError("Package op-code requires a non-empty 'target' file name.")