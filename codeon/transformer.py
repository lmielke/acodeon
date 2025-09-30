# C:\Users\lars\python_venvs\packages\acodeon\transformer.py

import libcst as cst
from codeon.op_codes import OpCodes, OF, OPObjects


class ClassTransformer:
    def __init__(
        self,
        in_node: cst.ClassDef,
        op_codes: list[OpCodes],
        ch_id: str,
        *args,
        **kwargs,
    ):
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
        removals = {op.target: op for op in self.op_codes if op.op_type == OF.REMOVE}
        replacements = {
            op.target: op for op in self.op_codes if op.op_type == OF.REPLACE
        }
        return removals, replacements

    def _process_method_statement(self, *args, stmt: cst.FunctionDef, **kwargs):
        name = stmt.name.value
        if name in self.removals:
            self._emit_marker(op=self.removals[name], *args, **kwargs)
            return
        if name in self.replacements:
            op = self.replacements[name]
            self._emit_marker(op=op, *args, **kwargs)
            self.new_body.append(op.node)
            self.tgt_nodes.add(name)
            return
        for op in [
            o
            for o in self.op_codes
            if o.target == name and o.op_type == OF.INSERT_BEFORE
        ]:
            self._insert_node(op=op, *args, **kwargs)
        self.new_body.append(stmt)
        self.tgt_nodes.add(name)
        for op in [
            o
            for o in self.op_codes
            if o.target == name and o.op_type == OF.INSERT_AFTER
        ]:
            self._insert_node(op=op, *args, **kwargs)

    def _insert_node(self, *args, op: OpCodes, **kwargs):
        if (
            not op.node
            or not hasattr(op.node, "name")
            or op.node.name.value in self.tgt_nodes
        ):
            return
        self._emit_marker(op=op, *args, **kwargs)
        self.new_body.append(op.node)
        self.tgt_nodes.add(op.node.name.value)

    def _emit_marker(self, *args, op: OpCodes, **kwargs):
        marker_text = op.create_marker(ch_id=self.ch_id)
        if self.new_body and not isinstance(self.new_body[-1], cst.EmptyLine):
            self.new_body.append(cst.EmptyLine())
        self.new_body.append(cst.EmptyLine(comment=cst.Comment(marker_text)))


class ApplyChangesTransformer(cst.CSTTransformer):
    import_nodes = {OF.INSERT_AFTER, OF.INSERT_BEFORE}

    def __init__(self, *args, operations: list[OpCodes], ch_id: str | None = None, **kwargs):
        self.operations = operations
        self.ch_id = ch_id or "unknown"

    def leave_Module(self, in_node: cst.Module, out_node: cst.Module) -> cst.Module:
            m_ops = [op for op in self.operations if op.obj == OPObjects.IMPORT]
            if not m_ops:
                return out_node

            new_body = list(out_node.body)

            # We must iterate in reverse to ensure that our modifications don't
            # invalidate the indices of statements we still need to find.
            for op in reversed(m_ops):
                target_index = -1
                # Find the specific target statement if one is provided
                if op.target:
                    for i, stmt in enumerate(new_body):
                        # Render the statement to a string for simple comparison
                        stmt_code = cst.Module([stmt]).code.strip()
                        if stmt_code == op.target.strip():
                            target_index = i
                            break

                if target_index != -1:
                    # A specific target was found, act on it
                    if op.op_type == OF.REMOVE:
                        del new_body[target_index]
                    elif op.op_type == OF.INSERT_AFTER:
                        if op.node:
                            new_body.insert(target_index + 1, op.node)
                    elif op.op_type == OF.INSERT_BEFORE:
                        if op.node:
                            new_body.insert(target_index, op.node)
                    elif op.op_type == OF.REPLACE:
                        if op.node:
                            new_body[target_index] = op.node
                else:
                    # Fallback for non-targeted insertions
                    if op.node and op.op_type in self.import_nodes:
                        last_import_index = -1
                        docstring_index = -1
                        for i, stmt in enumerate(new_body):
                            if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                                last_import_index = i
                            elif (
                                isinstance(stmt, cst.SimpleStatementLine)
                                and isinstance(stmt.body[0], cst.Expr)
                                and isinstance(stmt.body[0].value, cst.SimpleString)
                            ):
                                if docstring_index == -1 and last_import_index == -1:
                                    docstring_index = i

                        if last_import_index != -1:
                            idx = last_import_index + 1
                        elif docstring_index != -1:
                            idx = docstring_index + 1
                        else:
                            idx = 0
                        new_body.insert(idx, op.node)

            return out_node.with_changes(body=tuple(new_body))

    def leave_ClassDef(self, in_node: cst.ClassDef, out_node: cst.ClassDef) -> cst.CSTNode:
        """
        Note: this class does not use *args, **kwargs because the signature
        must match the CSTTransformer method exactly.
        """
        op_codes = [op for op in self.operations
            if op.obj == OPObjects.METHOD and op.class_name == in_node.name.value
        ]
        if not op_codes:
            return out_node
        return ClassTransformer(in_node, op_codes, self.ch_id).transform()