import os, re, json, shutil, subprocess
import libcst as cst
from colorama import Fore, Style
from codeon.parsers import CSTSource, CSTDelta
from codeon.transformer import ApplyCreateTransformer
from codeon.op_codes import OP_P
from codeon.engine import Validator_Formatter
import codeon.settings as sts

class Formatter:
    """Handles code formatting, specifically with Black."""

    def format_with_black(self, code: str, *args, verbose: int = 0, **kwargs) -> str:
        """Formats a string of Python code using the 'black' code formatter."""
        if not shutil.which("black"):
            if verbose >= 1:
                print(
                    "WARNING: --black flag used, but 'black' is not in the system's PATH."
                )
            return code

        try:
            process = subprocess.run(
                ["black", "-q", "-"],
                input=code,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            if verbose >= 2:
                print("Formatted output with black.")
            return process.stdout
        except (subprocess.CalledProcessError, Exception) as e:
            if verbose >= 1:
                print(f"Error running black formatter: {e}")
            return code


class CreateEngine:
    """Orchestrates the creation of a new file from an op-code source."""

    def __init__(self, *args, **kwargs):
        """Initializes the engine with parsers and a formatter."""
        self.csts = CSTSource(*args, **kwargs)
        self.cstd = CSTDelta(*args, **kwargs)
        self.F = Validator_Formatter()

    def run(self, *args, source_path: str, ch_id: str, **kwargs) -> dict | None:
        """
        Executes the end-to-end refactoring process, ensuring the op-code is 'create'.
        Returns a status dictionary on success, otherwise None.
        """
        # Parse the op-code file, which returns a package_op and module_ops
        # The 'op_codes_path' is already in kwargs, so we don't pass it explicitly.
        op_data = self.get_op_codes(*args, **kwargs)
        if op_data is None:
            return None
        package_op, op_codes = op_data

        # Parse the source file and initialize the transformer
        self.csts(*args, source_path=source_path, **kwargs)
        tf = ApplyCreateTransformer(
            self.csts.body, *args, package_op=package_op, ch_id=ch_id, **kwargs
        )

        # Generate the adjusted code from the transformed CST
        out_code = self.F(self.csts.body.visit(tf).code, *args, **kwargs)
        self._write_output(out_code, *args, **kwargs)
        return {
            "source_file": os.path.basename(source_path),
            "ch_id": ch_id,
            "op_codes": [op.to_dict() for op, node in op_codes],
        }

    def get_op_codes(self, *args, op_codes_path: str, **kwargs) -> tuple | None:
        self.cstd(*args, source_path=op_codes_path, **kwargs)
        package_op, op_codes = self.cstd.body
        # Verify that a package op-code of type 'create' is present
        if not package_op or package_op.op_code != OP_P.CREATE:
            print(
                f"{Fore.RED}CreateEngine.run Error:{Fore.RESET} "
                f"{op_codes_path=} requires package op-code 'create' header. "
                f"but has {package_op.op_code = }"
            )
            return None
        return package_op, op_codes

    @staticmethod
    def _write_output(code: str, *args, target_path: str, **kwargs) -> None:
        """Writes the final transformed code to the target file path."""
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(code)
        short_target = target_path.replace(os.path.expanduser("~"), "~")
        print(
            f"{Fore.GREEN}Successfully wrote target file:{Fore.RESET} "
            f"{short_target}"
        )


class JsonEngine:
    """
    A robust JSON parser that attempts multiple strategies to extract a valid
    dictionary from a potentially malformed or polluted string.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the engine with a list of parsing strategies."""
        self.strategies = [
            self._strategy_strict_parse,
            self._strategy_find_json_block,
            self._strategy_fix_trailing_commas,
            self._strategy_fix_quotes_and_commas,
        ]

    def parse(self, *args, **kwargs) -> dict | None:
        """
        Attempts to parse the input string using a series of strategies.

        Returns:
            A dictionary if parsing is successful, otherwise None.
        """
        for strategy in self.strategies:
            data = strategy(*args, **kwargs)
            if data and isinstance(data, dict):
                return data
        return None

    def _strategy_strict_parse(self, *args, json_string: str, **kwargs) -> dict | None:
        """Strategy 1: Tries a direct, strict parse. The ideal case."""
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            return None

    def _strategy_find_json_block(self, *args, json_string: str, **kwargs) -> dict | None:
        """Strategy 2: Finds a JSON block enclosed in `{}` within a larger string."""
        match = re.search(r"\{[\s\S]*\}", json_string)
        if match:
            return self._strategy_strict_parse(*args, json_string=match.group(0), **kwargs)
        return None

    def _strategy_fix_trailing_commas(self, *args, json_string: str, **kwargs) -> dict | None:
        """Strategy 3: Removes trailing commas that are invalid in JSON."""
        cleaned_string = re.sub(r",\s*([\}\]])", r"\1", json_string)
        if cleaned_string != json_string:
            return self.parse(*args, json_string=cleaned_string, **kwargs)
        return None

    def _strategy_fix_quotes_and_commas(self, *args, json_string: str, **kwargs) -> dict | None:
        """
        Strategy 4: A more aggressive approach to fix common LLM mistakes like
        single quotes for keys/strings and missing commas.
        """
        # Note: This is a simplified and aggressive fix.
        # 1. Add commas between "} and "{", "]" and "[" etc.
        fixed_commas = re.sub(r'(["\]\}])\s*\n\s*(["\[\{])', r'\1,\n\2', json_string)
        # 2. Convert Python-style single quotes to JSON double quotes.
        fixed_quotes = fixed_commas.replace("'", '"')
        return self._strategy_strict_parse(*args, json_string=fixed_quotes, **kwargs)