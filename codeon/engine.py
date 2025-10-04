import os
import libcst as cst
from colorama import Fore, Style

from codeon.parsers import CSTSource, CSTDelta
from codeon.transformer import ApplyChangesTransformer
from codeon.cr_headers import OP_P


class RefactorEngine:
    """Orchestrates the parsing, transformation, and writing of refactored code."""

    def __init__(self, *args, **kwargs):
        """
        Initializes the engine with parsers for the source and update files.
        """
        self.csts = CSTSource(*args, **kwargs)
        self.cstd = CSTDelta(*args, **kwargs)
        self.F = Validator_Formatter()

    def run(self, *args, source_path:str, ch_id:str, **kwargs) -> dict | None:
        """
        Executes the end-to-end refactoring process, ensuring the cr-operation is 'update'.
        Returns a status dictionary on success, otherwise None.
        """
        # Parse the cr_integration_file, which now returns a package_op and module_ops
        cr_ops = self.get_cr_ops(*args, source_path=source_path, **kwargs)
        if cr_ops is None:
            return None
        # Parse the source file and initialize the transformer with cr_ops
        self.csts(*args, source_path=source_path, **kwargs)
        tf = ApplyChangesTransformer(self.csts.body, cr_ops, *args, ch_id=ch_id, **kwargs)
        # Generate the adjusted code from the transformed CST
        out_code = self.F(self.csts.body.visit(tf).code, *args, **kwargs)
        self._write_output(out_code, cr_ops, *args, **kwargs)
        return {
                "source_file": os.path.basename(source_path),
                "ch_id": ch_id,
                "cr_ops": [op.to_dict() for op, node in cr_ops],
            }

    def get_cr_ops(self, *args, cr_integration_path: str, source_path:str, **kwargs) -> list[dict]:
        self.cstd(*args, source_path=cr_integration_path, **kwargs)
        package_op, cr_ops = self.cstd.body
        # Verify that a package cr-operation of type 'update' is present
        if not package_op or package_op.cr_op != OP_P.UPDATE:
            print(f"{Fore.RED}RefactorEngine.run Error:{Fore.RESET} "
                    f"{cr_integration_path= } requires package cr-operation 'update' header. "
                    f"but has {package_op.cr_op = }")
            return None
        return cr_ops

    @staticmethod
    def _write_output(code: str, *args, target_path: str, **kwargs) -> bool:
        """Writes the final transformed code to the target file path."""
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(code)


class Validator_Formatter:

    def __init__(self, *args, **kwargs):
        self.out_code = ""

    def __call__(self, code, *args, use_black:bool=False, **kwargs):
        self.out_code = code
        if use_black:
            self.format_with_black(*args, **kwargs)
        return self.out_code
    
    def format_with_black(*args, verbose: int = 0, **kwargs) -> str:
        """
        Formats a string of Python code using the 'black' code formatter.

        If 'black' is not found in the system's PATH, it returns the original code.
        """
        if not shutil.which("black"):
            if verbose >= 1:
                print("WARNING: --black flag used, but 'black' is not in the system's PATH.")
            return self.out_code

        if verbose >= 2:
            print("Formatting output with black...")

        try:
            process = subprocess.run(
                ["black", "-q", "-"],
                input=self.out_code,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.out_code = process.stdout if process.returncode == 0 else self.out_code
        except Exception as e:
            if verbose >= 1:
                print(f"Error running black formatter: {e}")
