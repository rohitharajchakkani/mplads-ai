"""Generate an evidence-only intake inventory before dataset assignment or transformation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd

SUPPORTED_TABULAR_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xls", ".parquet"}
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def profile_frame(frame: pd.DataFrame) -> dict[str, Any]:
    rows = len(frame.index)
    return {
        "row_count": rows,
        "column_count": len(frame.columns),
        "columns": [
            {
                "name": str(column),
                "inferred_dtype": str(frame[column].dtype),
                "null_count": int(frame[column].isna().sum()),
                "null_percent": round(float(frame[column].isna().mean() * 100), 2) if rows else None,
            }
            for column in frame.columns
        ],
        "duplicate_row_count": int(frame.duplicated().sum()),
        # Source samples are intentionally excluded: reviewers inspect them locally before redaction policy.
    }


def _json_value(value: Any) -> Any:
    """Return a small, serializable evidence value without changing the source."""
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference)
    if not letters:
        return 0
    index = 0
    for letter in letters.group(0):
        index = index * 26 + ord(letter) - 64
    return index


def _text_content(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    return "".join(element.itertext())


def _xlsx_sheet_locations(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        relation.attrib["Id"]: relation.attrib["Target"].lstrip("/")
        for relation in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
    }
    locations = []
    for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
        target = targets[sheet.attrib[f"{{{REL_NS}}}id"]]
        locations.append((sheet.attrib["name"], target if target.startswith("xl/") else f"xl/{target}"))
    return locations


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [_text_content(item) or "" for item in root.findall(f"{{{MAIN_NS}}}si")]


def _xlsx_rows(archive: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]) -> list[dict[int, Any]]:
    root = ET.fromstring(archive.read(sheet_path))
    rows: list[dict[int, Any]] = []
    for row in root.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row"):
        values: dict[int, Any] = {0: int(row.attrib.get("r", len(rows) + 1))}
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            column = _column_index(cell.attrib.get("r", ""))
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                value = _text_content(cell.find(f"{{{MAIN_NS}}}is"))
            else:
                value = _text_content(cell.find(f"{{{MAIN_NS}}}v"))
                if cell_type == "s" and value is not None:
                    value = shared_strings[int(value)]
                elif cell_type == "b" and value is not None:
                    value = value == "1"
            if column:
                values[column] = value
        rows.append(values)
    return rows


def _row_values(row: dict[int, Any], width: int) -> list[Any]:
    return [_json_value(row.get(column)) for column in range(1, width + 1)]


def load_xlsx_table(path: Path, *, header_source_row: int) -> tuple[list[str], list[list[Any]]]:
    """Load values from an inspected .xlsx sheet without interpreting formatting or styles."""
    with zipfile.ZipFile(path) as archive:
        locations = _xlsx_sheet_locations(archive)
        if len(locations) != 1:
            raise ValueError(f"Expected one worksheet, found {len(locations)} in {path.name}")
        rows = _xlsx_rows(archive, locations[0][1], _xlsx_shared_strings(archive))
    width = max((max(row, default=0) for row in rows), default=0)
    header_index = header_source_row - 1
    if header_index >= len(rows):
        raise ValueError(f"Header row {header_source_row} is outside {path.name}")
    headers = [str(value or "").strip() for value in _row_values(rows[header_index], width)]
    if not headers or any(not header for header in headers) or len(set(headers)) != len(headers):
        raise ValueError(f"Header row {header_source_row} is not a complete unique schema in {path.name}")
    return headers, [_row_values(row, width) for row in rows[header_index + 1 :]]


def load_xlsx_table_with_provenance(path: Path, *, header_source_row: int) -> tuple[list[str], list[tuple[int, list[Any]]]]:
    """As ``load_xlsx_table``, retaining each XML worksheet row number for provenance."""
    with zipfile.ZipFile(path) as archive:
        locations = _xlsx_sheet_locations(archive)
        if len(locations) != 1:
            raise ValueError(f"Expected one worksheet, found {len(locations)} in {path.name}")
        rows = _xlsx_rows(archive, locations[0][1], _xlsx_shared_strings(archive))
    width = max((max(row, default=0) for row in rows), default=0)
    header_index = header_source_row - 1
    headers = [str(value or "").strip() for value in _row_values(rows[header_index], width)]
    if not headers or any(not header for header in headers) or len(set(headers)) != len(headers):
        raise ValueError(f"Header row {header_source_row} is not a complete unique schema in {path.name}")
    return headers, [(int(row[0]), _row_values(row, width)) for row in rows[header_index + 1 :]]


def profile_xlsx_sheet(archive: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]) -> dict[str, Any]:
    """Read worksheet values without loading potentially malformed Excel styles."""
    rows = _xlsx_rows(archive, sheet_path, shared_strings)
    width = max((max(row, default=0) for row in rows), default=0)
    preview = rows[:20]
    return {
        "raw_row_count": len(rows),
        "raw_column_count": width,
        "first_20_raw_rows": [
            {"source_row": index + 1, "values": _row_values(row, width)}
            for index, row in enumerate(preview)
        ],
        "candidate_header_rows": [
            {
                "source_row": index + 1,
                "non_empty_cells": len([column for column in row if column > 0]),
                "values": _row_values(row, width),
            }
            for index, row in enumerate(rows[:30])
            if len([column for column in row if column > 0]) >= 2
        ],
        "raw_duplicate_row_count": len(rows) - len({tuple(_row_values(row, width)) for row in rows}),
        "header_status": "PENDING_REVIEW",
    }


def profile_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    record: dict[str, Any] = {
        "filename": path.name,
        "extension": suffix,
        "byte_size": path.stat().st_size,
        "sha256": sha256(path),
        "inspection_status": "INSPECTED" if suffix in SUPPORTED_TABULAR_SUFFIXES else "UNSUPPORTED_FORMAT",
    }
    if suffix == ".csv":
        record["tables"] = {"default": profile_frame(pd.read_csv(path, nrows=None))}
    elif suffix == ".tsv":
        record["tables"] = {"default": profile_frame(pd.read_csv(path, sep="\t", nrows=None))}
    elif suffix == ".xlsx":
        with zipfile.ZipFile(path) as archive:
            shared_strings = _xlsx_shared_strings(archive)
            locations = _xlsx_sheet_locations(archive)
            record["sheet_names"] = [name for name, _ in locations]
            record["sheets"] = {
                name: profile_xlsx_sheet(archive, sheet_path, shared_strings)
                for name, sheet_path in locations
            }
    elif suffix == ".xls":
        record["inspection_status"] = "UNSUPPORTED_XLS_READER_REQUIRED"
        record["reason"] = "The source is a legacy .xls file and requires an approved compatible reader."
    elif suffix == ".parquet":
        record["tables"] = {"default": profile_frame(pd.read_parquet(path))}
    else:
        record["reason"] = "Add a format-specific reader before this source can be audited."
    return record


def inspect_directory(source_dir: Path) -> dict[str, Any]:
    files = sorted(path for path in source_dir.rglob("*") if path.is_file() and not path.name.startswith("."))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_directory": str(source_dir.resolve()),
        "file_count": len(files),
        "expected_file_count": 12,
        "file_count_status": "MATCH" if len(files) == 12 else "MISMATCH",
        "formal_assignment_status": "UNASSIGNED_PENDING_REVIEW",
        "records": [profile_file(path) for path in files],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.source_dir.is_dir():
        raise SystemExit(f"Source directory not found: {args.source_dir}")
    report = inspect_directory(args.source_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "dataset_intake_inventory.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {output} ({report['file_count']} file(s); assignments intentionally pending review).")


if __name__ == "__main__":
    main()
