"""`product` (`dim_product`) validation: `raw.product` -> `clean.product`
(docs/DATA_DICTIONARY.md §1).

Rejects (never defaults): a missing `product_id`, a duplicate `product_id`
within the batch, an unrecognised `family`, or a `size`/`family` mismatch -
`docs/DATA_DICTIONARY.md` §1 is explicit that an unrecognised family must be
"rejected at ingestion and reported, not defaulted to a guessed family".
"""

from __future__ import annotations

from typing import Any

from .quality import IssueKind, QualityIssue, QualityReport
from .validators import check_in_set, parse_optional_text, parse_required_text

TABLE_NAME = "product"
ALLOWED_FAMILIES = ("FOOT", "APPAREL", "PACK", "NUTRI")


def _find_duplicate_keys(raw_rows: list[dict[str, str]]) -> set[tuple[str, ...]]:
    seen: set[tuple[str, ...]] = set()
    duplicates: set[tuple[str, ...]] = set()
    for raw_row in raw_rows:
        key = (raw_row.get("product_id") or "",)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def validate_rows(raw_rows: list[dict[str, str]], report: QualityReport) -> list[dict[str, Any]]:
    report.rows_read[TABLE_NAME] = report.rows_read.get(TABLE_NAME, 0) + len(raw_rows)
    duplicate_keys = _find_duplicate_keys(raw_rows)

    clean_rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        key = (raw_row.get("product_id") or "",)

        if key in duplicate_keys:
            report.add(
                QualityIssue(
                    TABLE_NAME,
                    IssueKind.REJECTED,
                    "duplicate_key",
                    key,
                    f"product_id {raw_row.get('product_id')!r} appears more than once in this batch",
                )
            )
            continue

        product_id, id_error = parse_required_text(raw_row.get("product_id"), "product_id")
        product_name, name_error = parse_required_text(raw_row.get("product_name"), "product_name")
        family = (raw_row.get("family") or "").strip()
        family_error = "family is missing" if not family else check_in_set(
            family, ALLOWED_FAMILIES, "family"
        )
        size = parse_optional_text(raw_row.get("size"))
        unit_of_measure, uom_error = parse_required_text(
            raw_row.get("unit_of_measure"), "unit_of_measure"
        )

        errors = [e for e in (id_error, name_error, family_error, uom_error) if e]

        if not family_error:
            if family == "FOOT" and size is None:
                errors.append("FOOT product must have a size")
            if family != "FOOT" and size is not None:
                errors.append(f"{family} product must not have a size, got {size!r}")

        if errors:
            report.add(
                QualityIssue(TABLE_NAME, IssueKind.REJECTED, "invalid_product", key, "; ".join(errors))
            )
            continue

        clean_rows.append(
            {
                "product_id": product_id,
                "product_name": product_name,
                "family": family,
                "size": size,
                "unit_of_measure": unit_of_measure,
            }
        )

    report.rows_loaded[TABLE_NAME] = len(clean_rows)
    return clean_rows
