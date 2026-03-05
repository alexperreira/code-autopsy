import ast
from pathlib import Path

from autopsy.config import Config
from autopsy.models import FunctionMetrics, Issue, Severity


def cyclomatic_complexity(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Compute cyclomatic complexity for a single function.

    Base = 1. +1 per decision point:
        If, While, For, ExceptHandler, With, Assert
        BoolOp: +1 per additional operand (len(values) - 1)
        Comprehension filter: +1 per `if` clause in each generator
        match_case: +1 per arm (Python 3.10+)

    Does not cross nested function or class boundaries.
    """
    count = 1

    def _walk(node: ast.AST) -> None:
        nonlocal count
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # do not cross scope boundaries

            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                  ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Assert)):
                count += 1
            elif isinstance(child, ast.BoolOp):
                count += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                for generator in child.generators:
                    count += len(generator.ifs)
            elif hasattr(ast, "match_case") and isinstance(child, ast.match_case):
                count += 1

            _walk(child)

    _walk(func_node)
    return count


class CyclomaticComplexityRule:
    rule_id = "complexity.cyclomatic"

    def check(self, func: FunctionMetrics, path: Path, config: Config) -> list[Issue]:
        threshold = config.thresholds.max_cyclomatic_complexity
        cc = func.cyclomatic

        if cc >= 2 * threshold:
            severity = Severity.ERROR
            msg = (
                f"'{func.name}': cyclomatic complexity {cc} is ≥2× threshold ({threshold}) — ERROR"
            )
        elif cc >= threshold:
            severity = Severity.WARNING
            msg = f"'{func.name}': cyclomatic complexity {cc} exceeds threshold ({threshold})"
        else:
            return []

        return [
            Issue(
                rule_id=self.rule_id,
                severity=severity,
                message=msg,
                file=path,
                line=func.start_line,
                col=0,
            )
        ]
