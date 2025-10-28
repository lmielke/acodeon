# C:\Users\lars\python_venvs\packages\acodeon\codeon\transformer.py

import libcst as cst
from typing import List, Tuple, Optional, Set
from colorama import Fore, Style
from codeon.headers import CrHeads, OP_M, CRTypes


class ClassTransformer:
    def __init__(
        self,
        *args,
        in_node: cst.ClassDef,
        cr_ops: List[Tuple[CrHeads, Optional[cst.CSTNode]]],
        cr_id: str,
        **kwargs,
    ):
        self.in_node = in_node
        self.cr_ops = cr_ops
        self.cr_id = cr_id
        # Start new_body as a mutable list of original statements
        self.new_body: list[cst.BaseStatement] = list(in_node.body.body)
        # Track applied ops to prevent re-applying a replace
        self.applied_ops: Set[str] = set()

    def transform(self, *args, **kwargs) -> cst.ClassDef:
        pending_ops = list(self.cr_ops)

        # Loop until no new operations can be applied in a full pass
        while True:
            ops_applied_this_pass = 0
            remaining_ops = []

            for op, node in pending_ops:
                if self._try_apply_op(*args, op=op, node=node, **kwargs):
                    ops_applied_this_pass += 1
                else:
                    remaining_ops.append((op, node))

            if ops_applied_this_pass == 0 or not remaining_ops:
                break  # No progress or all ops are done
            pending_ops = remaining_ops

        if remaining_ops:
            print(
                f"{Fore.YELLOW}Warning: Could not apply all class operations. "
                f"Missing anchors for: "
                f"{[op.cr_anc for op, _ in remaining_ops]}{Style.RESET_ALL}"
            )

        return self.in_node.with_changes(
            body=self.in_node.body.with_changes(body=tuple(self.new_body))
        )

    def _find_anchor_index(self, *args, anchor_name: str, **kwargs) -> int:
        """Finds a method/node by name in the *current* self.new_body."""
        for i, stmt in enumerate(self.new_body):
            if (
                isinstance(stmt, (cst.FunctionDef, cst.ClassDef))
                and stmt.name.value == anchor_name
            ):
                return i
        return -1

    def _create_marker_node(self, *args, op: CrHeads, **kwargs) -> cst.EmptyLine:
        """Creates a new marker node."""
        marker_text = op.create_marker(cr_id=self.cr_id)
        # Add empty line before marker for non-import/decorator ops
        if op.cr_type not in {CRTypes.IMPORT}:
            return cst.EmptyLine(comment=cst.Comment(marker_text))
        return cst.EmptyLine(comment=cst.Comment(marker_text))

    def _try_apply_op(self, *args, op: CrHeads, node: Optional[cst.CSTNode], **kwargs) -> bool:
        """
        Attempts to apply a single operation to self.new_body.
        Returns True on success, False if anchor is not found.
        """
        if op.cr_op == OP_M.RP and op.cr_anc in self.applied_ops:
            return True  # Op already applied (e.g., a prior replace)
        idx = self._find_anchor_index(*args, anchor_name=op.cr_anc, **kwargs)
        if idx == -1:
            return False  # Anchor not found, defer this operation
        marker = self._create_marker_node(*args, op=op, **kwargs)
        nodes_to_add = []
        # Add the single required blank line before a method operation (PEP 8)
        if op.cr_type == CRTypes.METHOD:
            nodes_to_add.extend([cst.EmptyLine()])
        if op.cr_op == OP_M.IB:
            nodes_to_add.append(marker)
            if node:
                nodes_to_add.append(node)
            self.new_body[idx:idx] = nodes_to_add
        elif op.cr_op == OP_M.IA:
            nodes_to_add.append(marker)
            if node:
                nodes_to_add.append(node)
            self.new_body[idx + 1 : idx + 1] = nodes_to_add
        elif op.cr_op == OP_M.RP:
            nodes_to_add.append(marker)
            if node:
                nodes_to_add.append(node)
            self.new_body[idx : idx + 1] = nodes_to_add
            self.applied_ops.add(op.cr_anc)  # Mark as replaced
        elif op.cr_op == OP_M.RM:
            nodes_to_add.append(marker)
            self.new_body[idx : idx + 1] = nodes_to_add
        return True


class ApplyChangesTransformer(cst.CSTTransformer):
    """
    Applies a series of operations to a CST, modifying the tree structure.
    This transformer handles module-level changes (imports) and class-level
    changes (methods).
    """

    import_nodes = {OP_M.IA, OP_M.IB}

    def __init__(self, source, ops, *args, cr_id, **kwargs):
        self.source: list = source
        self.ops: List[Tuple[CrHeads, Optional[cst.CSTNode]]] = ops
        self.cr_id: str = cr_id

    def _create_marker_node(self, op: CrHeads, *args, **kwargs) -> cst.EmptyLine:
        marker_text = op.create_marker(cr_id=self.cr_id)
        return cst.EmptyLine(comment=cst.Comment(marker_text))

    def _apply_op(self, op: CrHeads, node: cst.CSTNode, target_index: int, new_body: list):
        marker_node = self._create_marker_node(op)
        if op.cr_op == OP_M.RM:
            new_body[target_index : target_index + 1] = [marker_node]
            return
        if not node:
            return
        nodes_to_add = []
        if op.cr_type in {CRTypes.CLASS, CRTypes.FUNCTION}:
            nodes_to_add.extend([cst.EmptyLine(), cst.EmptyLine()])
        nodes_to_add.append(marker_node)
        nodes_to_add.append(node)
        if op.cr_op == OP_M.RP:
            new_body[target_index : target_index + 1] = nodes_to_add
        elif op.cr_op == OP_M.IA:
            new_body[target_index + 1 : target_index + 1] = nodes_to_add
        elif op.cr_op == OP_M.IB:
            new_body[target_index:target_index] = nodes_to_add

    def _get_insertion_index(self, *args, body: list, **kwargs) -> int:
        """Find the best index for a non-targeted import (unwrap SimpleStatementLine)."""
        last_import_idx, docstring_idx = -1, -1
        if (
            body
            and isinstance(body[0], cst.SimpleStatementLine)
            and isinstance(body[0].body[0], cst.Expr)
            and isinstance(body[0].body[0].value, cst.SimpleString)
        ):
            docstring_idx = 0
        for i, stmt in enumerate(body):
            s = stmt.body[0] if isinstance(stmt, cst.SimpleStatementLine) else stmt
            if isinstance(s, (cst.Import, cst.ImportFrom)):
                last_import_idx = i
        return (
            (last_import_idx + 1)
            if last_import_idx != -1
            else (docstring_idx + 1)
            if docstring_idx != -1
            else 0
        )

    def _find_target_index(self, target_str: str, body: list) -> int:
        """Find exact target; handle SimpleStatementLine + class/function names."""
        t = target_str.strip()
        for i, stmt in enumerate(body):
            s = stmt.body[0] if isinstance(stmt, cst.SimpleStatementLine) else stmt
            # match class/function by name (e.g., "SecondClass")
            if isinstance(s, (cst.ClassDef, cst.FunctionDef)) and s.name.value == t:
                return i
            # fallback: exact code match (works for "import os", "from x import y")
            if cst.Module([s]).code.strip() == t:
                return i
        return -1

    def _process_module_operation(
        self, op: CrHeads, node: Optional[cst.CSTNode], new_body: list, *args, **kwargs
    ):
        """Find target and apply op; fallback insert for untargeted imports."""
        ti = self._find_target_index(op.cr_anc, new_body) if op.cr_anc else -1
        if ti != -1:
            self._apply_op(op, node, ti, new_body)
        elif node and op.cr_type == CRTypes.IMPORT and op.cr_op in self.import_nodes:
            idx = self._get_insertion_index(*args, body=new_body, **kwargs)
            new_body.insert(idx, node)

    def leave_Module(self, in_node: cst.Module, out_node: cst.Module) -> cst.Module:
        module_level_ops = {CRTypes.IMPORT, CRTypes.CLASS, CRTypes.FUNCTION}
        m_ops = [(op, node) for op, node in self.ops if op.cr_type in module_level_ops]
        if not m_ops:
            return out_node
        new_body = list(out_node.body)
        # Note: Module-level ops do not yet support chaining.
        # They are applied in reverse to maintain indices.
        for op, node in reversed(m_ops):
            self._process_module_operation(op, node, new_body)
        return out_node.with_changes(body=tuple(new_body))

    def leave_ClassDef(
        self, in_node: cst.ClassDef, out_node: cst.ClassDef
    ) -> cst.CSTNode:
        cr_ops = [
            (op, node)
            for op, node in self.ops
            if op.cr_type == CRTypes.METHOD and op.class_name == in_node.name.value
        ]
        if not cr_ops:
            return out_node
        # Pass the original in_node, not the out_node, to the transformer
        return ClassTransformer(
            in_node=in_node, cr_ops=cr_ops, cr_id=self.cr_id
        ).transform()