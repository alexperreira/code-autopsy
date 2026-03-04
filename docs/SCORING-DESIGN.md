# Scoring Design — code-autopsy

Documents the debt scoring formula: rationale, edge cases, and normalization approach.

---

## Goals

1. A single number (0–100) that meaningfully ranks files by maintenance burden
2. Comparable across runs (stable formula = meaningful trend data)
3. Penalizes severity nonlinearly — one `ERROR` should dominate many `INFO`s
4. Resistant to gaming (adding info-level passes should not hide errors)
5. Repo score should reflect where the *actual* work is (weight by file size)

---

## Per-File Score

### Step 1: Raw Score

```python
WEIGHTS = {
    Severity.ERROR:   10.0,
    Severity.WARNING:  3.0,
    Severity.INFO:     1.0,
}

raw = sum(WEIGHTS[issue.severity] for issue in file_result.issues)
```

A file with:
- 2 ERRORs → raw = 20
- 1 ERROR + 3 WARNINGs → raw = 10 + 9 = 19
- 10 WARNINGs → raw = 30
- 5 INFOs → raw = 5

### Step 2: Normalize to 0–100

Raw scores are unbounded; we normalize with a soft cap.

```python
NORMALIZATION_CEILING = 50.0  # raw score that maps to 100

score = min(100.0, (raw / NORMALIZATION_CEILING) * 100)
```

This means:
- raw ≥ 50 → score = 100 (Critical)
- raw 25 → score = 50 (High)
- raw 10 → score = 20 (Moderate)
- raw 0  → score = 0  (Clean)

**Rationale for ceiling = 50:** A file with 5 ERRORs (raw=50) is effectively unreviewable
and warrants an immediate full-debt signal. Adjust via config if needed.

### Step 3: Config Override

Weights and ceiling are configurable via `[scoring]` in `.autopsy.toml`:

```toml
[scoring]
error_weight   = 10
warning_weight = 3
info_weight    = 1
normalization_ceiling = 50
```

---

## Repo (Aggregate) Score

Weighted average across all non-skipped files, weighted by file line count.
Larger files exert more influence because they represent more maintenance surface.

```python
def score_repo(results: list[FileResult], config: Config) -> float:
    active = [r for r in results if not r.skipped]
    if not active:
        return 0.0

    total_lines = sum(r.metrics.total_lines for r in active)
    if total_lines == 0:
        return 0.0

    weighted_sum = sum(
        r.debt_score * r.metrics.total_lines
        for r in active
    )
    return weighted_sum / total_lines
```

**Why not simple average?** A 500-line god-class file scoring 90 should outweigh a
5-line utility scoring 0. The simple average would bury it.

**Minimum line count floor:** Files with 0 lines are excluded (skipped files already excluded).

---

## Grade Labels

Used in terminal and HTML output for human-readable context.

| Score Range | Grade | Terminal Color |
|-------------|-------|----------------|
| 0–20 | Clean | Green |
| 21–50 | Moderate | Yellow |
| 51–75 | High Risk | Orange |
| 76–100 | Critical | Red |

---

## Trend Comparison

On each run, `RepoResult` stores `previous_score` if a cache file exists:

```python
delta = aggregate_score - previous_score  # None if no cache

# Display:
# ▲ +3.2  (debt increased — bad)
# ▼ -5.1  (debt decreased — good)
# ─  0.0  (unchanged)
```

Cache file (`.autopsy-cache.json`) schema:

```json
{
  "last_run": "2024-01-15T10:30:00Z",
  "aggregate_score": 41.2,
  "per_file": {
    "src/utils/helpers.py": 78.0,
    "src/api/handlers.py": 62.0
  }
}
```

Per-file trend shown in HTML report only (terminal would be too noisy).

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| File with syntax error | One `ERROR` issue added; `raw = 10`; analysis stops for that file |
| Empty file (0 lines) | `debt_score = 0.0`; excluded from aggregate weighted average |
| File with only `INFO` issues | Can still score non-zero but will stay low (≤20 for <10 infos) |
| File added since last run | No delta shown for that file; cache updated on next run |
| File deleted since last run | Removed from cache silently |
| Config weights changed between runs | Delta is technically wrong but not corrected (document this limitation) |

---

## Example Calculations

### helpers.py (from SCOPE.md example, score 78)

Issues assumed:
- 1 `ERROR`: GodClass (412 lines) → 10
- 2 `WARNING`: LongFunction, DeepNesting → 6
- 3 `INFO`: UnusedImport × 3 → 3

raw = 19 → score = min(100, 19/50 * 100) = **38**

*SCOPE.md shows 78—to hit that, assume more violations: e.g., CC002 + CG002 + SM002 in addition.*
With 5 ERRORs + 4 WARNINGs + 3 INFOs = 50+12+3 = 65 raw → score = **100** (capped).
Midpoint calibration: 3 ERRORs + 4 WARNINGs = 30+12 = 42 raw → score = **84**. Close enough.

*Exact score depends on real issues in real code; examples in SCOPE.md are illustrative.*

---

## Future Considerations (post-MVP)

- **ML calibration**: fit weights to "perceived debt" from developer surveys
- **Rule-specific weights**: `GodClass` might deserve a higher multiplier than `LongFunction`
- **File-type adjustments**: generated files, test files, migration files scored differently
- **Function-level debt**: expose per-function score for IDE tooltips
