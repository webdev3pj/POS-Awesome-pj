import argparse
from datetime import datetime, timedelta
import json

from relay.relay.storage import cleanup_outbox_rows


def main():
    ap = argparse.ArgumentParser(description="Clean historical relay outbox demo-noise rows.")
    ap.add_argument("--limit", type=int, default=500, help="Max rows to inspect/delete")
    ap.add_argument("--status", action="append", dest="statuses", default=["queued"], help="Outbox status filter (repeatable)")
    ap.add_argument("--event-type", action="append", dest="event_types", default=[], help="Outbox event_type filter (repeatable)")
    ap.add_argument("--days-old", type=int, default=1, help="Only rows older than N days (UTC)")
    ap.add_argument("--error-contains", default="", help="Substring filter on last_error")
    ap.add_argument("--local-ref-contains", default="", help="Substring filter on local_ref")
    ap.add_argument("--delete", action="store_true", help="Delete matched rows (default is dry-run)")
    args = ap.parse_args()

    cutoff = (datetime.utcnow() - timedelta(days=max(0, int(args.days_old)))).isoformat(timespec="seconds") + "Z"
    result = cleanup_outbox_rows(
        limit=max(1, int(args.limit)),
        statuses=args.statuses,
        event_types=args.event_types,
        created_before=cutoff,
        error_contains=args.error_contains,
        local_ref_contains=args.local_ref_contains,
        delete=bool(args.delete),
    )

    print(json.dumps({
        "ok": True,
        "action": "delete" if args.delete else "dry_run",
        "created_before": cutoff,
        "matched": result.get("matched", 0),
        "deleted": result.get("deleted", 0),
        "filters": result.get("filters", {}),
        "sample": [
            {
                "event_id": r.get("event_id"),
                "event_type": r.get("event_type"),
                "status": r.get("status"),
                "local_ref": r.get("local_ref"),
                "created_at": r.get("created_at"),
                "retries": r.get("retries"),
                "last_error": r.get("last_error"),
            }
            for r in (result.get("rows") or [])[:20]
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
