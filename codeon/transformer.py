# C:\Users\lars\python_venvs\packages\acodeon\codeon\transformer.py

import libcst as cst
from colorama import Fore, Style
from codeon.headers import CrHeads, CR_OPS, CR_TYPES


class ClassTransformer:
    def __init__(self, *args, in_node, cr_ops, cr_id, **kwargs):
        self.in_node: cst.ClassDef = in_node
        self.cr_ops: list[tuple[CrHeads, cst.CSTNode | None]] = cr_ops
        self.cr_id: str = cr_id
        self.new_body: list[cst.BaseStatement] = list(in_node.body.body)
        self.applied_ops: set[str] = set()

    def transform(self, *args, **kwargs) -> cst.ClassDef:
        pending_ops = list(self.cr_ops)
        while True:
            ops_applied_this_pass = 0
            remaining_ops = []
            for head, node in pending_ops:
                if self._try_apply_op(*args, head=head, node=node, **kwargs):
                    ops_applied_this_pass += 1
                else:
                    remaining_ops.append((head, node))
            if ops_applied_this_pass == 0 or not remaining_ops:
                break  # No progress or all ops are done
            pending_ops = remaining_ops
        if remaining_ops:
            print(
                f"{Fore.YELLOW}Warning: Could not apply all class operations. "
                f"Missing anchors for: "
                f"{[head.cr_anc for head, _ in remaining_ops]}{Style.RESET_ALL}"
            )
        return self.in_node.with_changes(
            body=self.in_node.body.with_changes(body=tuple(self.new_body))
        )

    def _find_anchor_index(self, anc_name: str, *args, **kwargs) -> int:
        """Finds a method/node by name in the *current* self.new_body."""
        for i, stmt in enumerate(self.new_body):
            if (isinstance(stmt, (cst.FunctionDef, cst.ClassDef)) and stmt.name.value == anc_name):
                return i
        return -1

    def _create_marker_node(self, *args, head: CrHeads, **kwargs) -> cst.EmptyLine:
        """Creates a new marker node."""
        marker_text = head.create_marker(cr_id=self.cr_id)
        if head.cr_type not in {"import"}:
            return cst.EmptyLine(comment=cst.Comment(marker_text))
        return cst.EmptyLine(comment=cst.Comment(marker_text))

    def _try_apply_op(self, *args, head: CrHeads, node: cst.CSTNode | None, **kwargs) -> bool:
        """ Attempts to apply a single operation to self.new_body. """
        if head.cr_op == "replace" and head.cr_anc in self.applied_ops:
            return True  # Op already applied (e.g., a prior replace)
        idx = self._find_anchor_index(head.cr_anc, *args, **kwargs)
        if idx == -1:
            return False  # Anchor not found, defer this operation
        marker = self._create_marker_node(*args, head=head, **kwargs)
        nodes_to_add = []
        if head.cr_type == "method":
            nodes_to_add.extend([cst.EmptyLine()])
        # insert nodes based on operation type
        if head.cr_op == "insert_before":
            nodes_to_add.append(marker)
            if node:
                nodes_to_add.append(node)
            self.new_body[idx:idx] = nodes_to_add
        elif head.cr_op == "insert_after":
            nodes_to_add.append(marker)
            if node:
                nodes_to_add.append(node)
            self.new_body[idx + 1 : idx + 1] = nodes_to_add
        elif head.cr_op == "replace":
            nodes_to_add.append(marker)
            if node:
                nodes_to_add.append(node)
            self.new_body[idx : idx + 1] = nodes_to_add
            self.applied_ops.add(head.cr_anc)
        elif head.cr_op == "remove":
            nodes_to_add.append(marker)
            self.new_body[idx : idx + 1] = nodes_to_add
        return True


class ApplyChangesTransformer(cst.CSTTransformer):
    """
    Applies a series of operations to a CST, modifying the tree structure.
    This transformer handles module-level changes (imports) and class-level
    changes (methods).
    """
    import_nodes = {"insert_after", "insert_before"}

    def __init__(self, source, ops: list[tuple], *args, cr_id: str, **kwargs):
        self.source: list = source
        self.ops = ops
        self.cr_id: str = cr_id

    def _create_marker_node(self, head: CrHeads, *args, **kwargs) -> cst.EmptyLine:
        marker_text = head.create_marker(cr_id=self.cr_id)
        return cst.EmptyLine(comment=cst.Comment(marker_text))

    def _apply_op(self, head: CrHeads, node: cst.CSTNode, tgt_idx: int, new_body: list) -> None:
        marker_node = self._create_marker_node(head)
        if head.cr_op == "remove":
            new_body[tgt_idx : tgt_idx + 1] = [marker_node]
            return
        if not node:
            return
        nodes_to_add = []
        if head.cr_type in {"class", "function"}:
            nodes_to_add.extend([cst.EmptyLine(), cst.EmptyLine()])
        nodes_to_add.append(marker_node)
        nodes_to_add.append(node)
        
        if head.cr_op == "replace":
            new_body[tgt_idx : tgt_idx + 1] = nodes_to_add
        elif head.cr_op == "insert_after":
            new_body[tgt_idx + 1 : tgt_idx + 1] = nodes_to_add
        elif head.cr_op == "insert_before":
            new_body[tgt_idx:tgt_idx] = nodes_to_add

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

    def _module_ops(self, head:CrHeads, node:cst.CSTNode, new_body:list, *args, **kwargs) -> None:
        """Find target and apply op; fallback insert for untargeted imports."""
        ti = self._find_target_index(head.cr_anc, new_body) if head.cr_anc else -1
        if ti != -1:
            self._apply_op(head, node, ti, new_body)
        elif node and head.cr_type == "import" and head.cr_op in self.import_nodes:
            idx = self._get_insertion_index(*args, body=new_body, **kwargs)
            new_body.insert(idx, node)

    def leave_Module(self, in_node: cst.Module, out_node: cst.Module) -> cst.Module:
        module_level_types = {"import", "class", "function"}
        m_ops = [(head, node) for head, node in self.ops if head.cr_type in module_level_types]
        if not m_ops:
            return out_node
        new_body = list(out_node.body)
        # Note: Module-level ops do not yet support chaining.
        # They are applied in reverse to maintain indices.
        for head, node in reversed(m_ops):
            self._module_ops(head, node, new_body)
        return out_node.with_changes(body=tuple(new_body))

    def leave_ClassDef(self, in_node: cst.ClassDef, out_node: cst.ClassDef) -> cst.CSTNode:
        cr_ops = [(head, node) for head, node in self.ops
            if head.cr_type == "method" and head.class_name == in_node.name.value ]
        if not cr_ops:
            return out_node
        # Pass the original in_node, not the out_node, to the transformer
        return ClassTransformer(in_node=in_node, cr_ops=cr_ops, cr_id=self.cr_id).transform()