# dir_context.py
from __future__ import annotations
import os, ast
from typing import Any, Iterable
from dataclasses import dataclass


@dataclass
class DirContext:
    """
    WHY: Single source of truth about a path (file/dir) within a project tree.
         Resolves workspace (project/package), optional file facets, and can
         emit legacy kwargs flags derived from package_info.
    """
    # core
    work_dir: str | None = None
    project_dir: str | None = None
    package_dir: str | None = None
    is_package: bool = False
    pr_name: str | None = None
    pg_name: str | None = None
    # file facet
    file_path: str | None = None
    work_file_name: str | None = None
    file_dir: str | None = None
    is_test_file: bool = False
    import_path: str | None = None
    test_cmd: str | None = None
    class_name: str | None = None
    method_name: str | None = None
    # config
    project_key: str = "setup.py"
    package_key: str = "__main__.py"

    # ---------- factories ----------
    @classmethod
    def __call__(cls, *args, path: str | None = None, cursor_pos: int | None = None, **kwargs,
    ) -> DirContext:
        """
        WHY: Make DirContext callable as a class. Builds a full context object
        from a file or directory path. Uses default project/package key config.
        """
        abs_path = cls._abs_path(path)
        work_dir = cls._derive_work_dir(abs_path)
        project_dir = cls._find_root(work_dir, cls.project_key)
        package_dir = cls._find_package_dir(project_dir or work_dir, cls.package_key)
        is_package = package_dir is not None
        file_path, work_file_name, file_dir = cls._file_facet(abs_path)
        class_name, method_name = cls._ast_symbols(file_path, cursor_pos)

        return cls(
            work_dir=work_dir,
            project_dir=project_dir,
            package_dir=package_dir,
            is_package=is_package,
            pr_name=(os.path.basename(project_dir) if is_package and project_dir else None),
            pg_name=(os.path.basename(package_dir) if is_package and package_dir else None),
            file_path=file_path,
            work_file_name=work_file_name,
            file_dir=file_dir,
            is_test_file=bool(work_file_name and work_file_name.startswith("test")),
            import_path=cls._import_path(file_path, project_dir),
            test_cmd=cls._test_cmd(file_path, project_dir),
            class_name=class_name,
            method_name=method_name,
            project_key=cls.project_key,
            package_key=cls.package_key,
        )


    # ---------- public API ----------
    def to_kwargs(
        self, *args, package_info: Iterable[str] | None = None,
        verbose: bool = False, **kwargs,
    ) -> dict[str, Any]:
        """
        WHY: Emit kwargs flags compatible with existing callers.
        Mirrors prior prep_package_info semantics.
        """
        out = dict(**kwargs, is_package=self.is_package)
        if package_info and self.is_package:
            out["package_info"] = True
            for k in package_info: out[k] = True
        elif package_info and not self.is_package:
            if verbose:
                print(
                    f"WARNING: package_info set, but is_package is False! Only pg_tree used!"
                      )
            out["package_info"] = True
            if "pg_tree" in package_info: out["pg_tree"] = True
        else:
            out["package_info"] = False
        return out

    def snapshot(self, *args, **kwargs) -> dict[str, Any]:
        """
        WHY: Flat dict for logging/tests; stable, easy to diff.
        """
        return {
            "work_dir": self.work_dir, "project_dir": self.project_dir,
            "package_dir": self.package_dir, "is_package": self.is_package,
            "pr_name": self.pr_name, "pg_name": self.pg_name,
            "file_path": self.file_path, "work_file_name": self.work_file_name,
            "file_dir": self.file_dir, "is_test_file": self.is_test_file,
            "import_path": self.import_path, "test_cmd": self.test_cmd,
            "class_name": self.class_name, "method_name": self.method_name,
            "project_key": self.project_key, "package_key": self.package_key,
        }

    def refresh(
        self, *args, path: str | None = None, cursor_pos: int | None = None, **kwargs,
    ) -> "DirContext":
        """
        WHY: Recompute after FS changes or when switching path.
        Calls the class itself (via __call__) using current config.
        """
        base_path = path or self.file_path or self.work_dir
        return type(self)(path=base_path, cursor_pos=cursor_pos)


    # ---------- helpers (small, focused) ----------
    @staticmethod
    def _abs_path(path: str | None) -> str:
        if path: return os.path.abspath(path)
        return os.path.abspath(os.getcwd())

    @staticmethod
    def _derive_work_dir(path: str) -> str:
        return path if os.path.isdir(path) else os.path.dirname(path)

    @staticmethod
    def _find_root(start_dir: str, key_file: str) -> str | None:
        cur, up = start_dir, os.path.dirname(start_dir)
        while cur != up:
            if key_file in os.listdir(cur): return cur
            cur, up = up, os.path.dirname(up)
        return None

    @staticmethod
    def _find_package_dir(root_or_work: str | None, key_file: str) -> str | None:
        if not root_or_work: return None
        for n in os.listdir(root_or_work):
            p = os.path.join(root_or_work, n)
            if os.path.isdir(p) and key_file in os.listdir(p): return p
        # also allow "package as work_dir" when no root was found
        if key_file in os.listdir(root_or_work): return root_or_work
        return None

    @staticmethod
    def _file_facet(path: str) -> tuple[str | None, str | None, str | None]:
        if os.path.isdir(path): return None, None, None
        return path, os.path.basename(path), os.path.dirname(path)

    @staticmethod
    def _import_path(file_path: str | None, root_dir: str | None) -> str | None:
        if not file_path or not root_dir: return None
        af, ar = os.path.abspath(file_path), os.path.abspath(root_dir)
        if not af.startswith(ar): return None
        rel = af[len(ar):].lstrip(os.path.sep)
        return os.path.splitext(rel)[0].replace(os.path.sep, ".")

    @staticmethod
    def _test_cmd(file_path: str | None, root_dir: str | None) -> str | None:
        if not file_path or not root_dir: return None
        rel = os.path.splitext(file_path[len(root_dir):].lstrip(os.path.sep))[0]
        return f"python -m unittest {rel.replace(os.path.sep, '.')}"

    @staticmethod
    def _ast_symbols(
        file_path: str | None, cursor_pos: int | None,
    ) -> tuple[str | None, str | None]:
        if not file_path or cursor_pos is None: return None, None
        try:
            with open(file_path, encoding="utf-8") as f: txt = f.read()
            line = DirContext._line_idx(txt, cursor_pos)
            tree = ast.parse(txt)
        except Exception:
            return None, None
        c = DirContext._class_at_line(tree, line)
        m = DirContext._func_at_line(tree, line)
        return c, m

    @staticmethod
    def _line_idx(text: str, pos: int) -> int:
        cur = 0
        for i, ln in enumerate(text.splitlines(keepends=True)):
            if cur + len(ln) > pos: return i
            cur += len(ln)
        return max(0, len(text.splitlines()) - 1)

    @staticmethod
    def _class_at_line(tree: ast.AST, line: int) -> str | None:
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef):
                s, e = n.lineno - 1, (max((b.lineno for b in n.body), default=n.lineno) - 1)
                if s <= line <= e: return n.name
        return None

    @staticmethod
    def _func_at_line(tree: ast.AST, line: int) -> str | None:
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef):
                s, e = n.lineno - 1, (max((b.lineno for b in n.body), default=n.lineno) - 1)
                if s <= line <= e: return n.name
        return None
