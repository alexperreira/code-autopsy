"""Tests for autopsy.analyzers.python.PythonAnalyzer."""
from pathlib import Path

import pytest

from autopsy.analyzers.python import PythonAnalyzer
from autopsy.models import Severity

FIXTURE = Path(__file__).parent / "fixtures" / "sample_functions.py"
ANALYZER = PythonAnalyzer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def analyze_fixture():
    return ANALYZER.analyze(FIXTURE, FIXTURE.read_text())


def func_by_name(result, name):
    return next(f for f in result.metrics.functions if f.name == name)


# ---------------------------------------------------------------------------
# Function names and line counts
# ---------------------------------------------------------------------------


def test_collects_all_function_names():
    result = analyze_fixture()
    names = {f.name for f in result.metrics.functions}
    assert names == {"simple", "with_branch", "nested_loops", "__init__", "compute", "async_fn"}


def test_function_line_counts():
    result = analyze_fixture()
    assert func_by_name(result, "simple").line_count == 3
    assert func_by_name(result, "with_branch").line_count == 5
    assert func_by_name(result, "nested_loops").line_count == 6
    assert func_by_name(result, "async_fn").line_count == 2


def test_function_start_lines():
    result = analyze_fixture()
    assert func_by_name(result, "simple").start_line == 9
    assert func_by_name(result, "with_branch").start_line == 14
    assert func_by_name(result, "nested_loops").start_line == 21
    assert func_by_name(result, "__init__").start_line == 30
    assert func_by_name(result, "compute").start_line == 34
    assert func_by_name(result, "async_fn").start_line == 40


# ---------------------------------------------------------------------------
# Argument counts (self/cls excluded)
# ---------------------------------------------------------------------------


def test_arg_counts():
    result = analyze_fixture()
    assert func_by_name(result, "simple").arg_count == 2         # x, y
    assert func_by_name(result, "with_branch").arg_count == 1    # value
    assert func_by_name(result, "__init__").arg_count == 2       # a, b (self excluded)
    assert func_by_name(result, "compute").arg_count == 1        # x (self excluded)
    assert func_by_name(result, "async_fn").arg_count == 1       # key (kwonly)


# ---------------------------------------------------------------------------
# Nesting depth
# ---------------------------------------------------------------------------


def test_nesting_depths():
    result = analyze_fixture()
    assert func_by_name(result, "simple").max_nesting_depth == 0
    assert func_by_name(result, "with_branch").max_nesting_depth == 1
    assert func_by_name(result, "nested_loops").max_nesting_depth == 2
    assert func_by_name(result, "compute").max_nesting_depth == 1


# ---------------------------------------------------------------------------
# Class metrics
# ---------------------------------------------------------------------------


def test_collects_class():
    result = analyze_fixture()
    assert result.metrics.class_count == 1
    cls = result.metrics.classes[0]
    assert cls.name == "MyClass"
    assert cls.method_count == 2
    assert cls.start_line == 29
    assert cls.line_count == 9  # lines 29–37


# ---------------------------------------------------------------------------
# File-level metrics
# ---------------------------------------------------------------------------


def test_function_count():
    result = analyze_fixture()
    assert result.metrics.function_count == 6


def test_import_count():
    result = analyze_fixture()
    assert result.metrics.import_count == 3  # os, sys, Path


def test_language():
    result = analyze_fixture()
    assert result.language == "python"


def test_no_issues_on_valid_file():
    result = analyze_fixture()
    assert result.issues == []


# ---------------------------------------------------------------------------
# Syntax error handling
# ---------------------------------------------------------------------------


def test_syntax_error_emits_error_issue():
    bad_source = "def broken(\n    pass\n"
    result = ANALYZER.analyze(Path("bad.py"), bad_source)
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity == Severity.ERROR
    assert issue.rule_id == "python.syntax-error"


def test_syntax_error_returns_empty_metrics():
    bad_source = "def broken(\n    pass\n"
    result = ANALYZER.analyze(Path("bad.py"), bad_source)
    assert result.metrics.function_count == 0
    assert result.metrics.class_count == 0


def test_syntax_error_does_not_set_skipped():
    """Partial result — file is not skipped, it has an error issue."""
    bad_source = "def broken(\n    pass\n"
    result = ANALYZER.analyze(Path("bad.py"), bad_source)
    assert not result.skipped
