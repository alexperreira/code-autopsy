# Implementation Plan — code-autopsy

Tracks the concrete tasks for each milestone from SCOPE.md. Milestones are roughly one week each;
adjust as you go. Tasks are ordered by dependency—don't skip ahead.

---

## Week 1: Foundation

Goal: runnable CLI that scans a directory and prints a file list. No analysis yet.

### Project Setup
- [x] `uv init` with `pyproject.toml` — package name `autopsy`, entry point `autopsy.cli:app`
- [x] Add dependencies: `typer`, `rich`, `pathspec`, `jinja2`, `tomli` (conditional on Python <3.11)
- [x] Add dev dependencies: `pytest`, `pytest-cov`, `ruff`
- [x] Configure `ruff` in `pyproject.toml` (line length 100, select E/W/F/I)
- [x] Create `src/autopsy/__init__.py` with `__version__ = "0.1.0"`

### CLI Skeleton (`src/autopsy/cli.py`)
- [ ] `app = typer.Typer()` with `scan` command
- [ ] `scan` accepts `path: Path` argument + `--config` option (default `.autopsy.toml`)
- [ ] Print version header with `rich`
- [ ] On invocation, print "Scanning <path>..." and exit cleanly
- [ ] Wire entry point so `autopsy scan .` works after `uv run`

### File Scanner (`src/autopsy/scanner.py`)
- [ ] `scan_files(root: Path, config: Config) -> Iterator[Path]`
- [ ] Recursively walk with `os.walk` or `pathlib.rglob`
- [ ] Skip hidden dirs (`.git`, `.venv`, `node_modules`, `__pycache__`) by default
- [ ] Load `.gitignore` at root using `pathspec.PathSpec.from_lines("gitwildmatch", ...)`
- [ ] Apply additional ignore patterns from config (`[ignore] patterns`)
- [ ] Filter by extension—initially only `.py`
- [ ] Unit test: fixture dir with a nested `.gitignore`, assert ignored files absent

### Config Loader (`src/autopsy/config.py`)
- [ ] `Config` dataclass (or attrs) with fields matching `.autopsy.toml` schema from SCOPE.md
- [ ] `load_config(path: Path) -> Config` — reads TOML if present, falls back to defaults
- [ ] Defaults hardcoded as class-level values; no config file required to run
- [ ] Unit test: load a minimal toml, override one field, assert rest is default

### Data Models (`src/autopsy/models.py`)
- [ ] Define shared types used by all layers (see ARCHITECTURE.md for full spec):
  - `Severity` enum: `INFO`, `WARNING`, `ERROR`
  - `Issue` dataclass: `rule_id, severity, message, file, line, col`
  - `FunctionMetrics` dataclass: raw extracted metrics per function
  - `FileResult` dataclass: `path, issues, metrics, debt_score`
  - `RepoResult` dataclass: `files, aggregate_score, run_timestamp`

---

## Week 2: Complexity Analysis

Goal: extract cyclomatic + cognitive complexity for every function and flag overruns.

### AST Analyzer Base (`src/autopsy/analyzers/base.py`)
- [ ] `BaseAnalyzer` ABC with method `analyze(path: Path, source: str) -> FileResult`
- [ ] Defines the contract; no logic here

### Python Analyzer (`src/autopsy/analyzers/python.py`)
- [ ] `PythonAnalyzer(BaseAnalyzer)` — reads source, parses with `ast.parse`
- [ ] `FunctionVisitor(ast.NodeVisitor)` that walks the AST and extracts:
  - Function/method name, start line, end line → line count
  - Argument count
  - Nesting depth (tracked via visitor state)
- [ ] Handle `ast.parse` errors gracefully: emit one `ERROR`-severity issue, return partial result
- [ ] Unit test: parse a fixture file, assert correct function names and line counts

### Cyclomatic Complexity (`src/autopsy/rules/complexity.py`)
- [ ] `cyclomatic_complexity(func_node: ast.FunctionDef) -> int`
- [ ] Count decision points: `If`, `While`, `For`, `ExceptHandler`, `With`, `Assert`,
  boolean ops (`And`, `Or`), `comprehension` (each `if`), `match` arms
- [ ] Base = 1, add 1 per decision point
- [ ] `CyclomaticComplexityRule` class: compares against `config.max_cyclomatic_complexity`,
  emits `WARNING` (≥threshold) or `ERROR` (≥2×threshold)
- [ ] Unit test: known functions with expected CC values

### Cognitive Complexity (`src/autopsy/rules/complexity.py`)
- [ ] `cognitive_complexity(func_node: ast.FunctionDef) -> int`
- [ ] Scoring: +1 per nesting increment, +1 per structural break (`break`, `continue`,
  `goto`-style early returns), +1 for boolean sequence chains, add nesting level for
  nested control structures
- [ ] Reference: Cognitive Complexity whitepaper (SonarSource)
- [ ] `CognitiveComplexityRule` class with threshold from config
- [ ] Unit test: known examples with expected scores

### Per-file Aggregation
- [ ] `PythonAnalyzer.analyze()` runs all complexity rules for each function,
  collects issues into `FileResult`
- [ ] `FileResult.metrics` stores max/avg CC and cognitive complexity at file level
- [ ] CLI `scan` command prints a simple table: file, function count, max CC (no scoring yet)

---

## Week 3: Smell Detection

Goal: implement all smell rules from SCOPE.md. Rules are composable and independently testable.

### Rule Architecture (`src/autopsy/rules/base.py`)
- [ ] `BaseRule` ABC: `rule_id: str`, `check(func: FunctionMetrics, ...) -> list[Issue]`
- [ ] `RuleRegistry`: dict mapping `rule_id → BaseRule`; rules register themselves
- [ ] `RuleSet`: ordered list of rules to run; constructed from config (all enabled by default)

### Long Functions (`src/autopsy/rules/smells.py`)
- [ ] `LongFunctionRule`: `line_count > config.max_function_lines` → `WARNING`;
  `> 2×` → `ERROR`
- [ ] Message includes actual count and threshold

### Deep Nesting (`src/autopsy/rules/smells.py`)
- [ ] `DeepNestingRule`: max nesting depth > `config.max_nesting_depth`
- [ ] Depth tracked during AST walk (each `if/for/while/with/try` increments depth)
- [ ] Report the deepest nesting line number

### Too Many Parameters (`src/autopsy/rules/smells.py`)
- [ ] `TooManyParamsRule`: `arg_count > config.max_parameters`
- [ ] Exclude `self`/`cls` from count

### God Classes (`src/autopsy/rules/smells.py`)
- [ ] `GodClassRule`: fires on `ast.ClassDef` nodes (not functions)
- [ ] Triggers if: `method_count > 10` OR `class_line_count > 300`
- [ ] Reports both violations if both exceed thresholds

### Unused Imports (`src/autopsy/rules/smells.py`)
- [ ] `UnusedImportRule`: collect all `import` / `from X import Y` names,
  then check if name appears in any `ast.Name` node in the module
- [ ] Severity `INFO` (dead code hint, not definitive)
- [ ] Note in message: "may be unused (dynamic use not detected)"

### Duplicate Code (basic) (`src/autopsy/rules/smells.py`)
- [ ] `DuplicateBlockRule`: extract 5-line windows of normalized source lines
  (strip whitespace, comments), hash each window, flag files where same hash
  appears ≥3 times OR same hash appears in two different files
- [ ] Severity `WARNING`; this is intentionally basic (no token-level analysis)
- [ ] Disable by default in config (`enabled = false` flag per rule)

### Rule Integration
- [ ] `PythonAnalyzer` runs `RuleSet` rules after metric extraction
- [ ] All issues funneled into `FileResult.issues`
- [ ] CLI table updated to show issue count per severity per file

---

## Week 4: Scoring & Reporting

Goal: debt score visible in terminal; JSON and HTML exports work end-to-end.

### Debt Scorer (`src/autopsy/scoring.py`)
- [ ] `score_file(result: FileResult, config: Config) -> float` — see SCORING-DESIGN.md
- [ ] `score_repo(results: list[FileResult], config: Config) -> float`
- [ ] Attach scores to `FileResult.debt_score` and `RepoResult.aggregate_score`
- [ ] Unit tests: known issue lists produce expected scores; capped at 100

### Terminal Reporter (`src/autopsy/reporters/terminal.py`)
- [ ] `TerminalReporter.render(repo: RepoResult) -> None`
- [ ] Summary table: file | score | top issue (matches example in SCOPE.md)
- [ ] Color-coded score: green ≤20, yellow ≤50, orange ≤75, red >75
- [ ] Footer: overall score, grade label (Clean / Moderate / High Risk / Critical)
- [ ] Top 3 recommendations (highest-debt files with actionable description)
- [ ] Progress bar during scan via `rich.progress`

### JSON Reporter (`src/autopsy/reporters/json_report.py`)
- [ ] `JsonReporter.write(repo: RepoResult, path: Path) -> None`
- [ ] Serialize full `RepoResult` to JSON (use `dataclasses.asdict` + custom encoder for `Path`/`Severity`)
- [ ] Schema documented inline (keys stable for CI consumption)
- [ ] `run_timestamp` in ISO 8601 UTC

### HTML Reporter (`src/autopsy/reporters/html_report.py`)
- [ ] `HtmlReporter.write(repo: RepoResult, path: Path) -> None`
- [ ] Render `src/autopsy/templates/report.html` with Jinja2
- [ ] Template sections: header (score badge), file table (sortable via JS `<script>` inline),
  per-file issue breakdown (collapsible), recommendations
- [ ] Self-contained HTML (no CDN dependencies; inline minimal CSS + JS)

### CLI Integration
- [ ] `scan` command accepts `--output-json <path>` and `--output-html <path>` flags
- [ ] Default: terminal output always; JSON/HTML only if flag given
- [ ] `--quiet` flag: suppress terminal table, only print final score (for CI pipelines)

---

## Week 5: Polish & CI

Goal: production-ready CLI with threshold-based exit codes and trend comparison.

### Exit Codes
- [ ] `--fail-on <score>`: exit code `1` if `aggregate_score >= fail_on`
- [ ] Default no failure (exit `0`) unless flag provided
- [ ] Document exit codes in `--help` output

### Historical Comparison
- [ ] On each run, write/update `.autopsy-cache.json` in project root (or `--cache-dir`)
- [ ] Cache stores: `{run_timestamp, aggregate_score, per_file_scores}`
- [ ] On next run, if cache exists, print delta: `▲ +3.2` or `▼ -5.1` next to scores
- [ ] `--no-cache` flag to skip read/write

### Configurable Thresholds
- [ ] All thresholds from `.autopsy.toml` wired through; verify defaults match SCOPE.md
- [ ] `--max-complexity <n>` CLI override (takes precedence over config file)
- [ ] `autopsy config show` subcommand: prints active config as TOML

### Error Handling & Edge Cases
- [ ] Files with syntax errors: emit one `ERROR` issue, continue scanning
- [ ] Empty files: skip (no issues, no score contribution)
- [ ] Binary files accidentally matched: catch `UnicodeDecodeError`, skip
- [ ] Unreadable files: emit warning to stderr, continue

### Progress & Performance
- [ ] `rich.progress` live bar during scan with file count / elapsed time
- [ ] Warn if repo >10k files (suggest adding ignore patterns)
- [ ] Streaming analysis: process one file at a time, don't buffer all ASTs in memory

### Testing Hardening
- [ ] Integration test: run `autopsy scan tests/fixtures/sample_repo` end-to-end,
  assert JSON output matches expected schema
- [ ] Test CI mode: `--fail-on 50` with a high-debt fixture exits with code 1
- [ ] Coverage target: ≥80% on core modules (`scanner`, `analyzers`, `rules`, `scoring`)

---

## Week 6: Stretch Goals

Only if Weeks 1–5 are solid. Don't start these at the expense of polish.

### JavaScript/TypeScript Support
- [ ] Add `tree-sitter` + `tree-sitter-javascript` to optional deps (`[project.optional-dependencies] js`)
- [ ] `JavaScriptAnalyzer(BaseAnalyzer)` in `src/autopsy/analyzers/javascript.py`
- [ ] Re-use existing rule thresholds where semantically equivalent
- [ ] `scanner.py` filter by `.js`, `.ts`, `.jsx`, `.tsx` when JS analyzer present

### SARIF Output
- [ ] `SarifReporter.write(repo: RepoResult, path: Path) -> None`
- [ ] SARIF 2.1.0 schema; each `Issue` → `result` with `locations[].physicalLocation`
- [ ] `--output-sarif <path>` CLI flag
- [ ] Enables GitHub Advanced Security code scanning upload

### PyPI Release
- [ ] Finalize `pyproject.toml` classifiers, description, homepage
- [ ] `CHANGELOG.md` with v0.1.0 entry
- [ ] GitHub Actions workflow: test on push, publish to PyPI on tag
- [ ] Demo GIF in README (using `vhs` or `asciinema`)

---

## Cross-Cutting Concerns (all weeks)

- **Logging**: use `logging` module (not `print`); default level `WARNING`; `--verbose` sets `DEBUG`
- **Type hints**: all public functions fully annotated; run `mypy` in CI
- **Docs**: update `CLAUDE.md` Repo Quickstart section once commands are stable
- **Fixtures**: `tests/fixtures/` contains curated Python files with known issue counts
  (add one fixture per new rule to prevent regressions)
