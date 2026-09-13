"""CLI for explicit, auditable approval/promotion/rollback operations."""

from __future__ import annotations

import argparse

from app.db.session import create_session_factory
from app.services.versioning_service import approve_batch, promote_release, rollback_active_release


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    command = parser.add_subparsers(dest="command", required=True)
    approve = command.add_parser("approve")
    approve.add_argument("--batch-id", required=True)
    approve.add_argument("--actor", required=True)
    approve.add_argument("--notes")
    promote = command.add_parser("promote")
    promote.add_argument("--release-id", required=True)
    promote.add_argument("--actor", required=True)
    promote.add_argument("--notes")
    rollback = command.add_parser("rollback")
    rollback.add_argument("--actor", required=True)
    rollback.add_argument("--notes")
    args = parser.parse_args()
    factory = create_session_factory(args.database_url)
    with factory() as session:
        if args.command == "approve":
            release = approve_batch(session, args.batch_id, approved_by=args.actor, notes=args.notes)
        elif args.command == "promote":
            release = promote_release(session, args.release_id, actor=args.actor, notes=args.notes)
        else:
            release = rollback_active_release(session, actor=args.actor, notes=args.notes)
    print(f"release_id={release.id} release_version={release.release_version} status={release.status}")


if __name__ == "__main__":
    main()
