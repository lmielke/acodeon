import argparse
import libcst as cst
import re
import shutil
import subprocess
from pathlib import Path
from collections import defaultdict
import textwrap


class CSTDelta:
    """Parses a delta file into a structured list of operations."""

    # regex to find insert postition:
    #        position to insert          target function
    # -- op: insert_after, target: Transformer._apply_transformations --#
    # -- op: insert_before, target: Validate.format_with_black --#
    op_code_match = (
        r"#--\s*op:\s*(\w+),\s*target:\s*([\w\.]+)\s*--#(.*?)(?=#--\s*op:|$)"
    )

    def __init__(self, *args, delta_path: Path, **kwargs):
        self.path = delta_path
        self.source = self.path.read_text(encoding="utf-8")
        # Pull verbose from kwargs with a default, making the class more robust.

    # -- op: insert_after, target: CSTDelta.__init__ --# chid: delta_2025-09-29-27-51-36_unparse
    def _parse_block(self, *args, code: str, **kwargs) -> cst.CSTNode | None:
        """WHY: Parse a single top-level node, tolerant to errors."""
        try:
            return cst.parse_module(code).body[0]
        except (cst.ParserSyntaxError, IndexError):
            return None

    # -- op: insert_replace, target: CSTDelta.parse --# chid: delta_2025-09-29-27-51-36_unparse
    def parse(self, *args, verbose: int = 0, **kwargs) -> list[dict]:
        """
        WHY: Orchestrate scan → normalize → parse with strict support for
        insert_remove (node-less ops).
        """
        ops: list[dict] = []
        for op, tgt, raw in re.compile(self.op_code_match, re.DOTALL).findall(self.source):
            code = textwrap.dedent(raw.replace("\u00a0", " "))
            cls_name, meth = (tgt.split(".", 1) + [None])[:2] if "." in tgt else (None, tgt)
            if not code.strip():
                if op == "insert_remove":
                    ops.append({"op": op, "class": cls_name, "target": meth, "node": None})
                continue
            node = self._parse_block(code=code)
            if node is None:
                continue
            ops.append({"op": op, "class": cls_name, "target": meth, "node": node})
        if verbose >= 3:
            print(f"--> CSTDelta: ops={len(ops)}")
        return ops


class CSTSource:
    """Parses a source Python file into a CST Module."""

    def __init__(self, *args, input_path: Path, **kwargs):
        self.path = input_path
        self.source = self.path.read_text(encoding="utf-8")

    def parse(self, *args, **kwargs) -> cst.Module:
        """Returns the parsed CST tree of the source file."""
        return cst.parse_module(self.source)


class _ApplyChangesTransformer(cst.CSTTransformer):
    """
    Internal transformer that applies operations to a CST, capable of modifying
    the bodies of classes.
    """

    op_order = (
        "insert_before",
        "insert_after",
    )

    def __init__(
        self, operations: list[dict], *args, change_id: str | None = None, **kwargs
    ):
        self.operations = operations
        self.change_id = change_id or "unknown"

    # -- op: insert_remove, target: _ApplyChangesTransformer._attach_marker_to_node --# chid: delta_2025-09-29-13-15-36_unparse

    def _update_nodes(
        self, *args, op: dict, new_body: list, pre_nodes: set, cls_name: str, **kwargs
    ) -> None:
        """Unified method to insert a function node into the class body."""
        name_to_insert = op["node"].name.value
        if name_to_insert in pre_nodes:
            return  # Avoid duplicate insertions

        # Always emit the marker as a separate comment. This is cleaner and
        # works consistently for decorated and non-decorated functions.
        self._emit_marker(new_body=new_body, op=op, cls_name=cls_name)
        new_body.append(op["node"])
        pre_nodes.add(name_to_insert)

    def leave_ClassDef(
        self, in_node: cst.ClassDef, out_node: cst.ClassDef, *args, **kwargs
    ) -> cst.CSTNode:
        """
        WHY: Orchestrate per-class ops: remove > replace > before/after.
        Emits markers for remove/replace. Preserves decorators.
        """
        new_body, pre_nodes = [], set()
        cls_name, names, ops = self._collect_ops_for_class(in_node=in_node)
        if not ops:
            return out_node
        self._require_targets(*args, cls_name=cls_name, ops=ops, method_names=names, **kwargs)
        rem, rep = self._build_maps(ops=ops)

        for stmt in out_node.body.body:
            if not isinstance(stmt, cst.FunctionDef):
                new_body.append(stmt)
                continue
            self._handle_func_stmt(
                stmt=stmt, cls_name=cls_name, rem=rem, rep=rep, ops=ops,
                pre_nodes=pre_nodes, new_body=new_body,
            )

        return out_node.with_changes(body=out_node.body.with_changes(body=new_body))

    def _collect_ops_for_class(
        self, *args, in_node: cst.ClassDef, **kwargs
    ) -> tuple[str, set[str], list[dict]]:
        """
        WHY: Gather class name, method names, and relevant ops for this class.
        """
        cls_name = in_node.name.value
        names = {
            n.name.value for n in in_node.body.body if isinstance(n, cst.FunctionDef)
        }
        ops = [
            op for op in self.operations
            if (op.get("class") in (None, cls_name))
            and (op["target"] in names or op["op"] in {"insert_replace", "insert_remove"})
        ]
        return cls_name, names, ops

    def _build_maps(self, *args, ops: list[dict], **kwargs) -> tuple[dict, dict]:
        """
        WHY: Pre-index strict ops for O(1) lookups during traversal.
        """
        rem = {op["target"]: op for op in ops if op["op"] == "insert_remove"}
        rep = {op["target"]: op for op in ops if op["op"] == "insert_replace"}
        return rem, rep

    def _handle_func_stmt(
        self,
        *args,
        stmt: cst.FunctionDef,
        cls_name: str,
        rem: dict,
        rep: dict,
        ops: list[dict],
        pre_nodes: set,
        new_body: list,
        **kwargs,
    ) -> None:
        """
        WHY: Apply remove/replace/before/after for a single method.
        """
        name = stmt.name.value
        if name in rem:
            self._emit_marker(new_body=new_body, op=rem[name], cls_name=cls_name)
            return
        if name in rep:
            self._emit_marker(new_body=new_body, op=rep[name], cls_name=cls_name)
            new_body.append(rep[name]["node"])
            pre_nodes.add(name)
            return

        befores = [o for o in ops if o["target"] == name and o["op"] == "insert_before"]
        afters  = [o for o in ops if o["target"] == name and o["op"] == "insert_after"]

        for o in befores:
            self._update_nodes(op=o, new_body=new_body, pre_nodes=pre_nodes, cls_name=cls_name)
        new_body.append(stmt)
        pre_nodes.add(name)
        for o in afters:
            self._update_nodes(op=o, new_body=new_body, pre_nodes=pre_nodes, cls_name=cls_name)

    def _marker_text(self, *args, op: dict, cls_name: str, **kwargs) -> str:
        tgt = f"{cls_name}.{op['target']}" if op.get("class") else op["target"]
        return f"#-- op: {op['op']}, target: {tgt} --# chid: {self.change_id}"

    def _emit_marker(self, *args, new_body: list, op: dict, cls_name: str, **kwargs) -> None:
        """Add a marker as a class-body line (above decorators)."""
        if new_body and not isinstance(new_body[-1], cst.EmptyLine):
            new_body.append(cst.EmptyLine())
        new_body.append(
            cst.EmptyLine(comment=cst.Comment(self._marker_text(op=op, cls_name=cls_name)))
        )

    # -- op: insert_replace, target: _ApplyChangesTransformer._require_targets --# chid: delta_2025-09-29-13-06-36_unparse
    def _require_targets(
        self, *args, cls_name: str, ops: list[dict], method_names: set[str], **kwargs
    ) -> None:
        """
        WHY: Strict mode: targets for replace/remove must exist in the class.
        """
        need = {"insert_replace", "insert_remove"}
        missing = sorted(
            {
                op["target"]
                for op in ops
                if op["op"] in need and op["target"] not in method_names
            }
        )
        if missing:
            raise ValueError(f"strict ops missing in {cls_name}: {', '.join(missing)}")


class Transformer:
    """Orchestrates the entire CST refactoring process, including I/O."""

    def __init__(self, *args, **kwargs):
        self.source_parser = CSTSource(*args, **kwargs)
        self.delta_parser = CSTDelta(*args, **kwargs)
        self.validator = Validate(*args, **kwargs)

    def __call__(
        self, *args, verbose: int = 0, use_black: bool = False, **kwargs
    ) -> bool:
        """
        WHY: Orchestrate parsing, transforming, optional formatting, and writing.
        """
        if verbose >= 1:
            print(f"Updating source file: {self.source_parser.path}")
        ops = self._parse_operations(*args, verbose=verbose, **kwargs)
        if not ops:
            return False
        mod = self._apply_transformations(*args, operations=ops, **kwargs)
        tgt_code = mod.code
        if use_black:
            tgt_code = self.validator.format_with_black(
                tgt_code, *args, verbose=verbose, **kwargs
            )
        return self._write_output(tgt_code, *args, **kwargs)

    # -- op: insert_replace, target: Transformer._parse_operations --# chid: delta_2025-09-29-13-15-36_unparse
    def _parse_operations(self, *args, verbose: int = 0, **kwargs) -> list[dict] | None:
        """
        WHY: Load ops and print safely even for node-less ops (e.g., insert_remove).
        """
        ops = self.delta_parser.parse(*args, verbose=verbose, **kwargs)
        if not ops:
            print("Error: No valid operations found in delta file.")
            return None
        if verbose >= 2:
            for i, op in enumerate(ops, 1):
                n = op["node"].name.value if op.get("node") is not None else "(no-node)"
                print(f"{i}. RUN: {op['op']} '{n}' relative to '{op['target']}'")
        return ops

    def _apply_transformations(
        self, *args, operations: list[dict], **kwargs
    ) -> cst.Module:
        """Applies the parsed operations to the source CST."""
        source_tree = self.source_parser.parse()
        change_id = self.delta_parser.path.name.split(".")[0]
        apply_transformer = _ApplyChangesTransformer(
            operations, *args, change_id=change_id, **kwargs
        )
        return source_tree.visit(apply_transformer)

    def _write_output(self, tgt_code: str, *args, tgt_path: Path, **kwargs) -> bool:
        """
        WHY: Persist final code to file (parent created if needed).
        """
        try:
            tgt_path.parent.mkdir(parents=True, exist_ok=True)
            tgt_path.write_text(tgt_code, encoding="utf-8")
            return True
        except OSError as e:
            print(f"Error writing to output file {tgt_path}: {e}")
            return False


class Validate:
    """Performs validation and formatting on code."""

    def __init__(self, *args, **kwargs):
        pass

    def format_with_black(self, code: str, *args, verbose: int, **kwargs) -> str:
        """Formats a string of Python code using the 'black' formatter."""
        if not shutil.which("black"):
            if verbose >= 1:
                print("WARNING: --black flag used, but 'black' not found in PATH.")
            return code
        if verbose >= 2:
            print("99. RUN: using black to format output file")
        p = subprocess.run(
            ["black", "-q", "-"],
            input=code,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return p.stdout if p.returncode == 0 else code

    def run_tests(self, *args, **kwargs):
        """Code should be tested before pushing it."""
        pass


def main(*args, **kwargs) -> None:
    """Parses CLI arguments and runs the refactoring."""
    parser = argparse.ArgumentParser(description="Refactor a Python file using CST.")
    parser.add_argument(
        "-f", "--file_path", type=Path, required=True, help="Path to the input file."
    )
    parser.add_argument(
        "-d",
        "--delta_file_path",
        type=Path,
        required=True,
        help="Path to the delta file.",
    )
    parser.add_argument(
        "--hard", action="store_true", help="Overwrite the original file."
    )
    parser.add_argument(
        "-v", "--verbose", type=int, default=0, help="Set verbosity level (0-5)."
    )
    parser.add_argument(
        "-b", "--black", action="store_true", help="Format output with black."
    )
    args = parser.parse_args()

    if not args.file_path.is_file():
        print(f"Error: Input file not found at {args.file_path}")
        return
    if not args.delta_file_path.is_file():
        print(f"Error: Delta file not found at {args.delta_file_path}")
        return

    tgt_path = (
        args.file_path if args.hard else Path("/temp/refactor") / args.file_path.name
    )

    success = Transformer(
        input_path=args.file_path,
        delta_path=args.delta_file_path,
    )(
        tgt_path=tgt_path,
        verbose=args.verbose,
        use_black=args.black,
    )

    if not success:
        print("Transformation failed.")
        return

    print("Transformation complete.")
    if args.hard:
        print(f"  Overwritten: {args.file_path}")
    else:
        print(f"  Original: {args.file_path}")
        print(f"  Modified: {tgt_path}")


if __name__ == "__main__":
    main()
