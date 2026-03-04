"""Tests for autopsy.config.load_config."""
from pathlib import Path

from autopsy.config import Config, load_config


def _write_toml(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# No config file — pure defaults
# ---------------------------------------------------------------------------


def test_defaults_when_no_file(tmp_path: Path) -> None:
    config = load_config(tmp_path / "nonexistent.toml")
    assert isinstance(config, Config)
    assert config.thresholds.max_function_lines == 50
    assert config.thresholds.max_cyclomatic_complexity == 10
    assert config.thresholds.max_cognitive_complexity == 15
    assert config.thresholds.max_parameters == 5
    assert config.thresholds.max_nesting_depth == 4
    assert config.scoring.error_weight == 10.0
    assert config.scoring.warning_weight == 3.0
    assert config.scoring.info_weight == 1.0
    assert config.ci.fail_on_score is None
    assert config.ignore.patterns == []


# ---------------------------------------------------------------------------
# Single field overrides; rest stays default
# ---------------------------------------------------------------------------


def test_override_one_threshold(tmp_path: Path) -> None:
    toml = tmp_path / ".autopsy.toml"
    _write_toml(toml, "[thresholds]\nmax_function_lines = 100\n")
    config = load_config(toml)
    assert config.thresholds.max_function_lines == 100
    # All other thresholds remain default
    assert config.thresholds.max_cyclomatic_complexity == 10
    assert config.thresholds.max_parameters == 5


def test_override_scoring_weight(tmp_path: Path) -> None:
    toml = tmp_path / ".autopsy.toml"
    _write_toml(toml, "[scoring]\nerror_weight = 20.0\n")
    config = load_config(toml)
    assert config.scoring.error_weight == 20.0
    assert config.scoring.warning_weight == 3.0  # default unchanged
    assert config.scoring.info_weight == 1.0


def test_override_ci_fail_on_score(tmp_path: Path) -> None:
    toml = tmp_path / ".autopsy.toml"
    _write_toml(toml, "[ci]\nfail_on_score = 70\n")
    config = load_config(toml)
    assert config.ci.fail_on_score == 70.0


def test_override_ignore_patterns(tmp_path: Path) -> None:
    toml = tmp_path / ".autopsy.toml"
    _write_toml(toml, '[ignore]\npatterns = ["**/migrations/*", "**/*.generated.py"]\n')
    config = load_config(toml)
    assert config.ignore.patterns == ["**/migrations/*", "**/*.generated.py"]


# ---------------------------------------------------------------------------
# Full config file
# ---------------------------------------------------------------------------


def test_full_config(tmp_path: Path) -> None:
    toml = tmp_path / ".autopsy.toml"
    _write_toml(
        toml,
        """\
[thresholds]
max_function_lines = 40
max_cyclomatic_complexity = 8
max_cognitive_complexity = 12
max_parameters = 4
max_nesting_depth = 3

[scoring]
error_weight = 15.0
warning_weight = 5.0
info_weight = 0.5

[ci]
fail_on_score = 60

[ignore]
patterns = ["**/vendor/*"]
""",
    )
    config = load_config(toml)
    assert config.thresholds.max_function_lines == 40
    assert config.thresholds.max_cyclomatic_complexity == 8
    assert config.thresholds.max_nesting_depth == 3
    assert config.scoring.error_weight == 15.0
    assert config.scoring.info_weight == 0.5
    assert config.ci.fail_on_score == 60.0
    assert config.ignore.patterns == ["**/vendor/*"]


# ---------------------------------------------------------------------------
# Empty config file — all defaults
# ---------------------------------------------------------------------------


def test_empty_toml_uses_defaults(tmp_path: Path) -> None:
    toml = tmp_path / ".autopsy.toml"
    _write_toml(toml, "")
    config = load_config(toml)
    assert config.thresholds.max_function_lines == 50
    assert config.ci.fail_on_score is None
