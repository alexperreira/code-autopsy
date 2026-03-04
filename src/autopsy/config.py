import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class ThresholdConfig:
    max_function_lines: int = 50
    max_cyclomatic_complexity: int = 10
    max_cognitive_complexity: int = 15
    max_parameters: int = 5
    max_nesting_depth: int = 4
    min_duplicate_window: int = 5
    min_duplicate_occurrences: int = 3


@dataclass
class ScoringConfig:
    error_weight: float = 10.0
    warning_weight: float = 3.0
    info_weight: float = 1.0


@dataclass
class CiConfig:
    fail_on_score: float | None = None


@dataclass
class IgnoreConfig:
    patterns: list[str] = field(default_factory=list)


@dataclass
class Config:
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    ci: CiConfig = field(default_factory=CiConfig)
    ignore: IgnoreConfig = field(default_factory=IgnoreConfig)


def _apply_thresholds(cfg: ThresholdConfig, data: dict) -> None:
    for key in (
        "max_function_lines",
        "max_cyclomatic_complexity",
        "max_cognitive_complexity",
        "max_parameters",
        "max_nesting_depth",
        "min_duplicate_window",
        "min_duplicate_occurrences",
    ):
        if key in data:
            setattr(cfg, key, data[key])


def _apply_scoring(cfg: ScoringConfig, data: dict) -> None:
    for key in ("error_weight", "warning_weight", "info_weight"):
        if key in data:
            setattr(cfg, key, data[key])


def load_config(path: Path) -> Config:
    """Read .autopsy.toml if present; fall back to defaults for any missing fields."""
    config = Config()

    if not path.is_file():
        return config

    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    if "thresholds" in raw:
        _apply_thresholds(config.thresholds, raw["thresholds"])

    if "scoring" in raw:
        _apply_scoring(config.scoring, raw["scoring"])

    if "ci" in raw:
        ci_data = raw["ci"]
        if "fail_on_score" in ci_data:
            config.ci.fail_on_score = float(ci_data["fail_on_score"])

    if "ignore" in raw:
        ignore_data = raw["ignore"]
        if "patterns" in ignore_data:
            config.ignore.patterns = list(ignore_data["patterns"])

    return config
