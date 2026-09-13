"""Run Phase 5 source -> staging -> validation -> canonical ingestion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.session import create_session_factory
from app.services.ingestion_service import ingest_sources


def report_markdown(summary: dict) -> str:
    lines = [
        "# Ingestion report", "", f"Batch: `{summary['batch_id']}`.", "",
        f"Source rows: **{summary['source_rows']:,}**. Staged rows: **{summary['staged_rows']:,}**.", "",
        "| # | House | Dataset | Source | Staged | Valid | Warning | Rejected | Unresolved | Blank ID |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summary["datasets"]:
        lines.append(f"| {item['order']} | {item['house']} | {item['dataset_type']} | {item['source_rows']:,} | {item['staged_rows']:,} | {item['valid_rows']:,} | {item['warning_rows']:,} | {item['rejected_rows']:,} | {item['unresolved_rows']:,} | {item['blank_id_rows']:,} |")
    lines.extend(["", "## Canonical records", ""])
    for name, count in summary["canonical"].items():
        lines.append(f"- `{name}`: {count:,}")
    lines.extend(["", "House assignment is derived from controlled dataset intake grouping because the source files do not contain a House field. Source workbooks were not modified.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    factory = create_session_factory(args.database_url)
    with factory() as session:
        summary = ingest_sources(session, manifest, args.data_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "ingestion_report.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (args.output_dir / "ingestion_report.md").write_text(report_markdown(summary), encoding="utf-8")
    (args.output_dir / "validation_report.md").write_text(report_markdown(summary).replace("# Ingestion report", "# Validation report"), encoding="utf-8")
    print(f"Batch {summary['batch_id']} completed; staged {summary['staged_rows']} source rows.")


if __name__ == "__main__":
    main()
