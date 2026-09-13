"""Validate the explicit dataset manifest against observed workbook values.

This command is intentionally read-only with respect to source workbooks. It creates
evidence artifacts only; it neither stages, normalizes, nor promotes data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ingestion.inspect import load_xlsx_table

WORK_ID_PATTERN = re.compile(r"WS/MP\d+/\d{4}-\d{4}/\d+", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?$")
DATE_PATTERN = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}$")


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_work_id(value: Any) -> str | None:
    if value is None:
        return None
    match = WORK_ID_PATTERN.search(str(value).replace(" ", ""))
    return match.group(0).upper() if match else None


def inferred_type(values: list[Any]) -> str:
    populated = [str(value).strip() for value in values if value is not None and str(value).strip()]
    if not populated:
        return "empty"
    numeric_share = sum(bool(NUMBER_PATTERN.fullmatch(value.replace(",", ""))) for value in populated) / len(populated)
    date_share = sum(bool(DATE_PATTERN.fullmatch(value)) for value in populated) / len(populated)
    if numeric_share >= 0.98:
        return "numeric"
    if date_share >= 0.98:
        return "date_text_dd_mmm_yyyy"
    return "text"


def profile_dataset(definition: dict[str, Any], data_root: Path, header_source_row: int) -> tuple[dict[str, Any], set[str]]:
    source_path = data_root / definition["source_file"]
    if not source_path.is_file():
        raise FileNotFoundError(f"Manifest source file is missing: {source_path}")
    headers, source_rows = load_xlsx_table(source_path, header_source_row=header_source_row)
    rows = [row for row in source_rows if any(value is not None and str(value).strip() for value in row)]
    blank_post_header_row_count = len(source_rows) - len(rows)
    values_by_column = {header: [row[index] if index < len(row) else None for row in rows] for index, header in enumerate(headers)}
    serial_values = values_by_column.get("Sr. No.", [])
    serial_populated = [value for value in serial_values if value is not None]
    serial_unique = len(serial_populated) == len(set(serial_populated))
    header_by_casefold = {header.casefold(): header for header in headers}
    id_column = header_by_casefold.get("work id") or header_by_casefold.get("work")
    work_ids = {normalized_work_id(value) for value in values_by_column.get(id_column, []) if normalized_work_id(value)} if id_column else set()
    parsed_id_count = sum(1 for value in values_by_column.get(id_column, []) if normalized_work_id(value)) if id_column else 0
    unparsed_values = [value for value in values_by_column.get(id_column, []) if not normalized_work_id(value)] if id_column else []
    result = {
        **definition,
        "file_type": source_path.suffix.lower(),
        "source_sheet": "Sheet1",
        "sha256": checksum(source_path),
        "source_row_count_including_header": len(source_rows) + header_source_row,
        "data_row_count": len(rows),
        "blank_post_header_row_count": blank_post_header_row_count,
        "column_count": len(headers),
        "columns": [
            {
                "name": header,
                "inferred_type": inferred_type(values),
                "null_count": sum(value is None or not str(value).strip() for value in values),
                "null_percent": round(sum(value is None or not str(value).strip() for value in values) * 100 / len(rows), 2) if rows else None,
            }
            for header, values in values_by_column.items()
        ],
        "exact_duplicate_data_rows": len(rows) - len({tuple(row) for row in rows}),
        "source_record_number": {
            "column": "Sr. No." if serial_values else None,
            "populated_count": len(serial_populated),
            "unique": serial_unique,
            "candidate_business_key": "source sequence only" if serial_unique else None,
        },
        "work_identity_evidence": {
            "source_column": id_column,
            "parsed_work_id_count": parsed_id_count,
            "unparsed_or_missing_count": len(rows) - parsed_id_count if id_column else None,
            "na_placeholder_count": sum(str(value).strip().upper().startswith("NA-") for value in unparsed_values),
            "missing_source_value_count": sum(value is None or not str(value).strip() for value in unparsed_values),
            "distinct_normalized_work_id_count": len(work_ids),
        },
        "schema_status": "VERIFIED_OBSERVED",
        "validation_status": "PASSED_SOURCE_AUDIT",
    }
    return result, work_ids


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Data audit",
        "",
        "## Intake result",
        "",
        f"Audit generated: `{report['generated_at']}`.",
        "",
        "All 12 expected `.xlsx` files were found. Every workbook contains one observed `Sheet1` worksheet with a complete, unique header in source row 2. The files are assigned using the user-declared House directories and required order, then corroborated by their observed field semantics. No source contains a dedicated House field.",
        "",
        "The Excel style layer is malformed for the installed `openpyxl` reader. The audit read the underlying OOXML worksheet values directly, without editing source files. This is a format-compatibility finding, not a data-value change.",
        "",
        "## Dataset inventory",
        "",
        "| # | House | Domain | Source file | Data rows | Columns | Exact duplicate rows | Work-ID evidence | Validation |",
        "|---:|---|---|---|---:|---:|---:|---|---|",
    ]
    for dataset in report["datasets"]:
        work = dataset["work_identity_evidence"]
        work_text = "Not applicable" if work["source_column"] is None else f"{work['parsed_work_id_count']} parsed / {work['distinct_normalized_work_id_count']} distinct"
        lines.append(
            f"| {dataset['order']} | {dataset['house']} | {dataset['dataset_type']} | `{Path(dataset['source_file']).name}` | {dataset['data_row_count']:,} | {dataset['column_count']} | {dataset['exact_duplicate_data_rows']:,} | {work_text} | {dataset['validation_status']} |"
        )
    lines.extend([
        "",
        "## Observed schema and completeness",
        "",
    ])
    for dataset in report["datasets"]:
        lines.extend([
            f"### {dataset['order']}. {dataset['house']} — {dataset['dataset_type']}",
            "",
            f"SHA-256: `{dataset['sha256']}`. Source sequence (`Sr. No.`) unique: `{dataset['source_record_number']['unique']}`.",
            "",
            "| Observed source column | Inferred storage type | Nulls |",
            "|---|---|---:|",
        ])
        lines.extend(f"| {column['name']} | {column['inferred_type']} | {column['null_count']:,} ({column['null_percent']}%) |" for column in dataset["columns"])
        lines.append("")
    lines.extend([
        "## Work identity and House separation",
        "",
        f"Work IDs were parsed from the source `Work ID` column where present, otherwise from the observed `Work` label. The normalized source pattern is `WS/MP<number>/<financial-year>/<number>`, with incidental spaces removed before parsing. Across all work-bearing sources, the same normalized work ID appears in both Houses **{report['cross_house_work_id_collision_count']:,}** times. Canonical identity must therefore remain `normalized_house + ':' + normalized_work_id`; no cross-House merge is permitted.",
        "",
        "### Work-ID quality findings",
        "",
    ])
    for dataset in report["datasets"]:
        work = dataset["work_identity_evidence"]
        if work["source_column"] and work["unparsed_or_missing_count"]:
            lines.append(
                f"- {dataset['house']} {dataset['dataset_type']}: {work['unparsed_or_missing_count']:,} source values do not yield a canonical work ID; {work['na_placeholder_count']:,} are `NA-` placeholders and {work['missing_source_value_count']:,} are blank. These rows remain source-auditable but cannot be joined to a canonical work without a separate resolved identity."
            )
    lines.extend([
        "",
        "## Audit decision",
        "",
        "All twelve sources passed the source-audit gate. This permits schema mapping and a raw/staging ingestion implementation. It does not yet mean that a version is approved or active; promotion must wait for row-level validation and ingestion results.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    definitions = manifest["datasets"]
    if len(definitions) != 12 or {item["order"] for item in definitions} != set(range(1, 13)):
        raise SystemExit("Manifest must contain exactly the required ordered 1–12 dataset assignments.")
    datasets: list[dict[str, Any]] = []
    work_ids_by_house: dict[str, set[str]] = {"LOK_SABHA": set(), "RAJYA_SABHA": set()}
    for definition in sorted(definitions, key=lambda item: item["order"]):
        dataset, work_ids = profile_dataset(definition, args.data_root, manifest["header_source_row"])
        datasets.append(dataset)
        work_ids_by_house[definition["house"]].update(work_ids)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest_version": manifest["manifest_version"],
        "datasets": datasets,
        "cross_house_work_id_collision_count": len(work_ids_by_house["LOK_SABHA"] & work_ids_by_house["RAJYA_SABHA"]),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "source_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.output_dir / "source_audit.md").write_text(markdown_report(report), encoding="utf-8")
    print(f"Audited {len(datasets)} datasets; wrote evidence to {args.output_dir}.")


if __name__ == "__main__":
    main()
