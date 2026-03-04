"""Tests for autopsy.scanner.scan_files."""
from pathlib import Path

import pytest

from autopsy.config import Config, IgnoreConfig
from autopsy.scanner import scan_files


def _write(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def collected(root: Path, config: Config | None = None) -> set[Path]:
    return set(scan_files(root, config or Config()))


# ---------------------------------------------------------------------------
# Basic walk
# ---------------------------------------------------------------------------


def test_finds_python_files(tmp_path: Path) -> None:
    _write(tmp_path / "a.py")
    _write(tmp_path / "sub" / "b.py")
    result = collected(tmp_path)
    assert result == {
        (tmp_path / "a.py").resolve(),
        (tmp_path / "sub" / "b.py").resolve(),
    }


def test_ignores_non_python_files(tmp_path: Path) -> None:
    _write(tmp_path / "main.py")
    _write(tmp_path / "notes.txt")
    _write(tmp_path / "data.json")
    result = collected(tmp_path)
    assert result == {(tmp_path / "main.py").resolve()}


# ---------------------------------------------------------------------------
# Always-skip directories
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "skip_dir",
    ["__pycache__", ".git", ".venv", "venv", "node_modules", "dist", "build"],
)
def test_always_skip_dirs(tmp_path: Path, skip_dir: str) -> None:
    _write(tmp_path / skip_dir / "hidden.py")
    _write(tmp_path / "visible.py")
    result = collected(tmp_path)
    assert result == {(tmp_path / "visible.py").resolve()}


# ---------------------------------------------------------------------------
# Root .gitignore
# ---------------------------------------------------------------------------


def test_root_gitignore_excludes_file(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "ignored.py\n")
    _write(tmp_path / "ignored.py")
    _write(tmp_path / "kept.py")
    result = collected(tmp_path)
    assert (tmp_path / "kept.py").resolve() in result
    assert (tmp_path / "ignored.py").resolve() not in result


def test_root_gitignore_glob_pattern(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "*.generated.py\n")
    _write(tmp_path / "api.generated.py")
    _write(tmp_path / "api.py")
    result = collected(tmp_path)
    assert (tmp_path / "api.py").resolve() in result
    assert (tmp_path / "api.generated.py").resolve() not in result


def test_root_gitignore_excludes_directory(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "migrations/\n")
    _write(tmp_path / "migrations" / "0001_initial.py")
    _write(tmp_path / "app.py")
    result = collected(tmp_path)
    assert (tmp_path / "app.py").resolve() in result
    assert not any("migrations" in str(p) for p in result)


# ---------------------------------------------------------------------------
# Nested .gitignore
# ---------------------------------------------------------------------------


def test_nested_gitignore_excludes_file(tmp_path: Path) -> None:
    """A .gitignore inside a subdirectory should exclude files within that subdir."""
    sub = tmp_path / "sub"
    _write(sub / ".gitignore", "secret.py\n")
    _write(sub / "secret.py")
    _write(sub / "public.py")
    _write(tmp_path / "top.py")

    result = collected(tmp_path)
    assert (tmp_path / "top.py").resolve() in result
    assert (sub / "public.py").resolve() in result
    assert (sub / "secret.py").resolve() not in result


def test_nested_gitignore_does_not_affect_parent(tmp_path: Path) -> None:
    """A nested .gitignore must not exclude same-named files in the parent."""
    sub = tmp_path / "sub"
    _write(sub / ".gitignore", "utils.py\n")
    _write(sub / "utils.py")
    _write(tmp_path / "utils.py")  # should NOT be excluded

    result = collected(tmp_path)
    assert (tmp_path / "utils.py").resolve() in result
    assert (sub / "utils.py").resolve() not in result


# ---------------------------------------------------------------------------
# Config ignore patterns
# ---------------------------------------------------------------------------


def test_config_patterns_exclude_file(tmp_path: Path) -> None:
    config = Config(ignore=IgnoreConfig(patterns=["**/vendor/*"]))
    _write(tmp_path / "vendor" / "third_party.py")
    _write(tmp_path / "app.py")
    result = collected(tmp_path, config)
    assert (tmp_path / "app.py").resolve() in result
    assert not any("vendor" in str(p) for p in result)


def test_config_patterns_override_without_gitignore(tmp_path: Path) -> None:
    config = Config(ignore=IgnoreConfig(patterns=["skip_me.py"]))
    _write(tmp_path / "skip_me.py")
    _write(tmp_path / "keep_me.py")
    result = collected(tmp_path, config)
    assert {(tmp_path / "keep_me.py").resolve()} == result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_directory(tmp_path: Path) -> None:
    assert collected(tmp_path) == set()


def test_no_python_files(tmp_path: Path) -> None:
    _write(tmp_path / "README.md")
    _write(tmp_path / "config.yml")
    assert collected(tmp_path) == set()


def test_returns_absolute_paths(tmp_path: Path) -> None:
    _write(tmp_path / "a.py")
    for path in scan_files(tmp_path, Config()):
        assert path.is_absolute()
