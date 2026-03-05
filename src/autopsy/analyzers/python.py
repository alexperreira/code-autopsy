import ast
import logging
from pathlib import Path

from autopsy.analyzers.base import BaseAnalyzer
from autopsy.config import Config
from autopsy.models import (
    ClassMetrics,
    FileMetrics,
    FileResult,
    FunctionMetrics,
    Issue,
    Severity,
)
from autopsy.rules.complexity import CyclomaticComplexityRule, cyclomatic_complexity

log = logging.getLogger(__name__)

_NESTING_TYPES = (ast.If, ast.For, ast.While, ast.With, ast.Try)


def _max_nesting_depth(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Max depth of control-flow nesting within the function (does not cross into nested functions)."""

    def _walk(node: ast.AST, depth: int) -> int:
        best = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue  # nested function — its own scope
            next_depth = depth + 1 if isinstance(child, _NESTING_TYPES) else depth
            best = max(best, _walk(child, next_depth))
        return best

    return _walk(func_node, 0)


def _arg_count(args: ast.arguments) -> int:
    """Count arguments, excluding self/cls."""
    positional = args.posonlyargs + args.args
    count = len(positional)
    if positional and positional[0].arg in ("self", "cls"):
        count -= 1
    count += len(args.kwonlyargs)
    if args.vararg:
        count += 1
    if args.kwarg:
        count += 1
    return max(0, count)


class _Visitor(ast.NodeVisitor):
    """Single-pass AST visitor that collects function and class metrics."""

    def __init__(self) -> None:
        self.functions: list[FunctionMetrics] = []
        self.classes: list[ClassMetrics] = []
        self.import_count: int = 0

    def visit_Import(self, node: ast.Import) -> None:
        self.import_count += 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.import_count += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.generic_visit(node)
        method_count = sum(
            1
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        self.classes.append(
            ClassMetrics(
                name=node.name,
                start_line=node.lineno,
                end_line=node.end_lineno,
                line_count=node.end_lineno - node.lineno + 1,
                method_count=method_count,
            )
        )

    def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.generic_visit(node)
        self.functions.append(
            FunctionMetrics(
                name=node.name,
                start_line=node.lineno,
                end_line=node.end_lineno,
                line_count=node.end_lineno - node.lineno + 1,
                arg_count=_arg_count(node.args),
                max_nesting_depth=_max_nesting_depth(node),
                cyclomatic=cyclomatic_complexity(node),
                cognitive=0,  # populated later (Week 2 cognitive task)
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_func(node)


_cc_rule = CyclomaticComplexityRule()


class PythonAnalyzer(BaseAnalyzer):
    """Analyzes Python source files via the stdlib ast module."""

    language = "python"

    def analyze(self, path: Path, source: str, config: Config | None = None) -> FileResult:
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            issue = Issue(
                rule_id="python.syntax-error",
                severity=Severity.ERROR,
                message=f"Syntax error: {exc.msg} (line {exc.lineno})",
                file=path,
                line=exc.lineno or 1,
                col=exc.offset or 0,
            )
            empty_metrics = FileMetrics(
                total_lines=len(source.splitlines()),
                function_count=0,
                class_count=0,
                import_count=0,
                max_cyclomatic=0,
                avg_cyclomatic=0.0,
                max_cognitive=0,
            )
            return FileResult(
                path=path,
                language=self.language,
                metrics=empty_metrics,
                issues=[issue],
            )

        visitor = _Visitor()
        visitor.visit(tree)

        lines = source.splitlines()
        cyclomatics = [f.cyclomatic for f in visitor.functions]
        metrics = FileMetrics(
            total_lines=len(lines),
            function_count=len(visitor.functions),
            class_count=len(visitor.classes),
            import_count=visitor.import_count,
            max_cyclomatic=max(cyclomatics, default=0),
            avg_cyclomatic=sum(cyclomatics) / len(cyclomatics) if cyclomatics else 0.0,
            max_cognitive=max((f.cognitive for f in visitor.functions), default=0),
            functions=visitor.functions,
            classes=visitor.classes,
        )

        issues: list[Issue] = []
        if config is not None:
            for func in visitor.functions:
                issues.extend(_cc_rule.check(func, path, config))

        return FileResult(
            path=path,
            language=self.language,
            metrics=metrics,
            issues=issues,
        )
