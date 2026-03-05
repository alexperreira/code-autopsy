"""Tests for cyclomatic_complexity() and CyclomaticComplexityRule."""
import ast
from pathlib import Path

import pytest

from autopsy.config import Config, ThresholdConfig
from autopsy.models import Severity
from autopsy.rules.complexity import CyclomaticComplexityRule, cyclomatic_complexity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURE = Path(__file__).parent / "fixtures" / "complexity_samples.py"
_SOURCE = FIXTURE.read_text()
_TREE = ast.parse(_SOURCE)


def _get_func(name: str) -> ast.FunctionDef:
    for node in ast.walk(_TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise KeyError(f"Function '{name}' not found in fixture")


# ---------------------------------------------------------------------------
# cyclomatic_complexity() — individual cases
# ---------------------------------------------------------------------------


def test_trivial():
    assert cyclomatic_complexity(_get_func("trivial")) == 1


def test_single_if():
    assert cyclomatic_complexity(_get_func("single_if")) == 2


def test_if_elif():
    # elif becomes a nested If node → +2 total
    assert cyclomatic_complexity(_get_func("if_elif")) == 3


def test_for_loop():
    assert cyclomatic_complexity(_get_func("for_loop")) == 2


def test_while_loop():
    assert cyclomatic_complexity(_get_func("while_loop")) == 2


def test_try_except():
    assert cyclomatic_complexity(_get_func("try_except")) == 2


def test_two_excepts():
    assert cyclomatic_complexity(_get_func("two_excepts")) == 3


def test_with_stmt():
    assert cyclomatic_complexity(_get_func("with_stmt")) == 2


def test_assert_stmt():
    assert cyclomatic_complexity(_get_func("assert_stmt")) == 2


def test_bool_and():
    assert cyclomatic_complexity(_get_func("bool_and")) == 2


def test_bool_or():
    assert cyclomatic_complexity(_get_func("bool_or")) == 2


def test_bool_three_and():
    # 3 operands → len(values) - 1 = 2 → CC = 1 + 2 = 3
    assert cyclomatic_complexity(_get_func("bool_three_and")) == 3


def test_list_comp_with_if():
    assert cyclomatic_complexity(_get_func("list_comp_with_if")) == 2


def test_list_comp_two_ifs():
    assert cyclomatic_complexity(_get_func("list_comp_two_ifs")) == 3


def test_nested_func_isolation():
    # Outer function: 1 (base) + 1 (if) = 2; inner function not counted
    assert cyclomatic_complexity(_get_func("nested_func_isolation")) == 2


def test_complex_func():
    assert cyclomatic_complexity(_get_func("complex_func")) == 5


# ---------------------------------------------------------------------------
# CyclomaticComplexityRule
# ---------------------------------------------------------------------------


def _make_config(threshold: int) -> Config:
    cfg = Config()
    cfg.thresholds.max_cyclomatic_complexity = threshold
    return cfg


def _make_func_metrics(name: str, cc: int):
    from autopsy.models import FunctionMetrics
    return FunctionMetrics(
        name=name,
        start_line=1,
        end_line=10,
        line_count=10,
        arg_count=0,
        max_nesting_depth=0,
        cyclomatic=cc,
        cognitive=0,
    )


_rule = CyclomaticComplexityRule()
_dummy_path = Path("dummy.py")


def test_rule_no_issue_below_threshold():
    func = _make_func_metrics("f", cc=5)
    issues = _rule.check(func, _dummy_path, _make_config(10))
    assert issues == []


def test_rule_warning_at_threshold():
    func = _make_func_metrics("f", cc=10)
    issues = _rule.check(func, _dummy_path, _make_config(10))
    assert len(issues) == 1
    assert issues[0].severity == Severity.WARNING
    assert issues[0].rule_id == "complexity.cyclomatic"


def test_rule_warning_above_threshold():
    func = _make_func_metrics("f", cc=14)
    issues = _rule.check(func, _dummy_path, _make_config(10))
    assert len(issues) == 1
    assert issues[0].severity == Severity.WARNING


def test_rule_error_at_double_threshold():
    func = _make_func_metrics("f", cc=20)
    issues = _rule.check(func, _dummy_path, _make_config(10))
    assert len(issues) == 1
    assert issues[0].severity == Severity.ERROR


def test_rule_error_above_double_threshold():
    func = _make_func_metrics("f", cc=25)
    issues = _rule.check(func, _dummy_path, _make_config(10))
    assert len(issues) == 1
    assert issues[0].severity == Severity.ERROR


def test_rule_message_contains_name_and_values():
    func = _make_func_metrics("my_func", cc=15)
    issues = _rule.check(func, _dummy_path, _make_config(10))
    assert "my_func" in issues[0].message
    assert "15" in issues[0].message
    assert "10" in issues[0].message


def test_rule_issue_file_and_line():
    func = _make_func_metrics("f", cc=10)
    issues = _rule.check(func, Path("src/foo.py"), _make_config(10))
    assert issues[0].file == Path("src/foo.py")
    assert issues[0].line == 1


# ---------------------------------------------------------------------------
# Integration: PythonAnalyzer populates cyclomatic in FunctionMetrics
# ---------------------------------------------------------------------------


def test_analyzer_populates_cyclomatic():
    from autopsy.analyzers.python import PythonAnalyzer

    analyzer = PythonAnalyzer()
    result = analyzer.analyze(FIXTURE, _SOURCE)
    func_map = {f.name: f for f in result.metrics.functions}

    assert func_map["trivial"].cyclomatic == 1
    assert func_map["single_if"].cyclomatic == 2
    assert func_map["complex_func"].cyclomatic == 5


def test_analyzer_aggregates_max_cyclomatic():
    from autopsy.analyzers.python import PythonAnalyzer

    analyzer = PythonAnalyzer()
    result = analyzer.analyze(FIXTURE, _SOURCE)
    # complex_func has CC=5, which should be the max
    assert result.metrics.max_cyclomatic == 5


def test_analyzer_emits_cc_issues_when_config_provided():
    from autopsy.analyzers.python import PythonAnalyzer

    analyzer = PythonAnalyzer()
    cfg = _make_config(threshold=3)  # complex_func (CC=5) should trigger
    result = analyzer.analyze(FIXTURE, _SOURCE, cfg)
    rule_ids = [i.rule_id for i in result.issues]
    assert "complexity.cyclomatic" in rule_ids


def test_analyzer_no_cc_issues_without_config():
    from autopsy.analyzers.python import PythonAnalyzer

    analyzer = PythonAnalyzer()
    result = analyzer.analyze(FIXTURE, _SOURCE)  # no config → no rule issues
    assert result.issues == []
