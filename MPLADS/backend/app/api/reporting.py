"""Generate a Phase 7 evidence report from the API contract and active database."""

from __future__ import annotations

import argparse
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def report() -> str:
    client = TestClient(app)
    health = client.get("/api/v1/health")
    active = client.get("/api/v1/datasets/active")
    summary = client.get("/api/v1/dashboard/summary")
    if not health.is_success or not active.is_success or not summary.is_success:
        raise RuntimeError("A required live API evidence endpoint did not return success.")
    paths = [path for path in app.openapi()["paths"] if path.startswith("/api/v1/")]
    health_data = health.json()
    active_data = active.json()["data"]
    summary_data = summary.json()["data"]
    lines = [
        "# Phase 7 API report", "",
        f"Versioned API paths in the live OpenAPI contract: **{len(paths)}**.",
        f"Application status: `{health_data['status']}`. Database status: `{health_data['database_status']}`. Migration: `{health_data['migration_version']}`.",
        f"Active release: `{health_data['active_release_version']}`.",
        f"Active dataset versions: **{len(active_data['datasets'])}**.",
        "",
        "## Database-derived summary response", "",
    ]
    lines.extend(f"- `{name}`: {value}" for name, value in summary_data.items())
    lines.extend([
        "",
        "Every value above was obtained through the live FastAPI endpoint at report generation time. It is not embedded in the API implementation.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report(), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
