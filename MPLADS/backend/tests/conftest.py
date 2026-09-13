"""Session-wide SQLite isolation for tests that exercise mutable API workflows."""
from __future__ import annotations

import sqlite3
import gc
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.db.session import create_session_factory
from app.models.ai import AiRequestAudit


@dataclass(frozen=True)
class IsolatedDatabase:
    development_path: Path
    test_path: Path
    development_audit_count: int


def _sqlite_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise RuntimeError("The MPLADS test suite requires a file-backed SQLite database snapshot.")
    return Path(url.database).resolve()


@pytest.fixture(scope="session", autouse=True)
def isolated_database():
    """Point all application sessions at a consistent, disposable SQLite backup.

    The source development database is opened read-only by SQLite's backup API and
    is never used for test writes. Application audit records created by normal use
    remain durable in that source database; test audit rows exist only in this copy.
    """
    source_settings = get_settings()
    development_path = _sqlite_path(source_settings.database_url)
    if not development_path.exists():
        raise RuntimeError("Configured development SQLite database is unavailable for test isolation.")

    with create_session_factory(source_settings.database_url)() as source_session:
        development_audit_count = int(source_session.scalar(select(func.count()).select_from(AiRequestAudit)) or 0)

    runtime_root = Path(__file__).resolve().parents[1] / ".test-runtime"
    runtime_root.mkdir(exist_ok=True)
    # Windows can retain the final SQLite handle until the test process exits.
    # Reusing one ignored snapshot prevents repeated pytest invocations from
    # accumulating multi-gigabyte directories; the next invocation replaces the
    # released snapshot before any test runs.
    test_path = runtime_root / "pytest.sqlite"
    test_path.unlink(missing_ok=True)
    with sqlite3.connect(development_path) as source_connection, sqlite3.connect(test_path) as test_connection:
        source_connection.backup(test_connection)

    patch = pytest.MonkeyPatch()
    patch.setenv("DATABASE_URL", f"sqlite:///{test_path.as_posix()}")
    get_settings.cache_clear()
    try:
        yield IsolatedDatabase(development_path, test_path, development_audit_count)
    finally:
        get_settings.cache_clear()
        patch.undo()
        get_settings.cache_clear()
        gc.collect()
        try:
            test_path.unlink(missing_ok=True)
        except PermissionError:
            # It is released at interpreter exit and replaced by the next run.
            pass
