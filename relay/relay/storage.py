import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "relay.db")
CONFIG_PATH = os.path.join(DATA_DIR, "relay_config.json")


DEFAULT_CONFIG = {
    "frappe_base_url": "",
    "api_key": "",
    "api_secret": "",
    "relay_host": "0.0.0.0",
    "relay_port": 8787,
    "public_base_url": "",
    "site_name": "",
    "offline_mode": True,
    "poll_seconds": 5,
    "allowed_subnet": "192.168.50.0/24",
    # Phase 3 baseline relay client auth (browser -> relay). Keep disabled until
    # a matching key is configured in the cloud app bootstrap response.
    "relay_client_auth_required": False,
    "relay_client_auth_key": "",
}


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


@contextmanager
def get_db():
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_column(conn, table_name, column_name, column_type_sql):
    try:
        cur = conn.execute(f"PRAGMA table_info({table_name})")
        existing = {str(r["name"]) for r in cur.fetchall()}
    except Exception:
        existing = set()
    if column_name in existing:
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_sql}")


def _normalize_source_meta(source_meta=None):
    src = source_meta if isinstance(source_meta, dict) else {}
    origin = str(src.get("source_origin") or "").strip()[:500]
    env = str(src.get("source_env") or "").strip()[:100]
    ua = str(src.get("source_user_agent") or "").strip()[:1000]
    return {
        "source_origin": origin,
        "source_env": env,
        "source_user_agent": ua,
    }


def init_db():
    with get_db() as conn:
        # Legacy queue table kept for backward compatibility
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                retries INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # v2 local-first core entities
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_tokens (
                token_id TEXT PRIMARY KEY,
                pos_profile_id TEXT NOT NULL,
                cashier_user_id TEXT,
                customer_id TEXT,
                customer_name TEXT,
                source_origin TEXT,
                source_env TEXT,
                source_user_agent TEXT,
                status TEXT NOT NULL DEFAULT 'TOKEN_OPEN',
                expires_at TEXT,
                void_reason TEXT,
                voided_by TEXT,
                consumed_sale_ref TEXT,
                consumed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_token_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id TEXT NOT NULL,
                item_code TEXT NOT NULL,
                item_name TEXT,
                qty REAL NOT NULL,
                uom TEXT,
                rate REAL,
                amount REAL,
                payload TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(token_id) REFERENCES relay_tokens(token_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_cashier_sessions (
                session_id TEXT PRIMARY KEY,
                pos_profile_id TEXT NOT NULL,
                cashier_user_id TEXT NOT NULL,
                device_id TEXT,
                source_origin TEXT,
                source_env TEXT,
                source_user_agent TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN',
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                close_note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_local_sales (
                local_sale_ref TEXT PRIMARY KEY,
                token_id TEXT,
                pos_profile_id TEXT NOT NULL,
                cashier_user_id TEXT,
                cashier_session_id TEXT,
                device_id TEXT,
                idempotency_key TEXT NOT NULL UNIQUE,
                sale_status TEXT NOT NULL DEFAULT 'SALE_COMMITTED_LOCAL',
                pick_status TEXT NOT NULL DEFAULT 'PAID_PENDING_PICK',
                dispatch_status TEXT NOT NULL DEFAULT 'PENDING',
                paid INTEGER NOT NULL DEFAULT 1,
                total REAL,
                net_total REAL,
                customer_id TEXT,
                customer_name TEXT,
                invoice_payload TEXT,
                data_payload TEXT,
                cloud_invoice_name TEXT,
                cloud_sync_status TEXT NOT NULL DEFAULT 'SALE_SYNC_PENDING',
                cloud_sync_error TEXT,
                source_origin TEXT,
                source_env TEXT,
                source_user_agent TEXT,
                dispatch_proof_payload TEXT NOT NULL DEFAULT '{}',
                dispatch_exception_state TEXT NOT NULL DEFAULT 'NONE',
                cashier_adjustment_required INTEGER NOT NULL DEFAULT 0,
                released_by TEXT,
                released_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(token_id) REFERENCES relay_tokens(token_id),
                FOREIGN KEY(cashier_session_id) REFERENCES relay_cashier_sessions(session_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_local_sale_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                local_sale_ref TEXT NOT NULL,
                item_code TEXT,
                item_name TEXT,
                qty REAL,
                uom TEXT,
                rate REAL,
                amount REAL,
                line_status TEXT,
                pick_status TEXT,
                payload TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(local_sale_ref) REFERENCES relay_local_sales(local_sale_ref)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_idempotency (
                idempotency_key TEXT PRIMARY KEY,
                token_id TEXT,
                local_sale_ref TEXT,
                request_hash TEXT,
                response_payload TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_pick_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                local_sale_ref TEXT NOT NULL,
                picker_user_id TEXT,
                event_type TEXT NOT NULL,
                notes TEXT,
                payload TEXT,
                source_origin TEXT,
                source_env TEXT,
                source_user_agent TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(local_sale_ref) REFERENCES relay_local_sales(local_sale_ref)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_dispatch_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                local_sale_ref TEXT NOT NULL,
                dispatcher_user_id TEXT,
                event_type TEXT NOT NULL,
                notes TEXT,
                payload TEXT,
                source_origin TEXT,
                source_env TEXT,
                source_user_agent TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(local_sale_ref) REFERENCES relay_local_sales(local_sale_ref)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_customers (
                customer_id TEXT PRIMARY KEY,
                customer_name TEXT,
                mobile_no TEXT,
                email_id TEXT,
                tax_id TEXT,
                payload TEXT,
                updated_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_items_cache (
                item_code TEXT PRIMARY KEY,
                item_name TEXT,
                stock_uom TEXT,
                barcode TEXT,
                rate REAL,
                payload TEXT,
                updated_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_outbox (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                idempotency_key TEXT,
                local_ref TEXT,
                payload TEXT NOT NULL,
                source_origin TEXT,
                source_env TEXT,
                source_user_agent TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                retries INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                last_error TEXT,
                cloud_ref TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_quotes (
                quote_id TEXT PRIMARY KEY,
                cloud_quote_name TEXT,
                pos_profile_id TEXT NOT NULL,
                created_by TEXT,
                customer_id TEXT,
                customer_name TEXT,
                currency TEXT,
                base_total REAL NOT NULL DEFAULT 0,
                latest_total REAL NOT NULL DEFAULT 0,
                delta_total REAL NOT NULL DEFAULT 0,
                valid_until TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN',
                converted_token_id TEXT,
                converted_local_sale_ref TEXT,
                source_origin TEXT,
                source_env TEXT,
                source_user_agent TEXT,
                payload TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_quote_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id TEXT NOT NULL,
                item_code TEXT,
                item_name TEXT,
                qty REAL NOT NULL DEFAULT 0,
                uom TEXT,
                rate REAL NOT NULL DEFAULT 0,
                amount REAL NOT NULL DEFAULT 0,
                conversion_factor REAL NOT NULL DEFAULT 1,
                payload TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(quote_id) REFERENCES relay_quotes(quote_id)
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_relay_tokens_profile_status
            ON relay_tokens(pos_profile_id, status)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_relay_sessions_profile_status
            ON relay_cashier_sessions(pos_profile_id, status)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_relay_sales_profile_pick_dispatch
            ON relay_local_sales(pos_profile_id, pick_status, dispatch_status)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_relay_outbox_status_next_attempt
            ON relay_outbox(status, next_attempt_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_relay_quotes_profile_status
            ON relay_quotes(pos_profile_id, status)
            """
        )

        # Backward-compatible schema upgrades for existing relay DBs.
        for table_name in ("relay_tokens", "relay_cashier_sessions", "relay_local_sales", "relay_pick_events", "relay_dispatch_events", "relay_outbox"):
            _ensure_column(conn, table_name, "source_origin", "TEXT")
            _ensure_column(conn, table_name, "source_env", "TEXT")
            _ensure_column(conn, table_name, "source_user_agent", "TEXT")
        _ensure_column(conn, "relay_local_sales", "dispatch_proof_payload", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "relay_local_sales", "dispatch_exception_state", "TEXT NOT NULL DEFAULT 'NONE'")
        _ensure_column(conn, "relay_local_sales", "cashier_adjustment_required", "INTEGER NOT NULL DEFAULT 0")
        for table_name in ("relay_quotes", "relay_quote_lines"):
            _ensure_column(conn, table_name, "source_origin", "TEXT")
            _ensure_column(conn, table_name, "source_env", "TEXT")
            _ensure_column(conn, table_name, "source_user_agent", "TEXT")


def load_config():
    ensure_data_dir()
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    merged = DEFAULT_CONFIG.copy()
    merged.update(raw)
    return merged


def save_config(config):
    ensure_data_dir()
    merged = DEFAULT_CONFIG.copy()
    merged.update(config or {})
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    return merged


def _now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def enqueue_event(event_type, payload):
    now = _now_iso()
    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO relay_queue (event_type, payload, status, retries, last_error, created_at, updated_at)
            VALUES (?, ?, 'queued', 0, NULL, ?, ?)
            """,
            (event_type, payload_json, now, now),
        )
        return cur.lastrowid


def list_queue(limit=200):
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT id, event_type, payload, status, retries, last_error, created_at, updated_at
            FROM relay_queue
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            try:
                row["payload"] = json.loads(row.get("payload") or "{}")
            except Exception:
                pass
        return rows


def queue_counts():
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT status, COUNT(*) as cnt
            FROM relay_queue
            GROUP BY status
            """
        )
        raw = {r["status"]: r["cnt"] for r in cur.fetchall()}
    return {
        "queued": int(raw.get("queued", 0)),
        "processing": int(raw.get("processing", 0)),
        "done": int(raw.get("done", 0)),
        "failed": int(raw.get("failed", 0)),
        "total": sum(int(v) for v in raw.values()) if raw else 0,
    }


def get_next_queued_event():
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT id, event_type, payload, status, retries, last_error, created_at, updated_at
            FROM relay_queue
            WHERE status = 'queued'
            ORDER BY id ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            data["payload"] = json.loads(data.get("payload") or "{}")
        except Exception:
            data["payload"] = {}
        return data


def mark_processing(event_id):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_queue
            SET status = 'processing', updated_at = ?
            WHERE id = ?
            """,
            (_now_iso(), int(event_id)),
        )


def mark_done(event_id):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_queue
            SET status = 'done', last_error = NULL, updated_at = ?
            WHERE id = ?
            """,
            (_now_iso(), int(event_id)),
        )


def mark_failed(event_id, error):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_queue
            SET status = 'failed', retries = retries + 1, last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (str(error)[:1000], _now_iso(), int(event_id)),
        )


def retry_failed(event_id):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_queue
            SET status = 'queued', updated_at = ?
            WHERE id = ?
            """,
            (_now_iso(), int(event_id)),
        )


def _dumps(payload):
    return json.dumps(payload or {}, ensure_ascii=False)


def _loads(payload):
    if payload in (None, ""):
        return {}
    try:
        return json.loads(payload)
    except Exception:
        return {}


def _generate_token_id():
    return uuid.uuid4().hex[:10].upper()


def _generate_session_id():
    return f"SESS-{uuid.uuid4().hex[:12].upper()}"


def _generate_local_sale_ref(pos_profile_id=None):
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6].upper()
    profile_code = (pos_profile_id or "POS")[:4].upper()
    return f"LSR-{profile_code}-{stamp}-{suffix}"


def _generate_quote_id(pos_profile_id=None):
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6].upper()
    profile_code = (pos_profile_id or "POS")[:4].upper()
    return f"LQ-{profile_code}-{stamp}-{suffix}"


def _sum_amount_from_lines(lines):
    total = 0.0
    for line in lines or []:
        qty = float((line or {}).get("qty") or 0)
        rate = float((line or {}).get("rate") or 0)
        amount = (line or {}).get("amount")
        total += float(amount if amount is not None else (qty * rate))
    return total


def _quote_line_rows(raw_lines):
    rows = []
    for raw in raw_lines or []:
        if not isinstance(raw, dict):
            continue
        item_code = str(raw.get("item_code") or "").strip()
        if not item_code:
            continue
        qty = float(raw.get("qty") or 0)
        rate = float(raw.get("rate") or 0)
        amount = raw.get("amount")
        if amount is None:
            amount = qty * rate
        rows.append(
            {
                "item_code": item_code,
                "item_name": str(raw.get("item_name") or "").strip(),
                "qty": qty,
                "uom": str(raw.get("uom") or "").strip(),
                "rate": rate,
                "amount": float(amount or 0),
                "conversion_factor": float(raw.get("conversion_factor") or 1),
                "payload": dict(raw),
            }
        )
    return rows


def upsert_local_quote(payload, source_meta=None):
    payload = payload if isinstance(payload, dict) else {}
    now = _now_iso()
    source = _normalize_source_meta(source_meta)
    pos_profile_id = str(payload.get("pos_profile_id") or "").strip()
    if not pos_profile_id:
        raise ValueError("pos_profile_id is required")

    quote_id = str(payload.get("quote_id") or "").strip() or _generate_quote_id(pos_profile_id=pos_profile_id)
    lines = _quote_line_rows(payload.get("items") or payload.get("lines") or [])
    if not lines:
        raise ValueError("At least one quote line is required")

    customer_id = str(payload.get("customer_id") or "").strip()
    customer_name = str(payload.get("customer_name") or customer_id).strip()
    created_by = str(payload.get("created_by") or payload.get("cashier_user_id") or "").strip()
    currency = str(payload.get("currency") or "").strip()
    valid_until = str(payload.get("valid_until") or "").strip()
    status = str(payload.get("status") or "OPEN").strip().upper()
    if status not in ("OPEN", "EXPIRED", "CONVERTED", "VOID"):
        status = "OPEN"

    base_total = float(payload.get("base_total") or _sum_amount_from_lines(lines))
    latest_total = float(payload.get("latest_total") or base_total)
    delta_total = float(payload.get("delta_total") or (latest_total - base_total))
    cloud_quote_name = str(payload.get("cloud_quote_name") or "").strip() or None

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO relay_quotes (
                quote_id, cloud_quote_name, pos_profile_id, created_by, customer_id, customer_name,
                currency, base_total, latest_total, delta_total, valid_until, status,
                converted_token_id, converted_local_sale_ref,
                source_origin, source_env, source_user_agent, payload, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(quote_id) DO UPDATE SET
                cloud_quote_name=excluded.cloud_quote_name,
                pos_profile_id=excluded.pos_profile_id,
                created_by=excluded.created_by,
                customer_id=excluded.customer_id,
                customer_name=excluded.customer_name,
                currency=excluded.currency,
                base_total=excluded.base_total,
                latest_total=excluded.latest_total,
                delta_total=excluded.delta_total,
                valid_until=excluded.valid_until,
                status=excluded.status,
                source_origin=excluded.source_origin,
                source_env=excluded.source_env,
                source_user_agent=excluded.source_user_agent,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            (
                quote_id,
                cloud_quote_name,
                pos_profile_id,
                created_by,
                customer_id,
                customer_name,
                currency,
                base_total,
                latest_total,
                delta_total,
                valid_until,
                status,
                source["source_origin"],
                source["source_env"],
                source["source_user_agent"],
                _dumps(payload),
                now,
                now,
            ),
        )
        conn.execute("DELETE FROM relay_quote_lines WHERE quote_id = ?", (quote_id,))
        for line in lines:
            conn.execute(
                """
                INSERT INTO relay_quote_lines (
                    quote_id, item_code, item_name, qty, uom, rate, amount, conversion_factor,
                    payload, source_origin, source_env, source_user_agent, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    quote_id,
                    line["item_code"],
                    line["item_name"],
                    line["qty"],
                    line["uom"],
                    line["rate"],
                    line["amount"],
                    line["conversion_factor"],
                    _dumps(line["payload"]),
                    source["source_origin"],
                    source["source_env"],
                    source["source_user_agent"],
                    now,
                    now,
                ),
            )

    return get_local_quote(quote_id)


def get_local_quote(quote_id):
    quote_id = str(quote_id or "").strip()
    if not quote_id:
        return None
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT quote_id, cloud_quote_name, pos_profile_id, created_by, customer_id, customer_name,
                   currency, base_total, latest_total, delta_total, valid_until, status,
                   converted_token_id, converted_local_sale_ref,
                   source_origin, source_env, source_user_agent, payload, created_at, updated_at
            FROM relay_quotes
            WHERE quote_id = ?
            """,
            (quote_id,),
        ).fetchone()
        if not row:
            return None
        line_rows = conn.execute(
            """
            SELECT id, quote_id, item_code, item_name, qty, uom, rate, amount, conversion_factor, payload, created_at, updated_at
            FROM relay_quote_lines
            WHERE quote_id = ?
            ORDER BY id ASC
            """,
            (quote_id,),
        ).fetchall()
    out = dict(row)
    out["payload"] = _loads(out.get("payload"))
    out["lines"] = []
    for line in line_rows:
        item = dict(line)
        item["payload"] = _loads(item.get("payload"))
        out["lines"].append(item)
    return out


def list_local_quotes(
    pos_profile_id=None,
    search=None,
    statuses=None,
    limit=100,
    max_age_days=7,
    allow_stale=False,
    history_days=30,
):
    max_age_days = max(0, int(max_age_days or 7))
    allow_stale = bool(allow_stale)
    history_days = max(max_age_days, int(history_days or 30))
    lookback_days = history_days if allow_stale else max_age_days
    cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat(timespec="seconds") + "Z"

    query = """
        SELECT quote_id, cloud_quote_name, pos_profile_id, created_by, customer_id, customer_name,
               currency, base_total, latest_total, delta_total, valid_until, status,
               converted_token_id, converted_local_sale_ref,
               source_origin, source_env, source_user_agent, payload, created_at, updated_at
        FROM relay_quotes
        WHERE created_at >= ?
    """
    params = [cutoff]
    if pos_profile_id:
        query += " AND pos_profile_id = ?"
        params.append(pos_profile_id)
    statuses = [str(s).strip().upper() for s in (statuses or []) if str(s).strip()]
    if statuses:
        query += " AND status IN ({})".format(",".join(["?"] * len(statuses)))
        params.extend(statuses)
    if search:
        like = f"%{str(search).strip()}%"
        query += """
            AND (
                quote_id LIKE ?
                OR cloud_quote_name LIKE ?
                OR customer_id LIKE ?
                OR customer_name LIKE ?
            )
        """
        params.extend([like, like, like, like])
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(int(limit))

    with get_db() as conn:
        rows = [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]

    now_dt = datetime.utcnow()
    out = []
    for row in rows:
        created_dt = _parse_iso_utc(row.get("created_at"))
        age_days = max(0, (now_dt - created_dt.replace(tzinfo=None)).days) if created_dt else 0
        is_stale = 1 if age_days > max_age_days else 0
        if (not allow_stale) and is_stale:
            continue
        valid_until = _parse_iso_utc(row.get("valid_until")) if row.get("valid_until") else None
        is_expired = 1 if (valid_until and valid_until.replace(tzinfo=None).date() < datetime.utcnow().date()) else 0
        row["order_age_days"] = age_days
        row["is_stale"] = is_stale
        row["is_expired"] = is_expired
        row["stale_policy_allow"] = 1 if allow_stale else 0
        row["stale_policy_max_age_days"] = max_age_days
        row["stale_policy_history_days"] = history_days
        out.append(row)
    return out


def preview_local_quote_reprice(quote_id):
    quote = get_local_quote(quote_id)
    if not quote:
        return {"ok": False, "code": "QUOTE_NOT_FOUND"}
    lines = quote.get("lines") or []
    old_total = 0.0
    new_total = 0.0
    repriced_lines = []
    with get_db() as conn:
        for line in lines:
            item_code = str(line.get("item_code") or "").strip()
            qty = float(line.get("qty") or 0)
            old_rate = float(line.get("rate") or 0)
            old_amount = float(line.get("amount") or (qty * old_rate))
            item_row = conn.execute(
                "SELECT rate FROM relay_items_cache WHERE item_code = ?",
                (item_code,),
            ).fetchone()
            latest_rate = float(item_row["rate"]) if item_row and item_row["rate"] is not None else old_rate
            new_amount = float(qty * latest_rate)
            old_total += old_amount
            new_total += new_amount
            repriced_lines.append(
                {
                    "line_id": line.get("id"),
                    "item_code": item_code,
                    "item_name": line.get("item_name") or "",
                    "qty": qty,
                    "uom": line.get("uom") or "",
                    "old_rate": old_rate,
                    "new_rate": latest_rate,
                    "delta_rate": float(latest_rate - old_rate),
                    "old_amount": old_amount,
                    "new_amount": new_amount,
                    "delta_amount": float(new_amount - old_amount),
                }
            )
    return {
        "ok": True,
        "quote_id": quote.get("quote_id"),
        "old_total": float(old_total),
        "new_total": float(new_total),
        "delta_total": float(new_total - old_total),
        "valid_till": quote.get("valid_until") or "",
        "is_expired": 1 if str(quote.get("status") or "").upper() == "EXPIRED" else 0,
        "repriced_lines": repriced_lines,
    }


def convert_local_quote_to_token(
    quote_id,
    cashier_user_id=None,
    role=None,
    confirm_reprice=True,
    source_meta=None,
):
    quote = get_local_quote(quote_id)
    if not quote:
        return {"ok": False, "code": "QUOTE_NOT_FOUND"}

    if str(quote.get("status") or "").upper() == "CONVERTED":
        token_id = str(quote.get("converted_token_id") or "").strip()
        token = get_token(token_id) if token_id else None
        return {"ok": True, "idempotent_replay": True, "token": token, "quote": quote}

    valid_until = _parse_iso_utc(quote.get("valid_until"))
    if valid_until and valid_until.replace(tzinfo=None).date() < datetime.utcnow().date():
        with get_db() as conn:
            conn.execute(
                "UPDATE relay_quotes SET status = 'EXPIRED', updated_at = ? WHERE quote_id = ?",
                (_now_iso(), quote_id),
            )
        return {"ok": False, "code": "QUOTE_EXPIRED", "message": "Quotation is expired"}

    preview = preview_local_quote_reprice(quote_id)
    if not preview.get("ok"):
        return preview
    if abs(float(preview.get("delta_total") or 0)) > 0.0001 and not bool(confirm_reprice):
        return {"ok": False, "code": "QUOTE_REPRICE_CONFIRM_REQUIRED", "preview": preview}

    line_rows = quote.get("lines") or []
    new_rate_by_id = {int(r.get("line_id")): float(r.get("new_rate") or 0) for r in preview.get("repriced_lines") or []}
    token_lines = []
    for line in line_rows:
        lid = int(line.get("id") or 0)
        qty = float(line.get("qty") or 0)
        new_rate = float(new_rate_by_id.get(lid, line.get("rate") or 0))
        token_lines.append(
            {
                "item_code": line.get("item_code") or "",
                "item_name": line.get("item_name") or "",
                "qty": qty,
                "uom": line.get("uom") or "",
                "rate": new_rate,
                "amount": float(qty * new_rate),
                "conversion_factor": float(line.get("conversion_factor") or 1),
            }
        )

    token_payload = {
        "pos_profile_id": quote.get("pos_profile_id") or "",
        "cashier_user_id": str(cashier_user_id or quote.get("created_by") or "").strip(),
        "customer_id": quote.get("customer_id") or "",
        "customer_name": quote.get("customer_name") or "",
        "role": str(role or "").strip(),
        "source_doctype": "Quotation",
        "source_name": quote.get("cloud_quote_name") or quote.get("quote_id"),
        "items": token_lines,
    }
    token = create_token(token_payload, source_meta=source_meta)

    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_quotes
            SET status = 'CONVERTED',
                converted_token_id = ?,
                latest_total = ?,
                delta_total = ?,
                updated_at = ?
            WHERE quote_id = ?
            """,
            (
                token.get("token_id"),
                float(preview.get("new_total") or 0),
                float(preview.get("delta_total") or 0),
                _now_iso(),
                quote_id,
            ),
        )

    return {
        "ok": True,
        "quote_id": quote_id,
        "token": token,
        "preview": preview,
    }


def create_token(payload, expiry_minutes=120, source_meta=None):
    now = _now_iso()
    token_id = (payload or {}).get("token_id") or _generate_token_id()
    pos_profile_id = (payload or {}).get("pos_profile_id") or ""
    if not pos_profile_id:
        raise ValueError("pos_profile_id is required")
    source = _normalize_source_meta(source_meta)

    from datetime import datetime as _dt, timedelta

    expires_at = (_dt.utcnow() + timedelta(minutes=max(1, int(expiry_minutes)))).isoformat(timespec="seconds") + "Z"
    lines = (payload or {}).get("items") or (payload or {}).get("lines") or []

    with get_db() as conn:
        existing = conn.execute(
            """
            SELECT token_id, status, expires_at
            FROM relay_tokens
            WHERE token_id = ?
            """,
            (token_id,),
        ).fetchone()

        if existing:
            # idempotent behavior for token creation retries
            if existing["status"] in ("TOKEN_OPEN", "TOKEN_EXPIRED"):
                conn.execute(
                    """
                    UPDATE relay_tokens
                    SET pos_profile_id = ?, cashier_user_id = ?, customer_id = ?, customer_name = ?,
                        source_origin = ?, source_env = ?, source_user_agent = ?,
                        status = 'TOKEN_OPEN', expires_at = ?, updated_at = ?,
                        void_reason = NULL, voided_by = NULL, consumed_sale_ref = NULL, consumed_at = NULL
                    WHERE token_id = ?
                    """,
                    (
                        pos_profile_id,
                        (payload or {}).get("cashier_user_id"),
                        (payload or {}).get("customer_id"),
                        (payload or {}).get("customer_name"),
                        source["source_origin"],
                        source["source_env"],
                        source["source_user_agent"],
                        expires_at,
                        now,
                        token_id,
                    ),
                )
                conn.execute(
                    """
                    DELETE FROM relay_token_lines WHERE token_id = ?
                    """,
                    (token_id,),
                )
            else:
                # TOKEN_PAID / TOKEN_VOID should not be recreated
                raise ValueError(f"Token {token_id} already exists with status {existing['status']}")
        else:
            conn.execute(
                """
                INSERT INTO relay_tokens (
                    token_id, pos_profile_id, cashier_user_id, customer_id, customer_name,
                    source_origin, source_env, source_user_agent,
                    status, expires_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'TOKEN_OPEN', ?, ?, ?)
                """,
                (
                    token_id,
                    pos_profile_id,
                    (payload or {}).get("cashier_user_id"),
                    (payload or {}).get("customer_id"),
                    (payload or {}).get("customer_name"),
                    source["source_origin"],
                    source["source_env"],
                    source["source_user_agent"],
                    expires_at,
                    now,
                    now,
                ),
            )

        for line in lines:
            qty = float((line or {}).get("qty") or 0)
            rate = float((line or {}).get("rate") or 0)
            amount = float((line or {}).get("amount") or (qty * rate))
            conn.execute(
                """
                INSERT INTO relay_token_lines (
                    token_id, item_code, item_name, qty, uom, rate, amount, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token_id,
                    (line or {}).get("item_code") or "",
                    (line or {}).get("item_name") or "",
                    qty,
                    (line or {}).get("uom"),
                    rate,
                    amount,
                    _dumps(line),
                    now,
                ),
            )

    return {
        "token_id": token_id,
        "status": "TOKEN_OPEN",
        "expires_at": expires_at,
        "items": lines,
        "source_origin": source["source_origin"],
        "source_env": source["source_env"],
        "source_user_agent": source["source_user_agent"],
    }


def get_token(token_id):
    now = _now_iso()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT token_id, pos_profile_id, cashier_user_id, customer_id, customer_name,
                   source_origin, source_env, source_user_agent,
                   status, expires_at, void_reason, voided_by, consumed_sale_ref,
                   consumed_at, created_at, updated_at
            FROM relay_tokens
            WHERE token_id = ?
            """,
            (token_id,),
        ).fetchone()

        if not row:
            return None

        token = dict(row)
        # Auto-expire if needed
        if token.get("status") == "TOKEN_OPEN" and token.get("expires_at") and token.get("expires_at") < now:
            conn.execute(
                """
                UPDATE relay_tokens
                SET status = 'TOKEN_EXPIRED', updated_at = ?
                WHERE token_id = ?
                """,
                (now, token_id),
            )
            token["status"] = "TOKEN_EXPIRED"
            token["updated_at"] = now

        lines = conn.execute(
            """
            SELECT item_code, item_name, qty, uom, rate, amount, payload
            FROM relay_token_lines
            WHERE token_id = ?
            ORDER BY id ASC
            """,
            (token_id,),
        ).fetchall()

        token["items"] = [
            {
                "item_code": line["item_code"],
                "item_name": line["item_name"],
                "qty": line["qty"],
                "uom": line["uom"],
                "rate": line["rate"],
                "amount": line["amount"],
                "payload": _loads(line["payload"]),
            }
            for line in lines
        ]
        return token


def void_token(token_id, supervisor_user_id=None, reason=None):
    now = _now_iso()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT status FROM relay_tokens WHERE token_id = ?
            """,
            (token_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "code": "TOKEN_NOT_FOUND"}

        current = row["status"]
        if current == "TOKEN_PAID":
            return {"ok": False, "code": "TOKEN_ALREADY_PAID"}
        if current == "TOKEN_VOID":
            return {"ok": True, "status": "TOKEN_VOID"}

        conn.execute(
            """
            UPDATE relay_tokens
            SET status = 'TOKEN_VOID', void_reason = ?, voided_by = ?, updated_at = ?
            WHERE token_id = ?
            """,
            (reason or "", supervisor_user_id or "", now, token_id),
        )
        return {"ok": True, "status": "TOKEN_VOID"}


def open_cashier_session(payload, source_meta=None):
    now = _now_iso()
    session_id = (payload or {}).get("session_id") or _generate_session_id()
    pos_profile_id = (payload or {}).get("pos_profile_id") or ""
    cashier_user_id = (payload or {}).get("cashier_user_id") or ""
    device_id = (payload or {}).get("device_id") or ""

    if not pos_profile_id or not cashier_user_id:
        raise ValueError("pos_profile_id and cashier_user_id are required")
    source = _normalize_source_meta(source_meta)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO relay_cashier_sessions (
                session_id, pos_profile_id, cashier_user_id, device_id,
                source_origin, source_env, source_user_agent,
                status, opened_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
            """,
            (
                session_id,
                pos_profile_id,
                cashier_user_id,
                device_id,
                source["source_origin"],
                source["source_env"],
                source["source_user_agent"],
                now,
                now,
                now,
            ),
        )

    return {
        "session_id": session_id,
        "status": "OPEN",
        "opened_at": now,
        "pos_profile_id": pos_profile_id,
        "cashier_user_id": cashier_user_id,
        "device_id": device_id,
        "source_origin": source["source_origin"],
        "source_env": source["source_env"],
        "source_user_agent": source["source_user_agent"],
    }


def close_cashier_session(session_id, close_note=None):
    now = _now_iso()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT session_id, status FROM relay_cashier_sessions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "code": "SESSION_NOT_FOUND"}

        if row["status"] == "CLOSED":
            return {"ok": True, "status": "CLOSED"}

        conn.execute(
            """
            UPDATE relay_cashier_sessions
            SET status = 'CLOSED', closed_at = ?, close_note = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (now, close_note or "", now, session_id),
        )
        return {"ok": True, "status": "CLOSED", "closed_at": now}


def upsert_customer(payload):
    now = _now_iso()
    customer_id = (payload or {}).get("customer_id") or (payload or {}).get("name")
    if not customer_id:
        raise ValueError("customer_id is required")

    customer_name = (payload or {}).get("customer_name") or (payload or {}).get("customer_id")
    mobile_no = (payload or {}).get("mobile_no") or ""
    email_id = (payload or {}).get("email_id") or ""
    tax_id = (payload or {}).get("tax_id") or ""

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO relay_customers (
                customer_id, customer_name, mobile_no, email_id, tax_id,
                payload, updated_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(customer_id) DO UPDATE SET
                customer_name=excluded.customer_name,
                mobile_no=excluded.mobile_no,
                email_id=excluded.email_id,
                tax_id=excluded.tax_id,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            (
                customer_id,
                customer_name,
                mobile_no,
                email_id,
                tax_id,
                _dumps(payload),
                now,
                now,
            ),
        )

    return {
        "customer_id": customer_id,
        "customer_name": customer_name,
    }


def refresh_items_cache(items):
    now = _now_iso()
    rows = items or []
    with get_db() as conn:
        for item in rows:
            item_code = (item or {}).get("item_code") or (item or {}).get("name")
            if not item_code:
                continue

            barcode = ""
            barcodes = (item or {}).get("item_barcode") or []
            if barcodes:
                first = barcodes[0]
                if isinstance(first, dict):
                    barcode = first.get("barcode") or ""
                elif isinstance(first, str):
                    barcode = first

            conn.execute(
                """
                INSERT INTO relay_items_cache (
                    item_code, item_name, stock_uom, barcode, rate,
                    payload, updated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_code) DO UPDATE SET
                    item_name=excluded.item_name,
                    stock_uom=excluded.stock_uom,
                    barcode=excluded.barcode,
                    rate=excluded.rate,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (
                    item_code,
                    (item or {}).get("item_name") or "",
                    (item or {}).get("stock_uom") or "",
                    barcode,
                    float((item or {}).get("rate") or 0),
                    _dumps(item),
                    now,
                    now,
                ),
            )

    return {"count": len(rows)}


def search_items_cache(query=None, limit=50):
    q = (query or "").strip()
    like = f"%{q}%"
    with get_db() as conn:
        if q:
            cur = conn.execute(
                """
                SELECT item_code, item_name, stock_uom, barcode, rate, payload, updated_at
                FROM relay_items_cache
                WHERE item_code LIKE ? OR item_name LIKE ? OR barcode LIKE ?
                ORDER BY item_name ASC
                LIMIT ?
                """,
                (like, like, like, int(limit)),
            )
        else:
            cur = conn.execute(
                """
                SELECT item_code, item_name, stock_uom, barcode, rate, payload, updated_at
                FROM relay_items_cache
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (int(limit),),
            )
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            row["payload"] = _loads(row.get("payload"))
        return rows


def enqueue_outbox_event(event_type, payload, idempotency_key=None, local_ref=None, source_meta=None):
    now = _now_iso()
    event_id = uuid.uuid4().hex
    source = _normalize_source_meta(source_meta)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO relay_outbox (
                event_id, event_type, idempotency_key, local_ref, payload,
                source_origin, source_env, source_user_agent,
                status, retries, next_attempt_at, last_error, cloud_ref,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0, ?, NULL, NULL, ?, ?)
            """,
            (
                event_id,
                event_type,
                idempotency_key,
                local_ref,
                _dumps(payload),
                source["source_origin"],
                source["source_env"],
                source["source_user_agent"],
                now,
                now,
                now,
            ),
        )
    return event_id


def list_outbox(limit=200):
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT event_id, event_type, idempotency_key, local_ref, payload,
                   source_origin, source_env, source_user_agent,
                   status, retries, next_attempt_at, last_error, cloud_ref,
                   created_at, updated_at
            FROM relay_outbox
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            row["payload"] = _loads(row.get("payload"))
        return rows


def cleanup_outbox_rows(
    limit=200,
    statuses=None,
    event_types=None,
    created_before=None,
    error_contains=None,
    local_ref_contains=None,
    delete=False,
):
    statuses = [str(s).strip() for s in (statuses or []) if str(s).strip()]
    event_types = [str(s).strip() for s in (event_types or []) if str(s).strip()]
    created_before = str(created_before or "").strip()
    error_contains = str(error_contains or "").strip()
    local_ref_contains = str(local_ref_contains or "").strip()

    where = []
    params = []
    if statuses:
        where.append("status IN ({})".format(",".join(["?"] * len(statuses))))
        params.extend(statuses)
    if event_types:
        where.append("event_type IN ({})".format(",".join(["?"] * len(event_types))))
        params.extend(event_types)
    if created_before:
        where.append("created_at < ?")
        params.append(created_before)
    if error_contains:
        where.append("COALESCE(last_error, '') LIKE ?")
        params.append(f"%{error_contains}%")
    if local_ref_contains:
        where.append("COALESCE(local_ref, '') LIKE ?")
        params.append(f"%{local_ref_contains}%")

    where_sql = " WHERE " + " AND ".join(where) if where else ""

    with get_db() as conn:
        cur = conn.execute(
            f"""
            SELECT event_id, event_type, idempotency_key, local_ref, payload,
                   source_origin, source_env, source_user_agent,
                   status, retries, next_attempt_at, last_error, cloud_ref,
                   created_at, updated_at
            FROM relay_outbox
            {where_sql}
            ORDER BY created_at ASC
            LIMIT ?
            """,
            tuple(params + [int(limit)]),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            row["payload"] = _loads(row.get("payload"))

        deleted = 0
        if delete and rows:
            conn.executemany(
                "DELETE FROM relay_outbox WHERE event_id = ?",
                [(r["event_id"],) for r in rows],
            )
            deleted = len(rows)

    return {
        "rows": rows,
        "matched": len(rows),
        "deleted": deleted,
        "dry_run": not bool(delete),
        "filters": {
            "statuses": statuses,
            "event_types": event_types,
            "created_before": created_before,
            "error_contains": error_contains,
            "local_ref_contains": local_ref_contains,
            "limit": int(limit),
        },
    }


def outbox_counts():
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT status, COUNT(*) as cnt
            FROM relay_outbox
            GROUP BY status
            """
        )
        raw = {r["status"]: r["cnt"] for r in cur.fetchall()}
    return {
        "queued": int(raw.get("queued", 0)),
        "processing": int(raw.get("processing", 0)),
        "done": int(raw.get("done", 0)),
        "failed": int(raw.get("failed", 0)),
        "total": sum(int(v) for v in raw.values()) if raw else 0,
    }


def _outbox_backoff_seconds(retries):
    retry_num = max(0, int(retries or 0))
    base = min(300, 2 ** retry_num)
    return max(1, base)


def get_next_queued_outbox_event(now_iso=None):
    now_iso = now_iso or _now_iso()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT event_id, event_type, idempotency_key, local_ref, payload,
                   source_origin, source_env, source_user_agent,
                   status, retries, next_attempt_at, last_error, cloud_ref,
                   created_at, updated_at
            FROM relay_outbox
            WHERE status = 'queued' AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (now_iso,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["payload"] = _loads(data.get("payload"))
        return data


def mark_outbox_processing(event_id):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_outbox
            SET status = 'processing', updated_at = ?
            WHERE event_id = ?
            """,
            (_now_iso(), event_id),
        )


def mark_outbox_done(event_id, cloud_ref=None):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_outbox
            SET status = 'done', last_error = NULL, cloud_ref = COALESCE(?, cloud_ref), updated_at = ?
            WHERE event_id = ?
            """,
            (cloud_ref, _now_iso(), event_id),
        )


def mark_outbox_failed(event_id, error, retry_later=True):
    now = datetime.utcnow()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT retries FROM relay_outbox WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()
        retries = int(row["retries"]) + 1 if row else 1
        backoff_seconds = _outbox_backoff_seconds(retries) if retry_later else 0
        next_attempt_at = (
            (now.timestamp() + backoff_seconds)
            if retry_later
            else now.timestamp()
        )
        from datetime import datetime as _dt

        next_iso = _dt.utcfromtimestamp(next_attempt_at).isoformat(timespec="seconds") + "Z"
        next_status = "queued" if retry_later else "failed"
        conn.execute(
            """
            UPDATE relay_outbox
            SET status = ?, retries = ?, last_error = ?, next_attempt_at = ?, updated_at = ?
            WHERE event_id = ?
            """,
            (next_status, retries, str(error)[:1000], next_iso, _now_iso(), event_id),
        )


def commit_invoice_atomic(payload, source_meta=None):
    now = _now_iso()
    payload = payload or {}
    source = _normalize_source_meta(source_meta)
    token_id = payload.get("token_id")
    idempotency_key = (payload.get("idempotency_key") or "").strip()
    pos_profile_id = (payload.get("pos_profile_id") or "").strip()
    cashier_user_id = (payload.get("cashier_user_id") or "").strip()
    cashier_session_id = (payload.get("cashier_session_id") or "").strip() or None
    device_id = (payload.get("device_id") or "").strip() or None
    invoice_payload = payload.get("invoice") or {}
    data_payload = payload.get("data") or {}

    if not idempotency_key:
        return {"ok": False, "code": "IDEMPOTENCY_KEY_REQUIRED", "message": "idempotency_key is required"}
    if not pos_profile_id:
        return {"ok": False, "code": "POS_PROFILE_REQUIRED", "message": "pos_profile_id is required"}

    with get_db() as conn:
        existing_idem = conn.execute(
            """
            SELECT local_sale_ref, response_payload
            FROM relay_idempotency
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
        if existing_idem:
            return {
                "ok": True,
                "idempotent_replay": True,
                "local_sale_ref": existing_idem["local_sale_ref"],
                "result": _loads(existing_idem["response_payload"]),
            }

        if token_id:
            token_row = conn.execute(
                """
                SELECT token_id, status, consumed_sale_ref
                FROM relay_tokens
                WHERE token_id = ?
                """,
                (token_id,),
            ).fetchone()
            if not token_row:
                return {"ok": False, "code": "TOKEN_NOT_FOUND", "message": "Token not found"}

            token_status = token_row["status"]
            if token_status == "TOKEN_PAID":
                return {
                    "ok": False,
                    "code": "TOKEN_ALREADY_PAID",
                    "message": "Token already paid",
                    "local_sale_ref": token_row["consumed_sale_ref"],
                }
            if token_status in ("TOKEN_VOID", "TOKEN_EXPIRED"):
                return {
                    "ok": False,
                    "code": token_status,
                    "message": f"Token state is {token_status}",
                }

        local_sale_ref = _generate_local_sale_ref(pos_profile_id)
        total = float(invoice_payload.get("grand_total") or invoice_payload.get("total") or 0)
        net_total = float(invoice_payload.get("net_total") or 0)
        customer_id = invoice_payload.get("customer") or payload.get("customer_id") or ""
        customer_name = invoice_payload.get("customer_name") or payload.get("customer_name") or ""

        conn.execute(
            """
            INSERT INTO relay_local_sales (
                local_sale_ref, token_id, pos_profile_id, cashier_user_id,
                cashier_session_id, device_id, idempotency_key,
                sale_status, pick_status, dispatch_status, paid,
                total, net_total, customer_id, customer_name,
                invoice_payload, data_payload,
                cloud_sync_status, source_origin, source_env, source_user_agent, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'SALE_COMMITTED_LOCAL', 'PAID_PENDING_PICK', 'PENDING', 1,
                      ?, ?, ?, ?, ?, ?, 'SALE_SYNC_PENDING', ?, ?, ?, ?, ?)
            """,
            (
                local_sale_ref,
                token_id,
                pos_profile_id,
                cashier_user_id,
                cashier_session_id,
                device_id,
                idempotency_key,
                total,
                net_total,
                customer_id,
                customer_name,
                _dumps(invoice_payload),
                _dumps(data_payload),
                source["source_origin"],
                source["source_env"],
                source["source_user_agent"],
                now,
                now,
            ),
        )

        items = invoice_payload.get("items") or []
        for line in items:
            qty = float((line or {}).get("qty") or 0)
            rate = float((line or {}).get("rate") or 0)
            amount = float((line or {}).get("amount") or (qty * rate))
            conn.execute(
                """
                INSERT INTO relay_local_sale_lines (
                    local_sale_ref, item_code, item_name, qty, uom, rate, amount,
                    line_status, pick_status, payload, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PAID_PENDING_PICK', 'PAID_PENDING_PICK', ?, ?, ?)
                """,
                (
                    local_sale_ref,
                    (line or {}).get("item_code") or "",
                    (line or {}).get("item_name") or "",
                    qty,
                    (line or {}).get("uom") or "",
                    rate,
                    amount,
                    _dumps(line),
                    now,
                    now,
                ),
            )

        if token_id:
            conn.execute(
                """
                UPDATE relay_tokens
                SET status = 'TOKEN_PAID', consumed_sale_ref = ?, consumed_at = ?, updated_at = ?
                WHERE token_id = ? AND status = 'TOKEN_OPEN'
                """,
                (local_sale_ref, now, now, token_id),
            )
            if conn.total_changes == 0:
                token_row = conn.execute(
                    """
                    SELECT consumed_sale_ref FROM relay_tokens WHERE token_id = ?
                    """,
                    (token_id,),
                ).fetchone()
                return {
                    "ok": False,
                    "code": "TOKEN_ALREADY_PAID",
                    "message": "Token already paid",
                    "local_sale_ref": token_row["consumed_sale_ref"] if token_row else None,
                }

        result_payload = {
            "local_sale_ref": local_sale_ref,
            "sale_status": "SALE_COMMITTED_LOCAL",
            "pick_status": "PAID_PENDING_PICK",
            "dispatch_status": "PENDING",
            "cloud_sync_status": "SALE_SYNC_PENDING",
        }

        conn.execute(
            """
            INSERT INTO relay_idempotency (
                idempotency_key, token_id, local_sale_ref, request_hash,
                response_payload, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idempotency_key,
                token_id,
                local_sale_ref,
                "",
                _dumps(result_payload),
                now,
                now,
            ),
        )

    return {
        "ok": True,
        "idempotent_replay": False,
        "local_sale_ref": local_sale_ref,
        "result": result_payload,
    }


def update_pick_status(local_sale_ref, picking_status, picker_user_id=None, notes=None, payload=None, source_meta=None):
    now = _now_iso()
    source = _normalize_source_meta(source_meta)
    allowed = {
        "PAID_PENDING_PICK",
        "PICK_IN_PROGRESS",
        "PICK_EXCEPTION",
        "PICKED_READY_FOR_RELEASE",
    }
    if picking_status not in allowed:
        return {"ok": False, "code": "INVALID_PICK_STATUS"}

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT local_sale_ref, dispatch_status FROM relay_local_sales WHERE local_sale_ref = ?
            """,
            (local_sale_ref,),
        ).fetchone()
        if not row:
            return {"ok": False, "code": "SALE_NOT_FOUND"}

        if row["dispatch_status"] == "RELEASED":
            return {"ok": False, "code": "ALREADY_RELEASED"}

        # Persist line-wise pick quantities/status in each line payload so picker edits
        # survive refresh/offline operation without changing billed invoice line values.
        payload_obj = payload if isinstance(payload, dict) else {}
        line_updates = payload_obj.get("line_updates") if isinstance(payload_obj.get("line_updates"), list) else []
        if line_updates:
            line_rows = conn.execute(
                """
                SELECT id, qty, uom, pick_status, payload
                FROM relay_local_sale_lines
                WHERE local_sale_ref = ?
                """,
                (local_sale_ref,),
            ).fetchall()
            line_map = {int(r["id"]): r for r in line_rows}

            for line_update in line_updates:
                if not isinstance(line_update, dict):
                    continue
                try:
                    line_id = int(line_update.get("line_id") or line_update.get("id"))
                except Exception:
                    line_id = 0
                if not line_id or line_id not in line_map:
                    continue

                line_row = line_map[line_id]
                existing_payload = _loads(line_row["payload"]) if line_row["payload"] else {}
                if not isinstance(existing_payload, dict):
                    existing_payload = {}

                ordered_qty = float(line_row["qty"] or 0)
                ordered_uom = (line_row["uom"] or "").strip()
                try:
                    picked_qty = float(line_update.get("picked_qty") if line_update.get("picked_qty") is not None else ordered_qty)
                except Exception:
                    picked_qty = ordered_qty

                if picked_qty < 0:
                    picked_qty = 0.0

                try:
                    conversion_factor = float(
                        line_update.get("conversion_factor")
                        if line_update.get("conversion_factor") is not None
                        else (
                            (existing_payload or {}).get("conversion_factor")
                            or 1
                        )
                    )
                except Exception:
                    conversion_factor = 1.0
                if not conversion_factor:
                    conversion_factor = 1.0

                try:
                    picked_stock_qty = float(
                        line_update.get("picked_stock_qty")
                        if line_update.get("picked_stock_qty") is not None
                        else picked_qty * conversion_factor
                    )
                except Exception:
                    picked_stock_qty = picked_qty * conversion_factor

                line_pick_status = (
                    str(line_update.get("pick_status") or "").strip().upper()
                    or ("PICKED" if abs(picked_qty - ordered_qty) < 1e-9 else "PARTIAL")
                )
                line_note = str(line_update.get("note") or line_update.get("notes") or "").strip()

                picker_snapshot = existing_payload.get("picker") if isinstance(existing_payload.get("picker"), dict) else {}
                picker_snapshot.update(
                    {
                        "ordered_qty": ordered_qty,
                        "ordered_uom": ordered_uom,
                        "picked_qty": picked_qty,
                        "picked_uom": str(line_update.get("picked_uom") or ordered_uom).strip(),
                        "conversion_factor": conversion_factor,
                        "picked_stock_qty": picked_stock_qty,
                        "pick_status": line_pick_status,
                        "note": line_note,
                        "updated_at": now,
                    }
                )
                existing_payload["picker"] = picker_snapshot

                conn.execute(
                    """
                    UPDATE relay_local_sale_lines
                    SET pick_status = ?, line_status = ?, payload = ?, updated_at = ?
                    WHERE id = ? AND local_sale_ref = ?
                    """,
                    (
                        line_pick_status,
                        picking_status,
                        _dumps(existing_payload),
                        now,
                        line_id,
                        local_sale_ref,
                    ),
                )

        conn.execute(
            """
            UPDATE relay_local_sales
            SET pick_status = ?, updated_at = ?
            WHERE local_sale_ref = ?
            """,
            (picking_status, now, local_sale_ref),
        )
        conn.execute(
            """
            INSERT INTO relay_pick_events (
                local_sale_ref, picker_user_id, event_type, notes, payload,
                source_origin, source_env, source_user_agent, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                local_sale_ref,
                picker_user_id or "",
                picking_status,
                notes or "",
                _dumps(payload),
                source["source_origin"],
                source["source_env"],
                source["source_user_agent"],
                now,
            ),
        )

    return {"ok": True, "local_sale_ref": local_sale_ref, "pick_status": picking_status}


def _normalize_line_snapshot(rows):
    snapshot_rows = rows if isinstance(rows, list) else []
    cleaned = []
    for row in snapshot_rows:
        if not isinstance(row, dict):
            continue
        line_id_raw = row.get("line_id")
        if line_id_raw is None:
            line_id_raw = row.get("id")
        try:
            line_id = int(line_id_raw)
        except Exception:
            line_id = 0
        item_code = str(row.get("item_code") or "").strip()[:140]
        item_name = str(row.get("item_name") or "").strip()[:240]
        try:
            ordered_qty = float(row.get("ordered_qty") or row.get("qty") or 0)
        except Exception:
            ordered_qty = 0.0
        try:
            picked_qty = float(row.get("picked_qty") or 0)
        except Exception:
            picked_qty = 0.0
        ordered_uom = str(row.get("ordered_uom") or row.get("uom") or "").strip()[:40]
        picked_uom = str(row.get("picked_uom") or ordered_uom or "").strip()[:40]
        try:
            conversion_factor = float(row.get("conversion_factor") or 1)
        except Exception:
            conversion_factor = 1.0
        try:
            picked_stock_qty = float(row.get("picked_stock_qty") or (picked_qty * conversion_factor))
        except Exception:
            picked_stock_qty = picked_qty * conversion_factor
        pick_status = str(row.get("pick_status") or "").strip().upper()[:60]
        if line_id <= 0 and not item_code:
            continue
        cleaned.append(
            {
                "line_id": line_id,
                "item_code": item_code,
                "item_name": item_name,
                "ordered_qty": ordered_qty,
                "ordered_uom": ordered_uom,
                "picked_qty": picked_qty,
                "picked_uom": picked_uom,
                "conversion_factor": conversion_factor,
                "picked_stock_qty": picked_stock_qty,
                "pick_status": pick_status,
            }
        )
    return cleaned


def release_sale(local_sale_ref, dispatcher_user_id=None, allow_partial=False, notes=None, payload=None, source_meta=None):
    now = _now_iso()
    source = _normalize_source_meta(source_meta)
    payload_obj = payload if isinstance(payload, dict) else {}
    proof_ack_name = str(payload_obj.get("proof_ack_name") or "").strip()[:140]
    proof_mode = str(payload_obj.get("proof_mode") or "").strip().lower()
    proof_ref_no = str(payload_obj.get("proof_ref_no") or "").strip()[:120]
    proof_notes = str(payload_obj.get("proof_notes") or payload_obj.get("notes") or "").strip()[:500]
    line_snapshot = _normalize_line_snapshot(payload_obj.get("line_snapshot"))
    line_summary = payload_obj.get("line_summary") if isinstance(payload_obj.get("line_summary"), dict) else {}

    if not proof_ack_name:
        return {"ok": False, "code": "DISPATCH_PROOF_ACK_REQUIRED", "message": "proof_ack_name is required"}
    if proof_mode not in ("counter", "delivery", "other"):
        return {
            "ok": False,
            "code": "DISPATCH_PROOF_MODE_REQUIRED",
            "message": "proof_mode must be one of counter|delivery|other",
        }
    if not line_snapshot:
        return {"ok": False, "code": "DISPATCH_LINE_SNAPSHOT_REQUIRED", "message": "line_snapshot is required"}

    proof_payload = {
        "ack_name": proof_ack_name,
        "proof_mode": proof_mode,
        "proof_ref_no": proof_ref_no,
        "proof_notes": proof_notes,
        "captured_at": now,
    }

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT local_sale_ref, paid, pick_status, dispatch_status
            FROM relay_local_sales
            WHERE local_sale_ref = ?
            """,
            (local_sale_ref,),
        ).fetchone()
        if not row:
            return {"ok": False, "code": "SALE_NOT_FOUND"}

        if row["dispatch_status"] == "RELEASED":
            return {"ok": True, "local_sale_ref": local_sale_ref, "dispatch_status": "RELEASED"}

        paid_ok = int(row["paid"] or 0) == 1
        pick_ok = row["pick_status"] == "PICKED_READY_FOR_RELEASE" or (
            allow_partial and row["pick_status"] == "PICK_EXCEPTION"
        )
        if not paid_ok or not pick_ok:
            return {
                "ok": False,
                "code": "RELEASE_GATE_BLOCKED",
                "message": "Paid and picked-ready checks are required",
            }

        conn.execute(
            """
            UPDATE relay_local_sales
            SET dispatch_status = 'RELEASED',
                dispatch_proof_payload = ?,
                dispatch_exception_state = 'NONE',
                cashier_adjustment_required = 0,
                released_by = ?,
                released_at = ?,
                updated_at = ?
            WHERE local_sale_ref = ?
            """,
            (_dumps(proof_payload), dispatcher_user_id or "", now, now, local_sale_ref),
        )

        dispatch_event_payload = {
            "proof": proof_payload,
            "line_snapshot": line_snapshot,
            "line_summary": line_summary,
            "allow_partial": bool(allow_partial),
        }

        conn.execute(
            """
            INSERT INTO relay_dispatch_events (
                local_sale_ref, dispatcher_user_id, event_type, notes, payload,
                source_origin, source_env, source_user_agent, created_at
            ) VALUES (?, ?, 'DISPATCH_RELEASED_WITH_PROOF', ?, ?, ?, ?, ?, ?)
            """,
            (
                local_sale_ref,
                dispatcher_user_id or "",
                notes or proof_notes,
                _dumps(dispatch_event_payload),
                source["source_origin"],
                source["source_env"],
                source["source_user_agent"],
                now,
            ),
        )

    return {
        "ok": True,
        "local_sale_ref": local_sale_ref,
        "dispatch_status": "RELEASED",
        "dispatch_proof": proof_payload,
    }


def flag_dispatch_mismatch(
    local_sale_ref,
    dispatcher_user_id=None,
    reason_code=None,
    reason_text=None,
    requires_cashier_adjustment=False,
    payload=None,
    source_meta=None,
):
    now = _now_iso()
    source = _normalize_source_meta(source_meta)
    payload_obj = payload if isinstance(payload, dict) else {}
    reason_code = str(reason_code or payload_obj.get("reason_code") or "").strip().upper()[:80]
    reason_text = str(reason_text or payload_obj.get("reason_text") or payload_obj.get("notes") or "").strip()[:500]
    if not reason_code and not reason_text:
        return {
            "ok": False,
            "code": "MISMATCH_REASON_REQUIRED",
            "message": "reason_code or reason_text is required",
        }
    line_snapshot = _normalize_line_snapshot(payload_obj.get("line_snapshot"))
    requires_cashier_adjustment = bool(
        requires_cashier_adjustment or payload_obj.get("requires_cashier_adjustment")
    )

    event_payload = {
        "reason_code": reason_code,
        "reason_text": reason_text,
        "requires_cashier_adjustment": 1 if requires_cashier_adjustment else 0,
        "line_snapshot": line_snapshot,
        "captured_at": now,
    }

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT local_sale_ref, dispatch_status
            FROM relay_local_sales
            WHERE local_sale_ref = ?
            """,
            (local_sale_ref,),
        ).fetchone()
        if not row:
            return {"ok": False, "code": "SALE_NOT_FOUND"}
        if str(row["dispatch_status"] or "").upper() == "RELEASED":
            return {"ok": False, "code": "ALREADY_RELEASED", "message": "Cannot flag mismatch after release"}

        conn.execute(
            """
            UPDATE relay_local_sales
            SET pick_status = 'PICK_EXCEPTION',
                dispatch_status = 'PENDING',
                dispatch_proof_payload = '{}',
                dispatch_exception_state = 'MISMATCH_RETURNED_TO_PICKER',
                cashier_adjustment_required = ?,
                updated_at = ?
            WHERE local_sale_ref = ?
            """,
            (1 if requires_cashier_adjustment else 0, now, local_sale_ref),
        )

        conn.execute(
            """
            INSERT INTO relay_dispatch_events (
                local_sale_ref, dispatcher_user_id, event_type, notes, payload,
                source_origin, source_env, source_user_agent, created_at
            ) VALUES (?, ?, 'DISPATCH_MISMATCH_FLAGGED', ?, ?, ?, ?, ?, ?)
            """,
            (
                local_sale_ref,
                dispatcher_user_id or "",
                reason_text or "",
                _dumps(event_payload),
                source["source_origin"],
                source["source_env"],
                source["source_user_agent"],
                now,
            ),
        )

    return {
        "ok": True,
        "local_sale_ref": local_sale_ref,
        "pick_status": "PICK_EXCEPTION",
        "dispatch_status": "PENDING",
        "dispatch_exception_state": "MISMATCH_RETURNED_TO_PICKER",
        "cashier_adjustment_required": 1 if requires_cashier_adjustment else 0,
    }


def get_pick_queue(pos_profile_id=None, limit=100):
    with get_db() as conn:
        if pos_profile_id:
            cur = conn.execute(
                """
                SELECT local_sale_ref, token_id, pos_profile_id, customer_id, customer_name,
                       pick_status, dispatch_status, dispatch_exception_state, cashier_adjustment_required,
                       paid, total, created_at, updated_at
                FROM relay_local_sales
                WHERE pos_profile_id = ? AND paid = 1 AND dispatch_status != 'RELEASED'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (pos_profile_id, int(limit)),
            )
        else:
            cur = conn.execute(
                """
                SELECT local_sale_ref, token_id, pos_profile_id, customer_id, customer_name,
                       pick_status, dispatch_status, dispatch_exception_state, cashier_adjustment_required,
                       paid, total, created_at, updated_at
                FROM relay_local_sales
                WHERE paid = 1 AND dispatch_status != 'RELEASED'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (int(limit),),
            )
        return [dict(r) for r in cur.fetchall()]


def _parse_iso_utc(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def list_relay_tokens(
    pos_profile_id=None,
    search=None,
    statuses=None,
    limit=100,
    max_age_days=1,
    allow_stale=False,
    history_days=30,
):
    max_age_days = max(0, int(max_age_days or 1))
    allow_stale = bool(allow_stale)
    history_days = max(max_age_days, int(history_days or 30))
    lookback_days = history_days if allow_stale else max_age_days
    cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat(timespec="seconds") + "Z"

    query = """
        SELECT token_id, pos_profile_id, cashier_user_id, customer_id, customer_name,
               source_origin, source_env, source_user_agent,
               status, expires_at, void_reason, voided_by, consumed_sale_ref,
               consumed_at, created_at, updated_at
        FROM relay_tokens
        WHERE 1 = 1
    """
    params = []

    if pos_profile_id:
        query += " AND pos_profile_id = ?"
        params.append(pos_profile_id)

    statuses = [str(s).strip() for s in (statuses or []) if str(s).strip()]
    if statuses:
        query += " AND status IN ({})".format(",".join(["?"] * len(statuses)))
        params.extend(statuses)

    query += " AND created_at >= ?"
    params.append(cutoff)

    if search:
        like = f"%{str(search).strip()}%"
        query += """
            AND (
                token_id LIKE ?
                OR customer_id LIKE ?
                OR customer_name LIKE ?
                OR consumed_sale_ref LIKE ?
            )
        """
        params.extend([like, like, like, like])

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(int(limit))

    with get_db() as conn:
        token_rows = [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]

        token_ids = [row["token_id"] for row in token_rows]
        line_map = {}
        if token_ids:
            placeholders = ",".join(["?"] * len(token_ids))
            line_rows = conn.execute(
                f"""
                SELECT id, token_id, item_code, item_name, qty, uom, rate, amount, payload, created_at
                FROM relay_token_lines
                WHERE token_id IN ({placeholders})
                ORDER BY id ASC
                """,
                tuple(token_ids),
            ).fetchall()
            for line in line_rows:
                d = dict(line)
                d["payload"] = _loads(d.get("payload"))
                line_map.setdefault(d["token_id"], []).append(d)

    rows = []
    now_dt = datetime.utcnow().replace(tzinfo=None)
    for row in token_rows:
        items = line_map.get(row["token_id"], [])
        total = 0.0
        for item in items:
            try:
                total += float(item.get("amount") or (float(item.get("qty") or 0) * float(item.get("rate") or 0)))
            except Exception:
                pass
        created_dt = _parse_iso_utc(row.get("created_at"))
        if created_dt:
            age_days = max(0, (now_dt - created_dt.replace(tzinfo=None)).days)
        else:
            age_days = 0
        is_stale = 1 if age_days > max_age_days else 0
        if (not allow_stale) and is_stale:
            continue
        row["items"] = items
        row["grand_total"] = total
        row["order_age_days"] = age_days
        row["is_stale"] = is_stale
        row["stale_policy_allow"] = 1 if allow_stale else 0
        row["stale_policy_max_age_days"] = max_age_days
        row["stale_policy_history_days"] = history_days
        rows.append(row)

    return rows


def get_relay_monitor_board(
    pos_profile_id=None,
    business_date=None,
    mine_only=False,
    user_id=None,
    include_released=False,
    limit=200,
):
    target_date = str(business_date or "").strip()
    user_id = str(user_id or "").strip()
    include_released = bool(include_released)

    with get_db() as conn:
        # Load token rows first so we can map SA/taken-time even after payment.
        token_query = """
            SELECT token_id, pos_profile_id, cashier_user_id, customer_id, customer_name,
                   source_origin, source_env, source_user_agent,
                   status, consumed_sale_ref, created_at, updated_at
            FROM relay_tokens
            WHERE 1 = 1
        """
        token_params = []
        if pos_profile_id:
            token_query += " AND pos_profile_id = ?"
            token_params.append(pos_profile_id)
        token_query += " ORDER BY created_at DESC LIMIT ?"
        token_params.append(max(1, int(limit) * 3))
        token_rows = [dict(r) for r in conn.execute(token_query, tuple(token_params)).fetchall()]
        token_map = {r["token_id"]: r for r in token_rows}

        sale_query = """
            SELECT local_sale_ref, token_id, pos_profile_id, cashier_user_id, cashier_session_id,
                   device_id, sale_status, pick_status, dispatch_status, paid, total, customer_id, customer_name,
                   cloud_invoice_name, cloud_sync_status, source_origin, source_env, source_user_agent,
                   dispatch_proof_payload, dispatch_exception_state, cashier_adjustment_required,
                   released_by, released_at, created_at, updated_at
            FROM relay_local_sales
            WHERE 1 = 1
        """
        sale_params = []
        if pos_profile_id:
            sale_query += " AND pos_profile_id = ?"
            sale_params.append(pos_profile_id)
        if not include_released:
            sale_query += " AND dispatch_status != 'RELEASED'"
        sale_query += " ORDER BY created_at DESC LIMIT ?"
        sale_params.append(max(1, int(limit) * 3))
        sale_rows = [dict(r) for r in conn.execute(sale_query, tuple(sale_params)).fetchall()]

        sale_refs = [r["local_sale_ref"] for r in sale_rows]
        pick_events_by_sale = {}
        if sale_refs:
            placeholders = ",".join(["?"] * len(sale_refs))
            pick_rows = conn.execute(
                f"""
                SELECT local_sale_ref, event_type, created_at
                FROM relay_pick_events
                WHERE local_sale_ref IN ({placeholders})
                ORDER BY id ASC
                """,
                tuple(sale_refs),
            ).fetchall()
            for p in pick_rows:
                pick_events_by_sale.setdefault(p["local_sale_ref"], []).append(dict(p))

    def _date_of(value):
        raw = str(value or "")
        if not raw:
            return ""
        if "T" in raw:
            return raw.split("T", 1)[0]
        if " " in raw:
            return raw.split(" ", 1)[0]
        return raw[:10]

    def _cloud_style_pick_status(local_pick_status):
        mapping = {
            "PAID_PENDING_PICK": "Not Started",
            "PICK_IN_PROGRESS": "In Progress",
            "PICK_EXCEPTION": "Exception",
            "PICKED_READY_FOR_RELEASE": "Picked",
        }
        return mapping.get(str(local_pick_status or "").strip().upper(), "")

    def _display_status(token_status, pick_status, dispatch_status):
        dispatch_status = str(dispatch_status or "").strip()
        pick_status = str(pick_status or "").strip()
        token_status = str(token_status or "").strip()
        if dispatch_status == "Released":
            return "Dispatched"
        if dispatch_status == "On Hold" or pick_status == "Exception":
            return "On Hold"
        if token_status != "Paid":
            return "Unpaid"
        if pick_status == "In Progress":
            return "Picking"
        if pick_status == "Picked":
            return "Picked"
        return "Paid"

    rows = []
    status_counts = {}
    used_token_ids = set()

    for sale in sale_rows:
        token = token_map.get((sale.get("token_id") or "").strip()) if sale.get("token_id") else None
        token_id = (sale.get("token_id") or (token or {}).get("token_id") or "").strip()
        used_token_ids.add(token_id) if token_id else None

        order_taken_at = (token or {}).get("created_at") or sale.get("created_at")
        paid_at = sale.get("created_at")
        pick_events = pick_events_by_sale.get(sale.get("local_sale_ref"), [])
        pick_started_at = ""
        picked_at = ""
        for evt in pick_events:
            event_type = str(evt.get("event_type") or "").strip().upper()
            if event_type == "PICK_IN_PROGRESS" and not pick_started_at:
                pick_started_at = evt.get("created_at") or ""
            if event_type == "PICKED_READY_FOR_RELEASE" and not picked_at:
                picked_at = evt.get("created_at") or ""

        token_status = "Paid" if int(sale.get("paid") or 0) == 1 else "Unpaid"
        pick_status = _cloud_style_pick_status(sale.get("pick_status"))
        dispatch_status = "Released" if str(sale.get("dispatch_status") or "").upper() == "RELEASED" else "Pending"
        display_status = _display_status(token_status, pick_status, dispatch_status)

        row = {
            "workflow_state": f"relay-sale:{sale.get('local_sale_ref')}",
            "sales_order": token_id or "",
            "sales_invoice": sale.get("cloud_invoice_name") or "",
            "token_id": token_id or "",
            "customer_name": sale.get("customer_name") or (token or {}).get("customer_name") or "",
            "grand_total": sale.get("total"),
            "currency": "",
            "sales_associate_user": (token or {}).get("cashier_user_id") or "",
            "sales_associate_name": (token or {}).get("cashier_user_id") or "",
            "business_date": _date_of(order_taken_at) or _date_of(sale.get("created_at")),
            "pos_opening_shift": "",
            "token_status": token_status,
            "picking_status": pick_status,
            "dispatch_status": dispatch_status,
            "display_status": display_status,
            "order_taken_at": order_taken_at,
            "paid_at": paid_at,
            "pick_started_at": pick_started_at,
            "picked_at": picked_at,
            "released_at": sale.get("released_at") or "",
            "status_changed_at": sale.get("updated_at") or sale.get("created_at"),
            "dispatch_proof": _loads(sale.get("dispatch_proof_payload")),
            "dispatch_exception_state": sale.get("dispatch_exception_state") or "NONE",
            "cashier_adjustment_required": int(sale.get("cashier_adjustment_required") or 0),
            "source_origin": sale.get("source_origin") or "",
            "source_env": sale.get("source_env") or (token or {}).get("source_env") or "",
            "source_user_agent": sale.get("source_user_agent") or "",
        }

        if target_date and row["business_date"] and row["business_date"] != target_date:
            continue
        if mine_only and user_id and row.get("sales_associate_user") != user_id:
            continue

        rows.append(row)
        status_counts[display_status] = status_counts.get(display_status, 0) + 1

    # Add still-open unpaid tokens that do not yet have a local sale.
    for token in token_rows:
        token_id = str(token.get("token_id") or "").strip()
        if not token_id:
            continue
        if token_id in used_token_ids:
            continue
        status = str(token.get("status") or "").strip().upper()
        if status not in ("TOKEN_OPEN", "TOKEN_EXPIRED"):
            continue

        token_status = "Unpaid"
        display_status = "Unpaid"
        row = {
            "workflow_state": f"relay-token:{token_id}",
            "sales_order": token_id,
            "sales_invoice": "",
            "token_id": token_id,
            "customer_name": token.get("customer_name") or token.get("customer_id") or "",
            "grand_total": None,
            "currency": "",
            "sales_associate_user": token.get("cashier_user_id") or "",
            "sales_associate_name": token.get("cashier_user_id") or "",
            "business_date": _date_of(token.get("created_at")),
            "pos_opening_shift": "",
            "token_status": token_status,
            "picking_status": "",
            "dispatch_status": "Pending",
            "display_status": display_status,
            "order_taken_at": token.get("created_at"),
            "paid_at": "",
            "pick_started_at": "",
            "picked_at": "",
            "released_at": "",
            "status_changed_at": token.get("updated_at") or token.get("created_at"),
            "dispatch_proof": {},
            "dispatch_exception_state": "NONE",
            "cashier_adjustment_required": 0,
            "source_origin": token.get("source_origin") or "",
            "source_env": token.get("source_env") or "",
            "source_user_agent": token.get("source_user_agent") or "",
        }

        if target_date and row["business_date"] and row["business_date"] != target_date:
            continue
        if mine_only and user_id and row.get("sales_associate_user") != user_id:
            continue
        rows.append(row)
        status_counts[display_status] = status_counts.get(display_status, 0) + 1

    rows.sort(key=lambda r: str(r.get("status_changed_at") or r.get("order_taken_at") or ""))
    rows = rows[: max(1, int(limit))]
    visible_status_counts = {}
    for row in rows:
        key = str(row.get("display_status") or "").strip()
        if not key:
            continue
        visible_status_counts[key] = visible_status_counts.get(key, 0) + 1

    return {
        "summary": {
            "pending_count": len(rows),
            "status_counts": visible_status_counts,
            "server_time": _now_iso(),
            "scope_mode": "business_date",
            "business_date": target_date or "",
            "pos_profile": pos_profile_id or "",
            "source": "relay_local",
        },
        "rows": rows,
    }


def set_local_sale_cloud_synced(local_sale_ref, cloud_invoice_name=None):
    now = _now_iso()
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_local_sales
            SET cloud_sync_status = 'SALE_SYNCED_SI_SUBMITTED',
                cloud_invoice_name = COALESCE(?, cloud_invoice_name),
                cloud_sync_error = NULL,
                updated_at = ?
            WHERE local_sale_ref = ?
            """,
            (cloud_invoice_name, now, local_sale_ref),
        )


def set_local_quote_cloud_synced(quote_id, cloud_quote_name=None):
    quote_id = str(quote_id or "").strip()
    if not quote_id:
        return
    now = _now_iso()
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_quotes
            SET cloud_quote_name = COALESCE(?, cloud_quote_name),
                updated_at = ?
            WHERE quote_id = ?
            """,
            (str(cloud_quote_name or "").strip() or None, now, quote_id),
        )


def set_local_sale_sync_error(local_sale_ref, error):
    now = _now_iso()
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_local_sales
            SET cloud_sync_status = 'SALE_SYNC_PENDING', cloud_sync_error = ?, updated_at = ?
            WHERE local_sale_ref = ?
            """,
            (str(error)[:1000], now, local_sale_ref),
        )


def get_latest_local_sale(local_sale_ref):
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT local_sale_ref, token_id, pos_profile_id, cashier_user_id,
                   cashier_session_id, device_id, idempotency_key,
                   sale_status, pick_status, dispatch_status, paid,
                   total, net_total, customer_id, customer_name,
                   invoice_payload, data_payload,
                   cloud_invoice_name, cloud_sync_status, cloud_sync_error,
                   source_origin, source_env, source_user_agent,
                   dispatch_proof_payload, dispatch_exception_state, cashier_adjustment_required,
                   released_by, released_at, created_at, updated_at
            FROM relay_local_sales
            WHERE local_sale_ref = ?
            """,
            (local_sale_ref,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["invoice_payload"] = _loads(data.get("invoice_payload"))
        data["data_payload"] = _loads(data.get("data_payload"))
        data["dispatch_proof_payload"] = _loads(data.get("dispatch_proof_payload"))
        data["dispatch_proof"] = data["dispatch_proof_payload"]
        data["cashier_adjustment_required"] = int(data.get("cashier_adjustment_required") or 0)
        return data


def list_local_sales(limit=200, pos_profile_id=None, search=None):
    query = """
        SELECT local_sale_ref, token_id, pos_profile_id, cashier_user_id,
               cashier_session_id, device_id, idempotency_key,
               sale_status, pick_status, dispatch_status, paid,
               total, net_total, customer_id, customer_name,
               cloud_invoice_name, cloud_sync_status, cloud_sync_error,
               source_origin, source_env, source_user_agent,
               dispatch_proof_payload, dispatch_exception_state, cashier_adjustment_required,
               released_by, released_at, created_at, updated_at
        FROM relay_local_sales
        WHERE 1 = 1
    """
    params = []

    if pos_profile_id:
        query += " AND pos_profile_id = ?"
        params.append(pos_profile_id)

    if search:
        like = f"%{search}%"
        query += """
            AND (
                local_sale_ref LIKE ?
                OR token_id LIKE ?
                OR customer_id LIKE ?
                OR customer_name LIKE ?
                OR cloud_invoice_name LIKE ?
            )
        """
        params.extend([like, like, like, like, like])

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(int(limit))

    with get_db() as conn:
        cur = conn.execute(query, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            row["dispatch_proof_payload"] = _loads(row.get("dispatch_proof_payload"))
            row["dispatch_proof"] = row["dispatch_proof_payload"]
            row["cashier_adjustment_required"] = int(row.get("cashier_adjustment_required") or 0)
        return rows


def get_local_sale_detail(local_sale_ref):
    with get_db() as conn:
        sale_row = conn.execute(
            """
            SELECT local_sale_ref, token_id, pos_profile_id, cashier_user_id,
                   cashier_session_id, device_id, idempotency_key,
                   sale_status, pick_status, dispatch_status, paid,
                   total, net_total, customer_id, customer_name,
                   invoice_payload, data_payload,
                   cloud_invoice_name, cloud_sync_status, cloud_sync_error,
                   source_origin, source_env, source_user_agent,
                   dispatch_proof_payload, dispatch_exception_state, cashier_adjustment_required,
                   released_by, released_at, created_at, updated_at
            FROM relay_local_sales
            WHERE local_sale_ref = ?
            """,
            (local_sale_ref,),
        ).fetchone()

        if not sale_row:
            return None

        line_rows = conn.execute(
            """
            SELECT id, local_sale_ref, item_code, item_name, qty, uom, rate, amount,
                   line_status, pick_status, payload, created_at, updated_at
            FROM relay_local_sale_lines
            WHERE local_sale_ref = ?
            ORDER BY id ASC
            """,
            (local_sale_ref,),
        ).fetchall()

        pick_rows = conn.execute(
            """
            SELECT id, local_sale_ref, picker_user_id, event_type, notes, payload, created_at
                   ,source_origin, source_env, source_user_agent
            FROM relay_pick_events
            WHERE local_sale_ref = ?
            ORDER BY id ASC
            """,
            (local_sale_ref,),
        ).fetchall()

        dispatch_rows = conn.execute(
            """
            SELECT id, local_sale_ref, dispatcher_user_id, event_type, notes, payload, created_at
                   ,source_origin, source_env, source_user_agent
            FROM relay_dispatch_events
            WHERE local_sale_ref = ?
            ORDER BY id ASC
            """,
            (local_sale_ref,),
        ).fetchall()

        outbox_rows = conn.execute(
            """
            SELECT event_id, event_type, idempotency_key, local_ref, payload,
                   source_origin, source_env, source_user_agent,
                   status, retries, next_attempt_at, last_error, cloud_ref,
                   created_at, updated_at
            FROM relay_outbox
            WHERE local_ref = ?
            ORDER BY created_at DESC
            """,
            (local_sale_ref,),
        ).fetchall()

    sale = dict(sale_row)
    sale["invoice_payload"] = _loads(sale.get("invoice_payload"))
    sale["data_payload"] = _loads(sale.get("data_payload"))
    sale["dispatch_proof_payload"] = _loads(sale.get("dispatch_proof_payload"))
    sale["dispatch_proof"] = sale["dispatch_proof_payload"]
    sale["cashier_adjustment_required"] = int(sale.get("cashier_adjustment_required") or 0)

    lines = [dict(r) for r in line_rows]
    for row in lines:
        row["payload"] = _loads(row.get("payload"))

    pick_events = [dict(r) for r in pick_rows]
    for row in pick_events:
        row["payload"] = _loads(row.get("payload"))

    dispatch_events = [dict(r) for r in dispatch_rows]
    for row in dispatch_events:
        row["payload"] = _loads(row.get("payload"))

    outbox_events = [dict(r) for r in outbox_rows]
    for row in outbox_events:
        row["payload"] = _loads(row.get("payload"))

    return {
        "sale": sale,
        "lines": lines,
        "pick_events": pick_events,
        "dispatch_events": dispatch_events,
        "outbox_events": outbox_events,
    }

