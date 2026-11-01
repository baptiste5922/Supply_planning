"""Data-quality reporting for ingestion (docs/ARCHITECTURE.md §2, §5).

Three distinct outcomes exist per row, and they must not be collapsed into one
"valid/invalid" flag (see each table's missing-data rule in
`docs/DATA_DICTIONARY.md`):

  - REJECTED: the row is excluded from `clean` - it cannot be trusted for a
    calculation (e.g. an unknown `family`, a missing `promised_receipt_date` on
    a confirmed order).
  - FLAGGED: the row IS loaded into `clean` as-is, and also reported - it is a
    valid, true fact a planner should see (e.g. negative available stock, a
    capacity overload). Rejecting it would hide a real signal.
  - MISSING: there is no row to reject - the absence itself is the defect,
    found by comparing loaded keys against the expected grain (e.g. a missing
    SKU-week).

Every issue carries a `reason_code` (a short, stable string a test or a
downstream report can match on) and the business key it concerns, never a row
index - the report answers "which fact is wrong", not "which line of the file".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IssueKind(str, Enum):
    REJECTED = "rejected"
    FLAGGED = "flagged"
    MISSING = "missing"


@dataclass(frozen=True)
class QualityIssue:
    table: str
    kind: IssueKind
    reason_code: str
    key: tuple[str, ...]
    detail: str


@dataclass
class QualityReport:
    """Accumulates issues across one ingestion run, plus the row counts the
    "ingestion is logged and reports row counts" acceptance criterion needs."""

    issues: list[QualityIssue] = field(default_factory=list)
    rows_read: dict[str, int] = field(default_factory=dict)
    rows_loaded: dict[str, int] = field(default_factory=dict)

    def add(self, issue: QualityIssue) -> None:
        self.issues.append(issue)

    def rejected_keys(self, table: str) -> set[tuple[str, ...]]:
        return {
            issue.key
            for issue in self.issues
            if issue.table == table and issue.kind is IssueKind.REJECTED
        }

    def count_by_kind(self, table: str, kind: IssueKind) -> int:
        return sum(1 for issue in self.issues if issue.table == table and issue.kind is kind)

    def summary_lines(self) -> list[str]:
        """One human-readable line per table - what `run.py` logs after each load."""
        lines = []
        for table, read_count in self.rows_read.items():
            loaded_count = self.rows_loaded.get(table, 0)
            rejected = self.count_by_kind(table, IssueKind.REJECTED)
            flagged = self.count_by_kind(table, IssueKind.FLAGGED)
            missing = self.count_by_kind(table, IssueKind.MISSING)
            lines.append(
                f"{table}: read={read_count} loaded={loaded_count} "
                f"rejected={rejected} flagged={flagged} missing={missing}"
            )
        return lines
