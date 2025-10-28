#--- cr_op: create, cr_type: file, cr_anc: headers.py, cr_id: 2025-10-08-16-12-30 ---#

import os, re, yaml
from colorama import Fore, Style
from dataclasses import asdict, dataclass
from enum import Enum


@dataclass
class CR_OBJ_FIELDS:
    CR_OP: str = "cr_op"        # cr operation to perform (i.e. insert_before, insert_after, replace, remove)
    CR_TYPE: str = "cr_type"    # type of object to be updated (i.e. import, method, function, class, raw, file)
    CR_ANC: str = "cr_anc"      # relative update location in the target module
    INSTALL: str = "install"    # whether to install a package (True/False)

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


class CRTypes(str, Enum):
    """Target cr_object to perform the operation on."""
    IMPORT, METHOD, FUNCTION, CLASS, RAW, FILE = (
        "import", "method", "function", "class", "raw", "file",
    )


class CrHeads:
    """Represents the state of a parsed cr-header using YAML parsing."""

    def __init__(self, *args, **kwargs):
        """Initializes all potential cr-header fields to None."""
        self.field_order = list(CR_OBJ_FIELDS().to_dict().values())
        for field in self.field_order:
            setattr(self, field, None)
        self._enum_map = {"cr_op": OP_M, "cr_type": CRTypes}

    def load_string(self, *args, head: str, **kwargs):
        """Loads and parses an cr-header string."""
        content_str = head[len(self.start_token) : -len(self.end_token)].strip()
        data = yaml.safe_load("\n".join(p.strip() for p in content_str.split(",")))
        assert isinstance(data, dict), "Parsed cr-header is not a dictionary."
        return self.parse_data(data, *args, **kwargs)

    def parse_data(self, data: dict, *args, **kwargs):
        """Validates and assigns data from a parsed dictionary to the instance."""
        unrecognized = {}
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, self._validate_value(key, value))
            else:
                unrecognized[key] = value
        return unrecognized

    def _validate_value(self, key: str, value: any, *args, **kwargs):
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
        Validates the cross field state of the instance. For example, when cr_obj is an import, 
        then target must be a valid import statement.
        """
        if self.cr_type == CRTypes.IMPORT and self.cr_anc:
            import_pattern = r"^(import\s+\w+|from\s+\w+(\.\w+)*\s+import\s+\w+)$"
            if not re.match(import_pattern, self.cr_anc.strip()):
                raise ValueError(f"Invalid import statement in target: '{self.cr_anc}'")
        
    def to_dict(self, *args, **kwargs) -> dict:
        """Internal method to build a dictionary from the instance's state."""
        data = {}
        for field in self.field_order:
            value = getattr(self, field, None)
            if value is not None:
                data[field] = value.value if isinstance(value, Enum) else value
        return data
    
    #-- cr_op: replace, cr_type: method, class_name: CrHeads, cr_anc: create_marker, cr_id: 8888-88-88-88-88-88 --#
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
        """Initializes by adding the class_name attribute."""
        super().__init__(*args, **kwargs)
        # module-level cr-header tokens include two dashes
        self.start_token, self.end_token = "#-- ", " --#"
        self.class_name: str = None

    def __call__(self, *args, **kwargs):
        """Parses the header and derives the class name if applicable."""
        unrecognized = self.load_string(*args, **kwargs)
        assert not unrecognized, f"Unknown fields: {unrecognized}"
        self.validate_state(*args, **kwargs)
        self.derive_class_name(*args, **kwargs)

    def derive_class_name(self, *args, **kwargs):
        """Extracts class name from target string for method operations."""
        if self.cr_anc and "." in self.cr_anc and self.cr_type == CRTypes.METHOD:
            self.class_name, self.cr_anc = self.cr_anc.split(".", 1)
            # we add class_name to field_order before cr_id
        elif self.cr_type == CRTypes.CLASS and self.cr_anc:
            self.class_name = self.cr_anc
        else:
            self.class_name = None
        if self.class_name is not None:
            self.field_order.insert(-2, "class_name")


class PackageCrHeads(CrHeads):
    """Represents a package-level change-request for file/module operations."""

    def __init__(self, *args, **kwargs):
        """Initializes with package-specific tokens and enum maps."""
        super().__init__(*args, **kwargs)
        # package-level cr-header tokens include three dashes
        self.start_token, self.end_token = "#--- ", " ---#"
        self._enum_map = {"cr_op": OP_P, "cr_type": CRTypes}

    def __call__(self, *args, verbose:int=0, **kwargs):
        """Parses the header and validates the state."""
        unrecognized = self.load_string(*args, verbose=verbose, **kwargs)
        assert not unrecognized, f"Unknown fields: {unrecognized}"
        self.validate_state(*args, **kwargs)
        if verbose:
            print(f"{Fore.GREEN}Loaded package change-request:{Style.RESET_ALL} {self.to_dict()}")

    def validate_state(self, *args, **kwargs):
        """Ensures the change-request is valid for a package operation."""
        super().validate_state(*args, **kwargs)
        if self.cr_type != CRTypes.FILE:
            raise ValueError(f"Package change-request must have 'cr_obj: {CRTypes.FILE.value}'.")
        if not self.cr_anc or not isinstance(self.cr_anc, str):
            raise ValueError("Package change-request requires a non-empty 'target' file name.")