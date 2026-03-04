import os
from pathlib import Path
from typing import Iterator

import pathspec

from autopsy.config import Config

# Directories always skipped regardless of .gitignore
_ALWAYS_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)

_SOURCE_EXTENSIONS: frozenset[str] = frozenset({".py"})


def _load_gitignore(directory: Path) -> "pathspec.PathSpec | None":
    gitignore = directory / ".gitignore"
    if gitignore.is_file():
        try:
            lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
            return pathspec.PathSpec.from_lines("gitignore", lines)
        except OSError:
            pass
    return None


def scan_files(root: Path, config: Config) -> Iterator[Path]:
    """Yield absolute paths to source files under *root*, respecting .gitignore and config."""
    root = root.resolve()

    config_spec: "pathspec.PathSpec | None" = None
    if config.ignore.patterns:
        config_spec = pathspec.PathSpec.from_lines("gitignore", config.ignore.patterns)

    # Cache .gitignore specs keyed by their own directory
    gitignore_cache: dict[Path, "pathspec.PathSpec | None"] = {}

    def get_gitignore(directory: Path) -> "pathspec.PathSpec | None":
        if directory not in gitignore_cache:
            gitignore_cache[directory] = _load_gitignore(directory)
        return gitignore_cache[directory]

    def is_ignored(target: Path, is_dir: bool = False) -> bool:
        # Collect directories from root down to target's parent
        dirs: list[Path] = []
        part = target.parent if not is_dir else target.parent
        while True:
            dirs.append(part)
            if part == root:
                break
            if part == part.parent:
                # Reached filesystem root without hitting our root — shouldn't happen
                break
            part = part.parent
        dirs.reverse()  # root first

        for spec_dir in dirs:
            spec = get_gitignore(spec_dir)
            if spec is None:
                continue
            rel = target.relative_to(spec_dir)
            rel_str = str(rel)
            if is_dir:
                if spec.match_file(rel_str + "/") or spec.match_file(rel_str):
                    return True
            else:
                if spec.match_file(rel_str):
                    return True

        if config_spec is not None:
            rel_str = str(target.relative_to(root))
            if is_dir:
                if config_spec.match_file(rel_str + "/") or config_spec.match_file(rel_str):
                    return True
            else:
                if config_spec.match_file(rel_str):
                    return True

        return False

    for dirpath_str, dirnames, filenames in os.walk(root, topdown=True):
        dirpath = Path(dirpath_str)

        # Prune subdirectories in-place
        kept: list[str] = []
        for d in dirnames:
            if d in _ALWAYS_SKIP_DIRS:
                continue
            if not is_ignored(dirpath / d, is_dir=True):
                kept.append(d)
        dirnames[:] = kept

        # Yield matching source files
        for filename in filenames:
            filepath = dirpath / filename
            if filepath.suffix not in _SOURCE_EXTENSIONS:
                continue
            if not is_ignored(filepath):
                yield filepath
