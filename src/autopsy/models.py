from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Issue:
    rule_id: str
    severity: Severity
    message: str
    file: Path
    line: int
    col: int = 0


@dataclass
class FunctionMetrics:
    name: str
    start_line: int
    end_line: int
    line_count: int
    arg_count: int  # excludes self/cls
    max_nesting_depth: int
    cyclomatic: int
    cognitive: int


@dataclass
class ClassMetrics:
    name: str
    start_line: int
    end_line: int
    line_count: int
    method_count: int


@dataclass
class FileMetrics:
    total_lines: int
    function_count: int
    class_count: int
    import_count: int
    max_cyclomatic: int  # worst function in file
    avg_cyclomatic: float
    max_cognitive: int
    functions: list[FunctionMetrics] = field(default_factory=list)
    classes: list[ClassMetrics] = field(default_factory=list)


@dataclass
class FileResult:
    path: Path
    language: str  # "python", "javascript"
    metrics: FileMetrics
    issues: list[Issue] = field(default_factory=list)
    debt_score: float = 0.0
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class RepoResult:
    root: Path
    files: list[FileResult]
    aggregate_score: float
    run_timestamp: datetime
    previous_score: float | None = None  # from cache, if available
