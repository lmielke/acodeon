#--- cr_op: create, cr_type: file, cr_anc: headers.py, cr_id: 2025-10-08-16-12-30 ---#

import os, re, yaml
from colorama import Fore, Style
from codeon.helpers.printing import logprint, Color, MODULE_COLORS
MODULE_COLORS["headers"] = Color.MAGENTA
from dataclasses import asdict, dataclass

# Constants for all valid CR module options
CR_OPS = ("insert_before", "insert_after", "replace", "remove")
CR_TYPES = ("file", "import", "class", "function", "method")
#CR_ANCS = ("import <module>", "from <module> import <name>", "<Class.method>")
# Use CR_OPS_PG for package-level operations '#---'
CR_OPS_PG = ("update", "create", "remove")


@dataclass
class CR_OBJ_FIELDS:
    """Defines the standard fields and their descriptions for a CR header."""
    CR_OP: str = "cr_op"  # cr operation to perform
    CR_TYPE: str = "cr_type"  # type of object to be updated
    CR_ANC: str = "cr_anc"  # relative update location, example: CrHeads.load_string
    INSTALL: str = "install"  # whether to install a package
    CR_ID: str = "cr_id"  # NOTE: this is a blocked field (do not use), engine-generated only

    def to_dict(self) -> dict:
        return asdict(self)


class CrHeads:
    """Represents the state of a parsed cr-header using YAML parsing."""

    def __init__(self, *args, **kwargs):
        """Initializes all potential cr-header fields to None."""
        # Use CR_OBJ_FIELDS to ensure all recognized fields are included
        self.field_order = list(CR_OBJ_FIELDS().to_dict().values())
        for field in self.field_order:
            setattr(self, field, None)
        # Use lists of constant strings instead of Enums for validation
        self.valid_ops = CR_OPS
        self.valid_types = CR_TYPES
        self.cr_op = None
        self.cr_type = None

    def load_string(self, *args, head: str, **kwargs) -> dict:
        """Loads and parses an cr-header string."""
        content_str = head[len(self.start_token) : -len(self.end_token)].strip()
        data = yaml.safe_load("\n".join(p.strip() for p in content_str.split(",")))
        assert isinstance(data, dict), "Parsed cr-header is not a dictionary."
        return self.parse_data(data, *args, **kwargs)

    def parse_data(self, data: dict, *args, **kwargs) -> dict:
        """Validates and assigns data from a parsed dictionary to the instance."""
        unrecognized = {}
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, self._validate_value(key, value))
            else:
                unrecognized[key] = value
        return unrecognized

    def _validate_value(self, key: str, value: any, *args, **kwargs):
        """Validates a single value against its expected type or list of constants."""
        valid_map = {"cr_op": self.valid_ops, "cr_type": self.valid_types}
        
        if key in valid_map:
            valid_options = valid_map[key]
            if value not in valid_options:
                raise ValueError(
                    f"Invalid value '{value}' for '{key}'. Use one of: {valid_options}"
                )
        if key == "install" and not isinstance(value, bool):
            raise ValueError(f"Field 'install' must be a boolean (True/False).")
        return value

    def validate_state(self, *args, **kwargs) -> None:
        """Validates cross-field constraints."""
        if self.cr_type == "import" and self.cr_anc:
            import_pattern = r"^(import\s+\w+|from\s+\w+(\.\w+)*\s+import\s+\w+)$"
            if not re.match(import_pattern, self.cr_anc.strip()):
                raise ValueError(f"Invalid import statement in target: '{self.cr_anc}'")
        if self.cr_type == 'method':
            # Expecting format Class.method
            assert len(self.cr_anc.split('.')) == 2, \
            logprint(f"Invalid {self.cr_anc = } format. Must be Class.method", level='error')

    def to_dict(self, *args, **kwargs) -> dict:
        """Internal method to build a dictionary from the instance's state."""
        data = {}
        for field in self.field_order:
            value = getattr(self, field, None)
            if value is not None:
                # Value is a simple string/bool, no Enum.value needed
                data[field] = value
        return data

    def create_marker(self, *args, cr_id: str | None = None, **kwargs) -> str:
        """Allow emitting a header even when cr_id is unknown/omitted."""
        marker_data = self.to_dict()
        if cr_id:
            marker_data['cr_id'] = cr_id
        parts = [f"{k}: {v}" for k, v in marker_data.items()]
        return f"{self.start_token}{', '.join(parts)}{self.end_token}"


class UnitCrHeads(CrHeads):
    """Represents in module unit change-request(s) with cr-type specific logic."""

    def __init__(self, *args, **kwargs):
        """Initializes by adding the start and end token attribute."""
        super().__init__(*args, **kwargs)
        # module-level cr-header tokens include two dashes
        self.start_token, self.end_token = "#-- ", " --#"

    def __call__(self, *args, **kwargs) -> None:
        """Parses the header and validates state."""
        unrecognized = self.load_string(*args, **kwargs)
        assert not unrecognized, f"Unknown fields: {unrecognized}"
        self.validate_state(*args, **kwargs)

class PackageCrHeads(CrHeads):
    """Represents a package-level change-request for file/module operations."""

    def __init__(self, *args, **kwargs):
        """Initializes with package-specific tokens and valid operations."""
        super().__init__(*args, **kwargs)
        # package-level cr-header tokens include three dashes
        self.start_token, self.end_token = "#--- ", " ---#"
        # Use CR_OPS_PG constants for package-level operations
        self.valid_ops = CR_OPS_PG

    def __call__(self, *args, verbose:int=0, **kwargs) -> None:
        """Parses the header and validates the state."""
        unrecognized = self.load_string(*args, verbose=verbose, **kwargs)
        assert not unrecognized, f"Unknown fields: {unrecognized}"
        self.validate_state(*args, **kwargs)
        if verbose:
            print(f"{Fore.GREEN}Loaded package change-request:{Style.RESET_ALL} {self.to_dict()}")

    def validate_state(self, *args, **kwargs) -> None:
        """Ensures the change-request is valid for a package operation."""
        super().validate_state(*args, **kwargs)
        # Check against string "file" now
        if self.cr_type != "file":
            raise ValueError(f"Package change-request must have 'cr_type: file'.")
        if not self.cr_anc or not isinstance(self.cr_anc, str):
            raise ValueError("Package change-request requires a non-empty 'cr_anc' file name.")
        if not self.cr_op in self.valid_ops:
            raise ValueError(f"Invalid '{self.cr_op = }'. Note {self.valid_ops = }")