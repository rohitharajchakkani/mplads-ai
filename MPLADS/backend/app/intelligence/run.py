"""Explicit command for a reproducible protected monitoring run."""
from __future__ import annotations

import json

from app.core.config import get_settings
from app.db.session import create_session_factory
from app.intelligence.engine import run_monitoring_engine


def main() -> None:
    with create_session_factory(get_settings().database_url)() as session:
        print(json.dumps(run_monitoring_engine(session), indent=2, default=str))


if __name__ == "__main__":
    main()
