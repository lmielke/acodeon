import os
import libcst as cst

from codeon.parsers import CSTSource, CSTDelta
from codeon.transformer import ApplyChangesTransformer
from codeon.helpers.collections import format_with_black


class RefactorEngine:
    """Orchestrates the parsing, transformation, and writing of refactored code."""

    def __init__(self, *args, **kwargs):
        """
        Initializes the engine with parsers for the source and update files.
        """
        self.source_parser = CSTSource(*args, **kwargs)
        self.delta_parser = CSTDelta(*args, **kwargs)

    def run(self, *args, use_black: bool = False, verbose: int = 0, **kwargs ) -> bool:
        """
        Executes the end-to-end refactoring process.
        """
        if verbose >= 1:
            print(f"Processing update for: {os.path.basename(self.source_parser.path)}")

        operations = self.delta_parser.parse(verbose=verbose)
        if not operations:
            print("Error: No valid operations found in the update file.")
            return False

        modified_tree = self._apply_transformations(*args, operations=operations, **kwargs)
        target_code = modified_tree.code

        if use_black:
            target_code = format_with_black(target_code, verbose=verbose)

        return self._write_output(target_code, *args, **kwargs)

    def _apply_transformations(self, *args, **kwargs) -> cst.Module:
        """Applies the parsed operations to the source CST."""
        source_tree = self.source_parser.parse()
        # Pass 'operations' as a keyword argument
        transformer = ApplyChangesTransformer(*args, **kwargs)
        return source_tree.visit(transformer)

    def _write_output(self, target_code: str, *args, target_path: str, **kwargs) -> bool:
        """Writes the final transformed code to the target file path."""
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(target_code)
            return True
        except OSError as e:
            print(f"Error: Could not write to output file at {target_path}. Reason: {e}")
            return False
