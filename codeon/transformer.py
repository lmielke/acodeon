# C:\Users\lars\python_venvs\packages\acodeon\codeon\transformer.py

import libcst as cst
from typing import List, Tuple, Optional
from codeon.op_codes import OpCodes, OP_M, OPObjects


class ClassTransformer:
    def __init__(self, in_node: cst.ClassDef, op_codes: List, ch_id: str, *args, **kwargs):
        self.in_node = in_node
        self.op_codes = op_codes
        self.ch_id = ch_id
        self.removals, self.replacements = self._build_op_maps(*args, **kwargs)
        self.new_body: list[cst.BaseStatement] = []
        self.tgt_nodes: set[str] = set()

    def transform(self, *args, **kwargs) -> cst.ClassDef:
        for stmt in self.in_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                self._process_method_statement(stmt=stmt, *args, **kwargs)
            else:
                self.new_body.append(stmt)
        return self.in_node.with_changes(
            body=self.in_node.body.with_changes(body=tuple(self.new_body))
        )

    def _build_op_maps(self, *args, **kwargs) -> tuple[dict, dict]:
        removals = {op.target: (op, node) for op, node in self.op_codes if op.op_code == OP_M.RM}
        replacements = {op.target: (op, node) for op, node in self.op_codes if op.op_code == OP_M.RP}
        return removals, replacements

    def _process_method_statement(self, *args, stmt: cst.FunctionDef, **kwargs):
        name = stmt.name.value
        if name in self.removals:
            op, node = self.removals[name]
            self._emit_marker(op=op, *args, **kwargs)
            self.tgt_nodes.add(name)
            return
        for op, node in [(o, n) for o, n in self.op_codes if o.target == name and o.op_code == OP_M.IB]:
            self._insert_node(op=op, node=node, *args, **kwargs)
        if name in self.replacements:
            op, node = self.replacements[name]
            self._emit_marker(op=op, *args, **kwargs)
            self.new_body.append(node)
        else:
            self.new_body.append(stmt)
        self.tgt_nodes.add(name)
        for op, node in [(o, n) for o, n in self.op_codes if o.target == name and o.op_code == OP_M.IA]:
            self._insert_node(op=op, node=node, *args, **kwargs)

    def _insert_node(self, *args, op: OpCodes, node: Optional[cst.CSTNode], **kwargs):
        if not node or not hasattr(node, "name") or node.name.value in self.tgt_nodes:
            return
        self._emit_marker(op=op, *args, **kwargs)
        self.new_body.append(node)
        self.tgt_nodes.add(node.name.value)

    def _emit_marker(self, *args, op: OpCodes, **kwargs):
        marker_text = op.create_marker(ch_id=self.ch_id)
        if self.new_body and not isinstance(self.new_body[-1], cst.EmptyLine):
            self.new_body.append(cst.EmptyLine())
        self.new_body.append(cst.EmptyLine(comment=cst.Comment(marker_text)))


class ApplyChangesTransformer(cst.CSTTransformer):
    """
    Applies a series of op-codes to a CST, modifying the tree structure.
    This transformer handles module-level changes (imports) and class-level
    changes (methods).
    """

    import_nodes = {OP_M.IA, OP_M.IB}

    def __init__(self, source, ops, *args, ch_id=None, **kwargs):
        self.source: list = source
        self.ops: List[Tuple[OpCodes, Optional[cst.CSTNode]]] = ops
        self.ch_id: str = ch_id or "unknown"

    def _create_marker_node(self, op: OpCodes, *args, **kwargs) -> cst.EmptyLine:
        marker_text = op.create_marker(ch_id=self.ch_id)
        return cst.EmptyLine(comment=cst.Comment(marker_text))

    def _apply_op(self, op: OpCodes, node: cst.CSTNode, target_index: int, new_body: list):
        marker_node = self._create_marker_node(op)
        if op.op_code == OP_M.RM:
            new_body[target_index : target_index + 1] = [marker_node]
            return
        if not node:
            return
        nodes_to_add = []
        if op.obj in {OPObjects.CLASS, OPObjects.FUNCTION}:
            nodes_to_add.extend([cst.EmptyLine(), cst.EmptyLine()])
        nodes_to_add.append(marker_node)
        nodes_to_add.append(node)
        if op.op_code == OP_M.RP:
            new_body[target_index : target_index + 1] = nodes_to_add
        elif op.op_code == OP_M.IA:
            new_body[target_index + 1 : target_index + 1] = nodes_to_add
        elif op.op_code == OP_M.IB:
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
        self, op: OpCodes, node: Optional[cst.CSTNode], new_body: list, *args, **kwargs
    ):
        """Find target and apply op; fallback insert for untargeted imports."""
        ti = self._find_target_index(op.target, new_body) if op.target else -1
        if ti != -1:
            self._apply_op(op, node, ti, new_body)
        elif node and op.obj == OPObjects.IMPORT and op.op_code in self.import_nodes:
            idx = self._get_insertion_index(*args, body=new_body, **kwargs)
            new_body.insert(idx, node)

    def leave_Module(self, in_node: cst.Module, out_node: cst.Module) -> cst.Module:
        module_level_ops = {OPObjects.IMPORT, OPObjects.CLASS, OPObjects.FUNCTION}
        m_ops = [(op, node) for op, node in self.ops if op.obj in module_level_ops]
        if not m_ops:
            return out_node
        new_body = list(out_node.body)
        for op, node in reversed(m_ops):
            self._process_module_operation(op, node, new_body)
        return out_node.with_changes(body=tuple(new_body))

    def leave_ClassDef(self, in_node: cst.ClassDef, out_node: cst.ClassDef) -> cst.CSTNode:
        op_codes = [(op, node) for op, node in self.ops
            if op.obj == OPObjects.METHOD and op.class_name == in_node.name.value
        ]
        if not op_codes:
            return out_node
        return ClassTransformer(in_node, op_codes, self.ch_id).transform()


class ApplyCreateTransformer(cst.CSTTransformer):
    """
    A transformer specifically for the 'create' operation. It finds the
    package op-code header and replaces it with a new marker that includes
    the change ID (ch_id).
    """

    def __init__(self, *args, package_op, ch_id: str, **kwargs):
        self.package_op = package_op
        self.ch_id = ch_id
        self.header_found_and_replaced = False

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Finds and replaces the op-code header comment at the module level."""
        if self.header_found_and_replaced:
            return updated_node

        new_header_nodes = []
        for header_line in updated_node.header:
            if (
                header_line.comment
                and header_line.comment.value.startswith("#--- op_code:")
            ):
                new_marker = self.package_op.create_marker(ch_id=self.ch_id)
                new_comment = cst.Comment(value=new_marker)
                new_header_nodes.append(header_line.with_changes(comment=new_comment))
                self.header_found_and_replaced = True
            else:
                new_header_nodes.append(header_line)

        return updated_node.with_changes(header=tuple(new_header_nodes))