"""Generate a concise database-derived Phase 6 release and analytics report."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.analytics.dashboard_service import core_metrics
from app.analytics.integrity_service import active_release_integrity
from app.analytics.lifecycle_analytics_service import lifecycle_summary
from app.db.session import create_session_factory
from app.models import DatasetRelease
from app.services.versioning_service import resolve_active_scope


def report(database_url: str) -> str:
    factory = create_session_factory(database_url)
    with factory() as session:
        scope = resolve_active_scope(session)
        release = session.get(DatasetRelease, scope.release_id)
        integrity = active_release_integrity(session)
        metrics = core_metrics(session).data
        lifecycle = lifecycle_summary(session).data
    lines = [
        "# Phase 6 report", "", f"Active release: `{scope.release_version}`.", f"Batch: `{scope.batch_id}`.", f"Release status: `{release.status if release else 'UNAVAILABLE'}`.", "",
        "## Integrity", "",
    ]
    lines.extend(f"- `{name}`: {value}" for name, value in integrity.items())
    lines.extend(["", "## Core metrics", ""])
    lines.extend(f"- `{name}`: {value}" for name, value in metrics.items())
    lines.extend(["", "## Lifecycle", ""])
    lines.extend(f"- `{name}`: {value}" for name, value in lifecycle.items())
    lines.extend(["", "The values above are calculated from the active database release at report generation time. No frontend or static analytical data was created.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report(args.database_url), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
