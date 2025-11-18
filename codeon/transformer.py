# C:\Users\lars\python_venvs\packages\acodeon\codeon\transformer.py

import libcst as cst
from colorama import Fore, Style
from codeon.headers import CrHeads, CR_OPS
from typing import TypeVar

# Define a type variable for cleaner type hints in generics
T = TypeVar('T', bound=cst.BaseStatement)


class _BaseOpMixin:
    """Provides generic list mutation logic with CR-marker de-dupe."""

    def _is_marker(self, s, *args, **kwargs) -> bool:
        return isinstance(s, cst.EmptyLine) and getattr(s, "comment", None) and \
            s.comment.value.lstrip().startswith(("#--", "#---"))

    def _strip_above(self, body: list[T], idx: int, *args, **kwargs) -> int:
        k = idx
        while k > 0 and self._is_marker(body[k - 1]):
            k -= 1
        return k

    def _strip_at(self, body: list[T], idx: int, *args, **kwargs) -> int:
        while idx < len(body) and self._is_marker(body[idx]):
            del body[idx]
        return idx

    #-- cr_op: insert_after, cr_type: method, cr_anc: _BaseOpMixin._strip_at, cr_id: 2025-11-03-12-23-55 --#
    def _normalize(self, s: str) -> str:
        """Removes all whitespace and converts to lowercase for fault-tolerant matching."""
        return s.replace(" ", "").replace("\t", "").lower()

    def _insert_before(self, *args, body: list[T], idx: int, nodes: list[cst.BaseStatement],
        marker: cst.EmptyLine = None, **kwargs ) -> list[T]:
        k = self._strip_above(body, idx)
        body[k:k] = nodes
        return body

    def _insert_after(self, *args, body: list[T], idx: int, nodes: list[cst.BaseStatement],
        marker: cst.EmptyLine = None, **kwargs ) -> list[T]:
        pos = self._strip_at(body, idx + 1)
        body[pos:pos] = nodes
        return body

    def _replace(self, *args, body: list[T], idx: int, nodes: list[cst.BaseStatement],
        marker: cst.EmptyLine = None, **kwargs ) -> list[T]:
        k = self._strip_above(body, idx)
        body[k:idx + 1] = nodes
        return body

    def _remove(self, *args, body: list[T], idx: int, marker: cst.EmptyLine, **kwargs) -> list[T]:
        k = self._strip_above(body, idx)
        body[k:idx + 1] = [cst.EmptyLine(), marker]
        return body


class _BaseTransformer(_BaseOpMixin):
    """Base class for scope-specific finding logic."""

    def __init__(self, *args, cr_id: str, **kwargs):
        self.cr_id: str = cr_id

    def _create_marker_node(self, head: CrHeads, *args, **kwargs) -> cst.EmptyLine:
        """Creates a marker node with the change request ID."""
        marker_text = head.create_marker(cr_id=self.cr_id)
        return cst.EmptyLine(comment=cst.Comment(marker_text))

    #-- cr_op: replace, cr_type: method, cr_anc: _BaseTransformer.dispatch, cr_id: 2025-11-03-12-29-12 --#
    def dispatch(
        self, *args, head: CrHeads, node: cst.CSTNode | None, source: cst.CSTNode, **kwargs
        ) -> tuple[cst.CSTNode, bool]:
        """Route op; skip no-ops; build nodes; apply op. Includes anchor validation."""
        idx = self._find_anchor_index(head, source, *args, **kwargs)

        # --- ANCHOR VALIDATION ---
        if idx == -1:
            print(f"{Fore.RED}CR Anchor NOT FOUND: "
                  f"cr_anc='{head.cr_anc}' cr_type='{head.cr_type}' "
                  f"in source.{Style.RESET_ALL}")
            return source, False
        # -------------------------

        body = list(self._access_body(source))
        if self._should_skip(body, idx, head, node):
            return source, False
        nodes = self._nodes_for(head, node, *args, **kwargs)
        op = getattr(self, f"_{head.cr_op}")
        new_body = op(*args, body=body, idx=idx, nodes=nodes, marker=nodes[0], **kwargs)
        return self._wrap_new_body_with(source, new_body), True


    def _should_skip(self, body: list[T], idx: int, head: CrHeads, node: cst.CSTNode ) -> bool:
        """Skip if replace is identical or insert duplicates the adjacent block."""
        if head.cr_op == "replace" and node and self._same_code(body[idx], node):
            return True
        if head.cr_op in {"insert_before", "insert_after"} and node:
            return self._duplicate_insert(body, idx, head, node)
        return False

    def _nodes_for(self, head: CrHeads, node: cst.CSTNode, *args, **kwargs
        ) -> list[cst.BaseStatement]:
        """Assemble [marker,(spacers),node] consistently."""
        marker = self._create_marker_node(head, *args, **kwargs)
        if head.cr_op == "remove":
            return [marker]
        out: list[cst.BaseStatement] = []
        if head.cr_type == "method" and head.cr_op in {"insert_before","insert_after","replace"}:
            out.append(cst.EmptyLine())
        elif head.cr_type == "class":
            out.extend([cst.EmptyLine(), cst.EmptyLine()])
        out.append(marker)
        if node:
            out.append(node)
        return out

    def _same_code(self, a: cst.CSTNode, b: cst.CSTNode, *args, **kwargs) -> bool:
        """Compare normalized single-statement code."""
        aa = a.body[0] if isinstance(a, cst.SimpleStatementLine) else a
        return cst.Module([aa]).code.strip() == cst.Module([b]).code.strip()

    def _first_non_marker_up(self, body: list[T], j: int, *args, **kwargs) -> int:
        while j >= 0 and self._is_marker(body[j]):
            j -= 1
        return j

    def _first_non_marker_down(self, body: list[T], j: int, *args, **kwargs) -> int:
        n = len(body)
        while j < n and self._is_marker(body[j]):
            j += 1
        return j

    def _duplicate_insert(self, body: list[T], idx: int, head: CrHeads, node: cst.CSTNode,
        *args, **kwargs) -> bool:
        """Detect same code already adjacent at insertion site."""
        if head.cr_op == "insert_before":
            j = self._first_non_marker_up(body, idx - 1)
        else:  # insert_after
            j = self._first_non_marker_down(body, idx + 1)
        if j < 0 or j >= len(body):
            return False
        return self._same_code(body[j], node)


    def _access_body(self, source: cst.CSTNode, *args, **kwargs) -> tuple[cst.BaseStatement, ...]:
        """Generic body access (works for Module)."""
        return source.body

    def _wrap_new_body_with(self, source: cst.CSTNode, new_body: list[cst.BaseStatement],
        *args, **kwargs) -> cst.CSTNode:
        """Generic body wrapping (works for Module)."""
        return source.with_changes(body=tuple(new_body))

    def _find_anchor_index(self, head: CrHeads, source: cst.CSTNode, *args, **kwargs) -> int:
        raise NotImplementedError("Subclasses must implement _find_anchor_index.")


class ModuleTransformer(_BaseTransformer):
    """Handles top-level imports, classes, and functions."""

    def _find_anchor_index(self, head: CrHeads, source: cst.Module, *args, **kwargs) -> int:
        """Finds a top-level anchor using the appropriate method."""
        if head.cr_type == "import":
            return self._find_import_anchor(head.cr_anc, source.body, *args, **kwargs)
        return self._find_tgt_idx(head.cr_anc, source.body, *args, **kwargs)

    #-- cr_op: replace, cr_type: method, cr_anc: ModuleTransformer._find_tgt_idx, cr_id: 2025-11-03-12-23-55 --#
    def _find_tgt_idx(self, target_str: str, body: list[cst.BaseStatement], *args, **kwargs) -> int:
        """Finds class/function by name or statement by normalized code match (fallback)."""
        t = self._normalize(target_str)
        for i, stmt in enumerate(body):
            s = stmt.body[0] if isinstance(stmt, cst.SimpleStatementLine) else stmt

            # 1. Class/Function Match (Name remains case-sensitive as per Python convention)
            if isinstance(s, (cst.ClassDef, cst.FunctionDef)) and s.name.value == target_str.strip():
                return i

            # 2. Normalized Code Match (Fallback)
            code_str = cst.Module([s]).code.strip()
            if self._normalize(code_str) == t:
                return i

        return -1

    def _find_import_anchor(self, anchor_str: str, body: list, *args, **kwargs) -> int:
        """Find import by prefix to allow partial anchors (tolerant match)."""
        t = anchor_str.strip()
        for i, st in enumerate(body):
            s = st.body[0] if isinstance(st, cst.SimpleStatementLine) else st
            if cst.Module([s]).code.strip().startswith(t):
                return i
        return -1


class ClassMethodTransformer(_BaseTransformer):
    """Handles methods and other statements inside a ClassDef."""


    def _find_anchor_index(self, head: CrHeads, source: cst.ClassDef, *args, **kwargs) -> int:
        """Finds a method anchor by name in the class body, deriving names from cr_anc."""
        if head.cr_type != "method":
             return -1
        # Separate ClassName.MethodName from cr_anc (Method)
        try:
            class_name, method_name = head.cr_anc.split(".", 1)
        except ValueError:
            # Anchor must be Class.Method for method-type operations
            return -1
        if class_name != source.name.value:
            return -1
        class_statements = source.body.body # Access class body statements
        for i, stmt in enumerate(class_statements):
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == method_name:
                return i
        return -1

    def _access_body(self, source: cst.ClassDef) -> tuple[cst.BaseStatement, ...]:
        """Returns the class body's statements tuple (source.body.body)."""
        body: tuple[cst.BaseStatement, ...] = source.body.body
        return body

    def _wrap_new_body_with(self, source: cst.ClassDef, new_body: list[cst.BaseStatement]) -> cst.ClassDef:
        """Wraps the modified list of statements back into a ClassDef node."""
        new_indented_block = source.body.with_changes(body=tuple(new_body))
        return source.with_changes(body=new_indented_block)


class Transformer:
    """The main entry point: runs the multi-pass loop and delegates to specialized transformers."""


    def __init__(self, csts_body, cstd_body, *args, cr_id, **kwargs):
        self.source: cst.Module = csts_body
        self.cstd_body: cst.Module = cstd_body
        self.pg_head, self.cr_ops = self.cstd_body
        self.cr_id: str = cr_id
        self.applied_ops: set[str] = set()
        self.module_handler = ModuleTransformer(*args, cr_id=cr_id, **kwargs)
        self.class_handler = ClassMethodTransformer(*args, cr_id=cr_id, **kwargs)

    #-- cr_op: replace, cr_type: method, cr_anc: Transformer.__call__, cr_id: 2025-11-05-14-21-57 --#
    def __call__(self, *args, **kwargs) -> 'Transformer':
        """Main multi-pass loop to resolve dependencies."""
        pending_ops = list(self.cr_ops)
        while True:
            ops_applied_this_pass = 0
            remaining_ops = []
            # Process each pending operation
            for head, node in pending_ops:
                if head.cr_type == "method":
                    new_source, success = self._apply_class_op(head, node, *args, **kwargs)
                elif head.cr_type in {"import", "class", "function"}:
                    new_source, success = self._apply_module_op(head, node, *args, **kwargs)
                else:
                    new_source, success = self.source, False # Unsupported type
                if success:
                    self.source = new_source
                    ops_applied_this_pass += 1
                else:
                    remaining_ops.append((head, node))
            if ops_applied_this_pass == 0 or not remaining_ops:
                break
            pending_ops = remaining_ops
        if remaining_ops:
            print(f"{Fore.YELLOW}Warning: Could not apply all changes...{Style.RESET_ALL}")
        # Return the instance itself so we can access properties like 'code'
        return self

    def _apply_module_op(self, head: CrHeads, node: cst.CSTNode | None, *args, **kwargs) -> tuple[cst.Module, bool]:
        """Applies operations targeting the top-level module body."""
        return self.module_handler.dispatch(head=head, node=node, source=self.source, *args, **kwargs)

    def _apply_class_op(self, head: CrHeads, node: cst.CSTNode | None, *args, **kwargs) -> tuple[cst.Module, bool]:
        """Finds the target ClassDef in the module and applies method operations."""
        # 1. Derive class_name from cr_anc for finding the class node
        try:
            class_name, _ = head.cr_anc.split(".", 1)
        except ValueError:
            return self.source, False # Malformed cr_anc
        tgt_cls_idx = self.module_handler._find_tgt_idx(class_name, self.source.body,
                                                             *args, **kwargs)
        if tgt_cls_idx == -1:
            return self.source, False # Class anchor not found
        target_class_node: cst.ClassDef = self.source.body[tgt_cls_idx]
        # 2. Dispatch to the ClassMethodTransformer (now operates on full cr_anc)
        new_class_node, success = self.class_handler.dispatch(
            head=head, node=node, source=target_class_node, *args, **kwargs
        )
        if not success:
            return self.source, False
        # 3. Replace the old ClassDef node with the new one in the module body
        new_module_body = list(self.source.body)
        new_module_body[tgt_cls_idx] = new_class_node
        return self.source.with_changes(body=tuple(new_module_body)), True