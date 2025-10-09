# C:\Users\lars\python_venvs\packages\acodeon\codeon\transformer.py

import libcst as cst
from typing import List, Tuple, Optional
from colorama import Fore, Style
from codeon.headers import CrHeads, OP_M, CRTypes


class ClassTransformer:
    def __init__(self, in_node: cst.ClassDef, cr_ops: List, cr_id: str, *args, **kwargs):
        self.in_node = in_node
        self.cr_ops = cr_ops
        self.cr_id = cr_id
        self.removals, self.replacements = self._build_cr_maps(*args, **kwargs)
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

    def _build_cr_maps(self, *args, **kwargs) -> tuple[dict, dict]:
        removals = {op.cr_anc: (op, node) for op, node in self.cr_ops if op.cr_op == OP_M.RM}
        replacements = {op.cr_anc: (op, node) for op, node in self.cr_ops if op.cr_op == OP_M.RP}
        return removals, replacements

    def _process_method_statement(self, *args, stmt: cst.FunctionDef, **kwargs):
        name = stmt.name.value
        if name in self.removals:
            op, node = self.removals[name]
            self._emit_marker(op=op, *args, **kwargs)
            self.tgt_nodes.add(name)
            return
        for op, node in [(o, n) for o, n in self.cr_ops if o.cr_anc == name and o.cr_op == OP_M.IB]:
            self._insert_node(op=op, node=node, *args, **kwargs)
        if name in self.replacements:
            op, node = self.replacements[name]
            self._emit_marker(op=op, *args, **kwargs)
            self.new_body.append(node)
        else:
            self.new_body.append(stmt)
        self.tgt_nodes.add(name)
        for op, node in [(o, n) for o, n in self.cr_ops if o.cr_anc == name and o.cr_op == OP_M.IA]:
            self._insert_node(op=op, node=node, *args, **kwargs)

    def _insert_node(self, *args, op: CrHeads, node: Optional[cst.CSTNode], **kwargs):
        if not node or not hasattr(node, "name") or node.name.value in self.tgt_nodes:
            return
        self._emit_marker(op=op, *args, **kwargs)
        self.new_body.append(node)
        self.tgt_nodes.add(node.name.value)

    def _emit_marker(self, *args, op: CrHeads, **kwargs):
        marker_text = op.create_marker(cr_id=self.cr_id)
        if self.new_body and not isinstance(self.new_body[-1], cst.EmptyLine):
            self.new_body.append(cst.EmptyLine())
        self.new_body.append(cst.EmptyLine(comment=cst.Comment(marker_text)))


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
        for op, node in reversed(m_ops):
            self._process_module_operation(op, node, new_body)
        return out_node.with_changes(body=tuple(new_body))

    def leave_ClassDef(self, in_node: cst.ClassDef, out_node: cst.ClassDef) -> cst.CSTNode:
        cr_ops = [(op, node) for op, node in self.ops
            if op.cr_type == CRTypes.METHOD and op.class_name == in_node.name.value
        ]
        if not cr_ops:
            return out_node
        return ClassTransformer(in_node, cr_ops, self.cr_id).transform()


# class ApplyCreateTransformer(cst.CSTTransformer):
#     """
#     A transformer specifically for the 'create' operation. It finds the
#     package cr-header and replaces it with a new marker that includes
#     the change ID (cr_id).
#     """

#     def __init__(self, *args, package_op, cr_id: str, **kwargs):
#         self.package_op = package_op
#         self.cr_id = cr_id
#         self.header_found_and_replaced = False

#     def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
#         """Finds and replaces the cr-header comment at the module level."""
#         if self.header_found_and_replaced:
#             return updated_node

#         new_header_nodes = []
#         for header_line in updated_node.header:
#             if (
#                 header_line.comment
#                 and header_line.comment.value.startswith("#--- cr_op:")
#             ):
#                 new_marker = self.package_op.create_marker(cr_id=self.cr_id)
#                 new_comment = cst.Comment(value=new_marker)
#                 new_header_nodes.append(header_line.with_changes(comment=new_comment))
#                 self.header_found_and_replaced = True
#             else:
#                 new_header_nodes.append(header_line)

#         return updated_node.with_changes(header=tuple(new_header_nodes))