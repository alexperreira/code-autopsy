# code-autopsy

## Project Overview
Automated codebase analysis and technical debt scoring. Scans repositories, identifies code smells, complexity hotspots, and maintenance risks—then generates actionable reports with prioritized recommendations.

**Tagline:** "It tells you what you already know but refuse to acknowledge."

## Tech Stack
- **Core:** Python (AST parsing, analysis engine, CLI)
- **Analysis:** Built-in AST module + custom heuristics (ML scoring deferred post-MVP)
- **Output:** Terminal (rich tables), JSON, HTML reports
- **Supported Languages (MVP):** Python first, JavaScript/TypeScript stretch goal

## MVP Scope (4-6 weeks)

### Core Features (Must Have)
1. **Codebase Scanning**
   - Recursively scan directory for source files
   - Respect .gitignore patterns
   - Handle large repos efficiently (streaming, not loading all into memory)

2. **Complexity Analysis**
   - Cyclomatic complexity per function/method
   - Cognitive complexity (nesting depth, boolean chains)
   - Function/file length metrics
   - Flag functions exceeding thresholds

3. **Code Smell Detection**
   - Long functions (>50 lines configurable)
   - Deep nesting (>4 levels)
   - Too many parameters (>5)
   - God classes (classes with >10 methods or >300 lines)
   - Duplicate/similar code blocks (basic detection)
   - Dead code hints (unused imports, unreachable branches)

4. **Technical Debt Scoring**
   - Per-file debt score (0-100, higher = worse)
   - Aggregate repo score
   - Weighted formula based on severity and prevalence
   - Trend tracking (compare against previous runs via JSON cache)

5. **Reporting**
   - CLI output with color-coded severity
   - JSON export for CI integration
   - HTML report with sortable tables and charts

6. **CI-Friendly**
   - Exit codes based on thresholds (fail build if score > X)
   - SARIF output for GitHub code scanning integration (stretch)

### Non-Goals for MVP
- No ML-based predictions (heuristics only)
- No multi-language support beyond Python (JS is stretch)
- No IDE plugins
- No real-time / watch mode
- No git blame integration (who introduced debt)
- No auto-fix suggestions

## Architecture Sketch
```
┌─────────────────────────────────────────┐
│                  CLI                     │
│  (click or typer, handles args/config)   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│            Analysis Engine               │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ File Walker │  │  AST Analyzer    │  │
│  │ (.gitignore)│  │  (per-language)  │  │
│  └─────────────┘  └──────────────────┘  │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ Smell Rules │  │  Debt Scorer     │  │
│  │ (pluggable) │  │  (weighted calc) │  │
│  └─────────────┘  └──────────────────┘  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│             Reporters                    │
│  Terminal │ JSON │ HTML │ SARIF         │
└─────────────────────────────────────────┘
```

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CLI framework | `typer` | Modern, type-hinted, auto-generates help |
| AST parsing (Python) | Built-in `ast` module | No dependencies, full fidelity |
| AST parsing (JS/TS) | `tree-sitter` with `py-tree-sitter` | Fast, multi-language, incremental |
| Complexity calculation | Custom visitor pattern | Full control, easy to extend |
| Terminal output | `rich` | Beautiful tables, progress bars, colors |
| HTML reports | Jinja2 templates | Simple, flexible, no JS framework needed |
| Config format | `pyproject.toml` or `.autopsy.toml` | Standard, no new config format to learn |

## File Structure (Suggested)
```
code-autopsy/
├── src/
│   └── autopsy/
│       ├── __init__.py
│       ├── cli.py              # Typer CLI entry point
│       ├── scanner.py          # File discovery, .gitignore handling
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract analyzer interface
│       │   ├── python.py       # Python AST analyzer
│       │   └── javascript.py   # JS/TS analyzer (stretch)
│       ├── rules/
│       │   ├── __init__.py
│       │   ├── complexity.py   # Cyclomatic, cognitive complexity
│       │   ├── smells.py       # Code smell detectors
│       │   └── metrics.py      # Length, count metrics
│       ├── scoring.py          # Debt score calculation
│       ├── reporters/
│       │   ├── __init__.py
│       │   ├── terminal.py     # Rich console output
│       │   ├── json_report.py  # JSON export
│       │   └── html_report.py  # HTML generation
│       └── templates/
│           └── report.html     # Jinja2 HTML template
├── tests/
│   ├── fixtures/               # Sample codebases for testing
│   ├── test_scanner.py
│   ├── test_analyzers.py
│   └── test_scoring.py
├── pyproject.toml
└── README.md
```

## Milestones

### Week 1: Foundation
- [ ] Project setup (pyproject.toml, typer CLI skeleton)
- [ ] File scanner with .gitignore support
- [ ] Basic Python AST visitor that walks all functions/classes
- [ ] Extract raw metrics: line counts, function counts

### Week 2: Complexity Analysis
- [ ] Cyclomatic complexity calculation
- [ ] Cognitive complexity calculation
- [ ] Per-function and per-file aggregation
- [ ] Threshold configuration

### Week 3: Smell Detection
- [ ] Implement smell rules (long functions, deep nesting, god classes, etc.)
- [ ] Rule severity levels (info, warning, error)
- [ ] Pluggable rule architecture (easy to add new rules)

### Week 4: Scoring & Reporting
- [ ] Debt scoring formula (weighted by severity/prevalence)
- [ ] Terminal reporter with rich tables
- [ ] JSON export
- [ ] Basic HTML report with summary + file breakdown

### Week 5: Polish & CI
- [ ] Configurable thresholds via .autopsy.toml
- [ ] Exit codes for CI (--fail-on flag)
- [ ] Historical comparison (diff against previous JSON)
- [ ] Progress bar for large repos

### Week 6: Stretch & Release
- [ ] JavaScript/TypeScript support via tree-sitter (if time)
- [ ] SARIF output for GitHub integration (if time)
- [ ] README, demo GIF, PyPI release

## Scoring Formula (Draft)
```python
# Per-file debt score (0-100)
def calculate_file_score(issues: list[Issue]) -> float:
    weights = {
        "error": 10,
        "warning": 3,
        "info": 1
    }
    raw_score = sum(weights[issue.severity] for issue in issues)
    # Normalize to 0-100, cap at 100
    return min(100, raw_score)

# Repo score = weighted average by file size (larger files matter more)
```

## Example Output
```bash
$ autopsy scan ./my-project

  code-autopsy v0.1.0
  Scanning ./my-project...

  ┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ File                   ┃ Score ┃ Top Issues                ┃
  ┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
  │ src/utils/helpers.py   │  78   │ 🔴 God class (412 lines)  │
  │ src/api/handlers.py    │  62   │ 🟠 Cyclomatic: 23         │
  │ src/models/user.py     │  15   │ 🟡 Long function (67 ln)  │
  │ src/main.py            │   4   │ ✅ Minor issues only      │
  └────────────────────────┴───────┴───────────────────────────┘

  ──────────────────────────────────────────────────────────────
  Overall Debt Score: 41/100 (Moderate)

  Recommendations:
  1. Refactor helpers.py - split into focused modules
  2. Reduce complexity in handlers.py:process_request()

  Full report: ./autopsy-report.html
```

## Configuration Example
```toml
# .autopsy.toml

[thresholds]
max_function_lines = 50
max_cyclomatic_complexity = 10
max_cognitive_complexity = 15
max_parameters = 5
max_nesting_depth = 4

[scoring]
error_weight = 10
warning_weight = 3
info_weight = 1

[ci]
fail_on_score = 70  # Exit code 1 if repo score >= 70

[ignore]
patterns = ["**/migrations/*", "**/vendor/*", "**/*.generated.py"]
```

## Dependencies
```toml
[project]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pathspec>=0.11.0",      # .gitignore parsing
    "jinja2>=3.1.0",
    "tomli>=2.0.0",          # TOML parsing (Python <3.11)
]

[project.optional-dependencies]
js = ["tree-sitter>=0.20.0", "tree-sitter-javascript>=0.20.0"]
```

## Open Questions (Decide During Build)
1. Should duplicate detection be token-based or AST-based?
2. How to handle dynamically generated code (exec, eval)?
3. Include test files in analysis or separate scoring?
4. Monorepo support—per-package scoring?

## Getting Started (For Claude Code)

1. Initialize: `mkdir code-autopsy && cd code-autopsy`
2. Setup: `uv init` or `poetry init` (pyproject.toml)
3. Start with scanner.py (file walking + .gitignore)
4. Build Python AST analyzer with basic metrics
5. Add rules incrementally (one smell at a time)
6. Terminal reporter last (needs data to display)

Ship the simplest version that produces useful output. Fancy reports come after the analysis is solid.
