# Architecture — code-autopsy

Reference for module boundaries, data models, and component contracts.
This is the source of truth for interfaces; IMPLEMENTATION-PLAN.md describes *when* to build them.

---

## Layer Overview

```
CLI (typer)
  │  parses args, loads config, orchestrates layers
  ▼
Scanner
  │  yields Path objects; applies .gitignore + custom ignores
  ▼
Analyzer (per language)
  │  parses source, runs metric extraction + rule checks
  │  returns FileResult per file
  ▼
Scorer
  │  assigns debt_score to each FileResult; computes aggregate
  ▼
Reporters (terminal | JSON | HTML | SARIF)
     consume RepoResult, write output
```

No layer reaches "up" — reporters don't call analyzers, analyzers don't know about reporters.
Config is passed down; no global state.

---

## Data Models (`src/autopsy/models.py`)

These are the shared types that cross layer boundaries.

```python
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

class Severity(Enum):
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"

@dataclass
class Issue:
    rule_id:  str
    severity: Severity
    message:  str
    file:     Path
    line:     int
    col:      int = 0

@dataclass
class FunctionMetrics:
    name:              str
    start_line:        int
    end_line:          int
    line_count:        int
    arg_count:         int          # excludes self/cls
    max_nesting_depth: int
    cyclomatic:        int
    cognitive:         int

@dataclass
class ClassMetrics:
    name:         str
    start_line:   int
    end_line:     int
    line_count:   int
    method_count: int

@dataclass
class FileMetrics:
    total_lines:      int
    function_count:   int
    class_count:      int
    import_count:     int
    max_cyclomatic:   int           # worst function in file
    avg_cyclomatic:   float
    max_cognitive:    int
    functions:        list[FunctionMetrics] = field(default_factory=list)
    classes:          list[ClassMetrics]    = field(default_factory=list)

@dataclass
class FileResult:
    path:       Path
    language:   str                 # "python", "javascript"
    metrics:    FileMetrics
    issues:     list[Issue]         = field(default_factory=list)
    debt_score: float               = 0.0
    skipped:    bool                = False
    skip_reason: str                = ""

@dataclass
class RepoResult:
    root:            Path
    files:           list[FileResult]
    aggregate_score: float
    run_timestamp:   datetime
    previous_score:  float | None   = None  # from cache, if available
```

**Invariants:**
- `Issue.file` is always an absolute path
- `FileResult.debt_score` is in [0.0, 100.0]
- `RepoResult.aggregate_score` is in [0.0, 100.0]
- `skipped=True` files have no `issues` and contribute `0.0` to aggregate score

---

## Config (`src/autopsy/config.py`)

```python
@dataclass
class ThresholdConfig:
    max_function_lines:       int   = 50
    max_cyclomatic_complexity: int  = 10
    max_cognitive_complexity:  int  = 15
    max_parameters:           int   = 5
    max_nesting_depth:        int   = 4
    min_duplicate_window:     int   = 5     # lines for duplicate detection
    min_duplicate_occurrences: int  = 3     # times a block must repeat to flag

@dataclass
class ScoringConfig:
    error_weight:   float = 10.0
    warning_weight: float = 3.0
    info_weight:    float = 1.0

@dataclass
class CiConfig:
    fail_on_score: float | None = None

@dataclass
class IgnoreConfig:
    patterns: list[str] = field(default_factory=list)

@dataclass
class Config:
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    scoring:    ScoringConfig   = field(default_factory=ScoringConfig)
    ci:         CiConfig        = field(default_factory=CiConfig)
    ignore:     IgnoreConfig    = field(default_factory=IgnoreConfig)
```

`load_config(path: Path) -> Config` merges TOML values onto defaults;
missing keys in TOML silently use defaults (never error on missing optional fields).

---

## Scanner (`src/autopsy/scanner.py`)

```python
def scan_files(root: Path, config: Config) -> Iterator[Path]:
    ...
```

- Yields absolute paths to source files
- Applies `.gitignore` from `root` (and any nested `.gitignore` files)
- Applies `config.ignore.patterns` (gitignore-style globs)
- Skips: `__pycache__`, `.git`, `.venv`, `node_modules`, `dist`, `build`
- Extension filter: `.py` always; `.js/.ts/.jsx/.tsx` if JS analyzer installed

**Not scanner's job:** it does not open or parse files. That's the analyzer.

---

## Analyzers (`src/autopsy/analyzers/`)

### Interface

```python
class BaseAnalyzer(ABC):
    def __init__(self, config: Config): ...

    @abstractmethod
    def supports(self, path: Path) -> bool:
        """Return True if this analyzer handles the given file extension."""

    @abstractmethod
    def analyze(self, path: Path) -> FileResult:
        """Parse and analyze a single file. Never raises; returns skipped=True on error."""
```

### Analyzer Registry

CLI constructs a list of available analyzers. For each file from scanner:

```python
for analyzer in analyzers:
    if analyzer.supports(path):
        result = analyzer.analyze(path)
        break
```

If no analyzer matches, the file is silently skipped (shouldn't happen if scanner filters correctly).

### Python Analyzer internals

```
PythonAnalyzer.analyze(path)
  │
  ├── read source (catch UnicodeDecodeError → skipped)
  ├── ast.parse(source) (catch SyntaxError → skipped with ERROR issue)
  ├── MetricsVisitor(ast.NodeVisitor).visit(tree)
  │     builds FunctionMetrics + ClassMetrics for every function/class
  ├── run RuleSet.check(metrics, source) → list[Issue]
  └── return FileResult(path, "python", metrics, issues)
```

---

## Rules (`src/autopsy/rules/`)

### Interface

```python
class BaseRule(ABC):
    rule_id:  str     # e.g. "CC001"
    enabled:  bool = True

    @abstractmethod
    def check(
        self,
        file_metrics: FileMetrics,
        source_lines: list[str],
        config: Config,
    ) -> list[Issue]:
        ...
```

### Rule ID Namespace

| Prefix | Category |
|--------|----------|
| `CC`   | Cyclomatic complexity |
| `CG`   | Cognitive complexity |
| `SM`   | Code smell |
| `DC`   | Dead code |
| `DU`   | Duplicate code |

### Rule Table (MVP)

| Rule ID | Name | Trigger | Severity |
|---------|------|---------|---------|
| `CC001` | HighCyclomaticComplexity | cyclomatic ≥ threshold | WARNING |
| `CC002` | CriticalCyclomaticComplexity | cyclomatic ≥ 2×threshold | ERROR |
| `CG001` | HighCognitiveComplexity | cognitive ≥ threshold | WARNING |
| `CG002` | CriticalCognitiveComplexity | cognitive ≥ 2×threshold | ERROR |
| `SM001` | LongFunction | lines > max_function_lines | WARNING |
| `SM002` | VeryLongFunction | lines > 2×max_function_lines | ERROR |
| `SM003` | TooManyParameters | args > max_parameters | WARNING |
| `SM004` | DeepNesting | depth > max_nesting_depth | WARNING |
| `SM005` | GodClass | methods>10 OR lines>300 | WARNING |
| `DC001` | UnusedImport | import name not referenced | INFO |
| `DU001` | DuplicateBlock | same block ≥N times | WARNING |

### RuleSet

```python
class RuleSet:
    rules: list[BaseRule]

    def check(self, metrics: FileMetrics, source_lines: list[str], config: Config) -> list[Issue]:
        return [issue for rule in self.rules if rule.enabled
                       for issue in rule.check(metrics, source_lines, config)]
```

---

## Scorer (`src/autopsy/scoring.py`)

See SCORING-DESIGN.md for formula rationale.

```python
def score_file(result: FileResult, config: Config) -> float:
    """Returns 0.0–100.0. Higher = more debt."""
    ...

def score_repo(results: list[FileResult], config: Config) -> float:
    """Weighted average by file line count. Skipped files excluded."""
    ...
```

---

## Reporters (`src/autopsy/reporters/`)

### Interface

```python
class BaseReporter(ABC):
    @abstractmethod
    def write(self, repo: RepoResult, destination: Path | None) -> None:
        """Terminal reporter ignores destination (writes to stdout).
           File reporters write to destination."""
```

### Reporter Summary

| Reporter | Class | Output |
|----------|-------|--------|
| Terminal | `TerminalReporter` | stdout (rich) |
| JSON | `JsonReporter` | `.json` file |
| HTML | `HtmlReporter` | `.html` file |
| SARIF | `SarifReporter` | `.sarif` file (stretch) |

---

## CLI (`src/autopsy/cli.py`)

```
autopsy
├── scan <path> [options]    # main command
└── config show              # print active config
```

**scan options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--config` | Path | `.autopsy.toml` | Config file path |
| `--output-json` | Path | None | Write JSON report |
| `--output-html` | Path | None | Write HTML report |
| `--output-sarif` | Path | None | Write SARIF report (stretch) |
| `--fail-on` | float | None | Exit 1 if score ≥ value |
| `--quiet` | bool | False | Suppress table output |
| `--verbose` | bool | False | Debug logging |
| `--no-cache` | bool | False | Skip cache read/write |
| `--max-complexity` | int | None | Override config threshold |

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | Success (or score below --fail-on) |
| `1` | Score exceeded --fail-on threshold |
| `2` | Fatal error (invalid path, config parse failure) |

---

## File Layout

```
src/autopsy/
├── __init__.py          (version)
├── cli.py
├── scanner.py
├── config.py
├── models.py
├── scoring.py
├── analyzers/
│   ├── __init__.py
│   ├── base.py
│   ├── python.py
│   └── javascript.py    (stretch)
├── rules/
│   ├── __init__.py
│   ├── base.py
│   ├── complexity.py    (CC*, CG* rules)
│   ├── smells.py        (SM* rules)
│   └── dead_code.py     (DC*, DU* rules)
├── reporters/
│   ├── __init__.py
│   ├── base.py
│   ├── terminal.py
│   ├── json_report.py
│   ├── html_report.py
│   └── sarif_report.py  (stretch)
└── templates/
    └── report.html
```

---

## Dependency Flow (import rules)

- `models.py` → nothing internal
- `config.py` → nothing internal
- `rules/*` → `models`, `config`
- `analyzers/*` → `models`, `config`, `rules`
- `scoring.py` → `models`, `config`
- `reporters/*` → `models`
- `scanner.py` → `config`
- `cli.py` → everything

Circular imports are a build error. If you need to break a cycle, extract shared types to `models.py`.
