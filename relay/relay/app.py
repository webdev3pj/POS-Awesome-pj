import os
import hashlib
import threading
from flask import Flask, flash, jsonify, redirect, render_template, request

from .storage import (
    commit_invoice_atomic,
    create_token,
    close_cashier_session,
    enqueue_event,
    enqueue_outbox_event,
    get_local_sale_detail,
    get_pick_queue,
    get_token,
    init_db,
    list_local_sales,
    list_outbox,
    list_queue,
    load_config,
    open_cashier_session,
    outbox_counts,
    refresh_items_cache,
    release_sale,
    queue_counts,
    search_items_cache,
    save_config,
    update_pick_status,
    upsert_customer,
    void_token,
)
from .sync_worker import run_sync_loop, sync_once
from .windows_setup import bootstrap_windows
from .offline_sync import refresh_items_from_cloud


def create_app():
    app = Flask(__name__, template_folder="templates")
    app.secret_key = os.environ.get("RELAY_SECRET", "pos-relay-secret")

    init_db()

    def _start_sync_thread():
        cfg = load_config()
        sleep_seconds = int(cfg.get("poll_seconds") or 5)
        t = threading.Thread(target=run_sync_loop, kwargs={"sleep_seconds": sleep_seconds}, daemon=True)
        t.start()

    _start_sync_thread()

    @app.after_request
    def add_cors_headers(response):
        # Allow POS browser clients (served from cloud origin) to post to the local relay
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return response

    @app.route("/")
    def dashboard():
        cfg = load_config()
        tx_limit = int(request.args.get("tx_limit") or 150)
        tx_limit = max(1, min(500, tx_limit))
        tx_pos_profile = (request.args.get("tx_pos_profile") or "").strip() or None
        tx_search = (request.args.get("tx_search") or "").strip() or None
        tx_rows = list_local_sales(limit=tx_limit, pos_profile_id=tx_pos_profile, search=tx_search)

        tx_summary = {
            "total": len(tx_rows),
            "sync_pending": 0,
            "synced": 0,
            "dispatch_released": 0,
            "pick_exceptions": 0,
            "sync_errors": 0,
        }
        for row in tx_rows:
            sync_status = (row.get("cloud_sync_status") or "").upper()
            dispatch_status = (row.get("dispatch_status") or "").upper()
            pick_status = (row.get("pick_status") or "").upper()
            if sync_status == "SALE_SYNCED_SI_SUBMITTED":
                tx_summary["synced"] += 1
            else:
                tx_summary["sync_pending"] += 1
            if dispatch_status == "RELEASED":
                tx_summary["dispatch_released"] += 1
            if pick_status == "PICK_EXCEPTION":
                tx_summary["pick_exceptions"] += 1
            if row.get("cloud_sync_error"):
                tx_summary["sync_errors"] += 1

        return render_template(
            "dashboard.html",
            title="POS Relay Dashboard",
            config=cfg,
            counts=queue_counts(),
            outbox_counts=outbox_counts(),
            tx_rows=tx_rows,
            tx_summary=tx_summary,
            tx_limit=tx_limit,
            tx_pos_profile=tx_pos_profile or "",
            tx_search=tx_search or "",
        )

    @app.route("/queue")
    def queue_page():
        return render_template(
            "queue.html",
            title="Relay Queue",
            rows=list_queue(300),
            counts=queue_counts(),
        )

    @app.route("/setup", methods=["GET", "POST"])
    def setup_page():
        if request.method == "POST":
            payload = {
                "frappe_base_url": (request.form.get("frappe_base_url") or "").strip(),
                "api_key": (request.form.get("api_key") or "").strip(),
                "api_secret": (request.form.get("api_secret") or "").strip(),
                "relay_host": (request.form.get("relay_host") or "0.0.0.0").strip(),
                "relay_port": int(request.form.get("relay_port") or 8787),
                "public_base_url": (request.form.get("public_base_url") or "").strip(),
                "site_name": (request.form.get("site_name") or "").strip(),
                "poll_seconds": int(request.form.get("poll_seconds") or 5),
                "allowed_subnet": (request.form.get("allowed_subnet") or "192.168.50.0/24").strip(),
            }
            save_config(payload)
            flash("Relay configuration saved.", "success")
            return redirect("/setup")

        cfg = load_config()
        return render_template("setup.html", title="System Setup", config=cfg)

    @app.route("/setup/bootstrap", methods=["POST"])
    def setup_bootstrap():
        cfg = load_config()
        result = bootstrap_windows(cfg.get("relay_port") or 8787)
        if result.get("ok"):
            flash("Windows bootstrap completed successfully.", "success")
        else:
            flash("Windows bootstrap completed with errors. Check output in /health.", "error")
        return redirect("/setup")

    @app.route("/health")
    def health():
        cfg = load_config()
        return jsonify(
            {
                "ok": True,
                "relay": {
                    "host": cfg.get("relay_host"),
                    "port": cfg.get("relay_port"),
                    "allowed_subnet": cfg.get("allowed_subnet"),
                },
                "frappe_base_url": cfg.get("frappe_base_url"),
                "public_base_url": cfg.get("public_base_url"),
                "queue": queue_counts(),
                "outbox": outbox_counts(),
            }
        )

    @app.route("/api/erpnext-access-check", methods=["GET"])
    def api_erpnext_access_check():
        """
        Validates if the configured relay URL is reachable from ERPNext/cloud perspective.
        This is best-effort and uses the same method ERPNext backend uses: HTTP GET /health.
        """
        cfg = load_config()
        target_url = (request.args.get("relay_url") or "").strip()
        if not target_url:
            target_url = (cfg.get("public_base_url") or "").strip()
        if not target_url:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "not_configured",
                        "message": "Relay URL is not configured. Set public_base_url in relay setup or pass relay_url query.",
                    }
                ),
                400,
            )

        if target_url.endswith("/"):
            target_url = target_url.rstrip("/")
        health_url = f"{target_url}/health"

        import requests

        try:
            resp = requests.get(health_url, timeout=5)
            resp.raise_for_status()
            payload = {}
            try:
                payload = resp.json() or {}
            except Exception:
                payload = {}
            return jsonify(
                {
                    "ok": True,
                    "status": "reachable",
                    "relay_url": target_url,
                    "health_url": health_url,
                    "http_status": resp.status_code,
                    "relay_ok": bool(payload.get("ok")) if isinstance(payload, dict) else True,
                    "message": "Relay URL is reachable via /health.",
                }
            )
        except requests.exceptions.Timeout:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "timeout",
                        "relay_url": target_url,
                        "health_url": health_url,
                        "message": "Timeout while checking relay URL.",
                    }
                ),
                504,
            )
        except requests.exceptions.ConnectionError:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "connection_error",
                        "relay_url": target_url,
                        "health_url": health_url,
                        "message": "Connection failed while checking relay URL.",
                    }
                ),
                503,
            )
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if getattr(exc, "response", None) else None
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "http_error",
                        "relay_url": target_url,
                        "health_url": health_url,
                        "http_status": status_code,
                        "message": "Relay URL responded with HTTP error.",
                    }
                ),
                502,
            )
        except Exception as exc:
            return (
                jsonify(
                    {
                        "ok": False,
                        "status": "error",
                        "relay_url": target_url,
                        "health_url": health_url,
                        "message": str(exc),
                    }
                ),
                500,
            )

    @app.route("/api/metrics")
    def api_metrics():
        return jsonify(queue_counts())

    @app.route("/api/queue")
    def api_queue():
        return jsonify({"rows": list_queue(500), "counts": queue_counts()})

    @app.route("/api/outbox")
    def api_outbox():
        return jsonify({"rows": list_outbox(500), "counts": outbox_counts()})

    @app.route("/api/transactions")
    def api_transactions():
        limit = int(request.args.get("limit") or 200)
        limit = max(1, min(1000, limit))
        pos_profile_id = (request.args.get("pos_profile_id") or "").strip() or None
        search = (request.args.get("search") or "").strip() or None
        rows = list_local_sales(limit=limit, pos_profile_id=pos_profile_id, search=search)
        return jsonify({"rows": rows, "count": len(rows)})

    @app.route("/api/transactions/<local_sale_ref>")
    def api_transaction_detail(local_sale_ref):
        detail = get_local_sale_detail(local_sale_ref)
        if not detail:
            return jsonify({"ok": False, "code": "SALE_NOT_FOUND"}), 404
        return jsonify({"ok": True, **detail})

    @app.route("/api/sync-now", methods=["POST"])
    def api_sync_now():
        result = sync_once()
        if request.headers.get("Accept", "").lower().find("application/json") >= 0:
            return jsonify(result)
        if result.get("ok"):
            flash("Sync executed.", "success")
        else:
            flash(f"Sync error: {result.get('message')}", "error")
        return redirect("/")

    @app.route("/relay/token", methods=["POST"])
    def relay_token():
        payload = request.get_json(silent=True) or {}
        event_id = enqueue_event("token_create", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/pick", methods=["POST"])
    def relay_pick():
        payload = request.get_json(silent=True) or {}
        event_id = enqueue_event("pick_update", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/release", methods=["POST"])
    def relay_release():
        payload = request.get_json(silent=True) or {}
        event_id = enqueue_event("dispatch_release", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/submit-invoice", methods=["POST", "OPTIONS"])
    def relay_submit_invoice():
        if request.method == "OPTIONS":
            return ("", 204)

        payload = request.get_json(silent=True) or {}
        invoice_payload = payload.get("invoice")
        data_payload = payload.get("data")

        if not invoice_payload or not data_payload:
            return (
                jsonify(
                    {
                        "ok": False,
                        "message": "Both 'invoice' and 'data' are required.",
                    }
                ),
                400,
            )

        event_id = enqueue_event("invoice_submit", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/token/create", methods=["POST", "OPTIONS"])
    def relay_token_create_v2():
        if request.method == "OPTIONS":
            return ("", 204)

        payload = request.get_json(silent=True) or {}
        expiry_minutes = int(payload.get("expiry_minutes") or 120)
        token = create_token(payload, expiry_minutes=expiry_minutes)

        outbox_event_id = enqueue_outbox_event(
            "TOKEN_CREATED",
            {
                "token_id": token.get("token_id"),
                "payload": payload,
            },
            local_ref=token.get("token_id"),
        )
        return jsonify(
            {
                "ok": True,
                "token": token,
                "outbox_event_id": outbox_event_id,
            }
        )

    @app.route("/relay/token/<token_id>", methods=["GET"])
    def relay_token_get_v2(token_id):
        token = get_token(token_id)
        if not token:
            return jsonify({"ok": False, "code": "TOKEN_NOT_FOUND"}), 404
        return jsonify({"ok": True, "token": token})

    @app.route("/relay/token/<token_id>/void", methods=["POST", "OPTIONS"])
    def relay_token_void_v2(token_id):
        if request.method == "OPTIONS":
            return ("", 204)
        payload = request.get_json(silent=True) or {}
        result = void_token(
            token_id,
            supervisor_user_id=payload.get("supervisor_user_id"),
            reason=payload.get("reason"),
        )
        status_code = 200 if result.get("ok") else 409
        return jsonify(result), status_code

    @app.route("/relay/session/open", methods=["POST", "OPTIONS"])
    def relay_session_open_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        payload = request.get_json(silent=True) or {}
        session = open_cashier_session(payload)
        outbox_event_id = enqueue_outbox_event(
            "SESSION_OPEN",
            payload,
            local_ref=session.get("session_id"),
        )
        return jsonify({"ok": True, "session": session, "outbox_event_id": outbox_event_id})

    @app.route("/relay/session/current", methods=["GET"])
    def relay_session_current_v2():
        pos_profile_id = (request.args.get("pos_profile_id") or "").strip()
        cashier_user_id = (request.args.get("cashier_user_id") or "").strip()
        device_id = (request.args.get("device_id") or "").strip()
        if not pos_profile_id or not cashier_user_id:
            return jsonify({"ok": False, "code": "MISSING_FIELDS"}), 400

        from .storage import get_db

        with get_db() as conn:
            query = """
                SELECT session_id, pos_profile_id, cashier_user_id, device_id,
                       status, opened_at, closed_at, close_note, created_at, updated_at
                FROM relay_cashier_sessions
                WHERE pos_profile_id = ?
                  AND cashier_user_id = ?
                  AND status = 'OPEN'
            """
            params = [pos_profile_id, cashier_user_id]
            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            query += " ORDER BY opened_at DESC LIMIT 1"

            row = conn.execute(query, tuple(params)).fetchone()

        if not row:
            return jsonify({"ok": True, "session": None})

        return jsonify({"ok": True, "session": dict(row)})

    @app.route("/relay/session/close", methods=["POST", "OPTIONS"])
    def relay_session_close_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        payload = request.get_json(silent=True) or {}
        session_id = payload.get("session_id")
        if not session_id:
            return jsonify({"ok": False, "code": "SESSION_ID_REQUIRED"}), 400

        result = close_cashier_session(session_id, close_note=payload.get("close_note"))
        if result.get("ok"):
            outbox_event_id = enqueue_outbox_event(
                "SESSION_CLOSE",
                payload,
                local_ref=session_id,
            )
            result["outbox_event_id"] = outbox_event_id
        status_code = 200 if result.get("ok") else 404
        return jsonify(result), status_code

    @app.route("/relay/customer/upsert", methods=["POST", "OPTIONS"])
    def relay_customer_upsert_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        payload = request.get_json(silent=True) or {}
        customer = upsert_customer(payload)
        outbox_event_id = enqueue_outbox_event(
            "CUSTOMER_UPSERT",
            payload,
            local_ref=customer.get("customer_id"),
        )
        return jsonify({"ok": True, "customer": customer, "outbox_event_id": outbox_event_id})

    @app.route("/relay/items/search", methods=["GET"])
    def relay_items_search_v2():
        q = (request.args.get("q") or "").strip()
        limit = int(request.args.get("limit") or 50)
        rows = search_items_cache(q, limit=limit)
        return jsonify({"ok": True, "rows": rows, "count": len(rows)})

    @app.route("/relay/items/refresh", methods=["POST", "OPTIONS"])
    def relay_items_refresh_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        payload = request.get_json(silent=True) or {}
        items = payload.get("items") or []
        result = refresh_items_cache(items)
        return jsonify({"ok": True, "result": result})

    @app.route("/relay/customer/search", methods=["GET"])
    def relay_customer_search_v2():
        q = (request.args.get("q") or "").strip()
        limit = int(request.args.get("limit") or 50)

        from .storage import get_db

        with get_db() as conn:
            if q:
                like = f"%{q}%"
                cur = conn.execute(
                    """
                    SELECT customer_id, customer_name, mobile_no, email_id, tax_id, payload, updated_at
                    FROM relay_customers
                    WHERE customer_id LIKE ? OR customer_name LIKE ? OR mobile_no LIKE ? OR email_id LIKE ?
                    ORDER BY customer_name ASC
                    LIMIT ?
                    """,
                    (like, like, like, like, limit),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT customer_id, customer_name, mobile_no, email_id, tax_id, payload, updated_at
                    FROM relay_customers
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            rows = [dict(r) for r in cur.fetchall()]
        return jsonify({"ok": True, "rows": rows, "count": len(rows)})

    @app.route("/relay/items/refresh-from-cloud", methods=["POST", "OPTIONS"])
    def relay_items_refresh_from_cloud_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        payload = request.get_json(silent=True) or {}
        cfg = load_config()
        result = refresh_items_from_cloud(
            cfg,
            pos_profile_payload=payload.get("pos_profile"),
            limit=int(payload.get("limit") or 200),
        )
        status_code = 200 if result.get("ok") else 503
        return jsonify(result), status_code

    @app.route("/relay/commit-invoice", methods=["POST", "OPTIONS"])
    def relay_commit_invoice_v2():
        if request.method == "OPTIONS":
            return ("", 204)

        payload = request.get_json(silent=True) or {}
        idempotency_key = (payload.get("idempotency_key") or "").strip()
        if not idempotency_key:
            return (
                jsonify(
                    {
                        "ok": False,
                        "code": "IDEMPOTENCY_KEY_REQUIRED",
                        "message": "idempotency_key is required",
                    }
                ),
                400,
            )

        # deterministic request hash to support future strict replay validation
        canonical_payload = {
            "token_id": payload.get("token_id"),
            "pos_profile_id": payload.get("pos_profile_id"),
            "cashier_user_id": payload.get("cashier_user_id"),
            "cashier_session_id": payload.get("cashier_session_id"),
            "device_id": payload.get("device_id"),
            "invoice": payload.get("invoice") or {},
            "data": payload.get("data") or {},
        }
        canonical_str = str(canonical_payload).encode("utf-8")
        payload["request_hash"] = hashlib.sha256(canonical_str).hexdigest()

        commit_result = commit_invoice_atomic(payload)
        if not commit_result.get("ok"):
            code = commit_result.get("code")
            if code == "TOKEN_ALREADY_PAID":
                return jsonify(commit_result), 409
            if code in ("IDEMPOTENCY_KEY_REQUIRED", "POS_PROFILE_REQUIRED"):
                return jsonify(commit_result), 400
            if code == "TOKEN_NOT_FOUND":
                return jsonify(commit_result), 404
            return jsonify(commit_result), 409

        local_sale_ref = commit_result.get("local_sale_ref")

        if not commit_result.get("idempotent_replay"):
            outbox_payload = {
                "local_sale_ref": local_sale_ref,
                "invoice": payload.get("invoice") or {},
                "data": payload.get("data") or {},
                "token_id": payload.get("token_id"),
                "pos_profile_id": payload.get("pos_profile_id"),
                "cashier_user_id": payload.get("cashier_user_id"),
                "cashier_session_id": payload.get("cashier_session_id"),
                "device_id": payload.get("device_id"),
            }
            outbox_event_id = enqueue_outbox_event(
                "SALE_COMMITTED",
                outbox_payload,
                idempotency_key=idempotency_key,
                local_ref=local_sale_ref,
            )
        else:
            outbox_event_id = None

        return jsonify(
            {
                "ok": True,
                "idempotent_replay": bool(commit_result.get("idempotent_replay")),
                "local_sale_ref": local_sale_ref,
                "sale_status": "SALE_COMMITTED_LOCAL",
                "cloud_sync_status": "SALE_SYNC_PENDING",
                "outbox_event_id": outbox_event_id,
            }
        )

    @app.route("/relay/pick-queue", methods=["GET"])
    def relay_pick_queue_v2():
        pos_profile_id = (request.args.get("pos_profile_id") or "").strip() or None
        limit = int(request.args.get("limit") or 100)
        rows = get_pick_queue(pos_profile_id=pos_profile_id, limit=limit)
        return jsonify({"ok": True, "rows": rows, "count": len(rows)})

    @app.route("/relay/pick/update", methods=["POST", "OPTIONS"])
    def relay_pick_update_v2():
        if request.method == "OPTIONS":
            return ("", 204)

        payload = request.get_json(silent=True) or {}
        local_sale_ref = payload.get("local_sale_ref")
        picking_status = payload.get("picking_status")
        if not local_sale_ref or not picking_status:
            return jsonify({"ok": False, "code": "MISSING_FIELDS"}), 400

        result = update_pick_status(
            local_sale_ref=local_sale_ref,
            picking_status=picking_status,
            picker_user_id=payload.get("picker_user_id"),
            notes=payload.get("notes"),
            payload=payload,
        )
        if result.get("ok"):
            outbox_event_id = enqueue_outbox_event(
                "PICK_EVENT",
                payload,
                local_ref=local_sale_ref,
            )
            result["outbox_event_id"] = outbox_event_id
        status_code = 200 if result.get("ok") else 409
        return jsonify(result), status_code

    @app.route("/relay/dispatch/release", methods=["POST", "OPTIONS"])
    def relay_dispatch_release_v2():
        if request.method == "OPTIONS":
            return ("", 204)

        payload = request.get_json(silent=True) or {}
        local_sale_ref = payload.get("local_sale_ref")
        if not local_sale_ref:
            return jsonify({"ok": False, "code": "LOCAL_SALE_REF_REQUIRED"}), 400

        result = release_sale(
            local_sale_ref=local_sale_ref,
            dispatcher_user_id=payload.get("dispatcher_user_id"),
            allow_partial=bool(payload.get("allow_partial")),
            notes=payload.get("notes"),
            payload=payload,
        )
        if result.get("ok"):
            outbox_event_id = enqueue_outbox_event(
                "RELEASE_EVENT",
                payload,
                local_ref=local_sale_ref,
            )
            result["outbox_event_id"] = outbox_event_id
        status_code = 200 if result.get("ok") else 409
        return jsonify(result), status_code

    return app


if __name__ == "__main__":
    app = create_app()
    cfg = load_config()
    host = cfg.get("relay_host") or "0.0.0.0"
    port = int(cfg.get("relay_port") or 8787)
    app.run(host=host, port=port, debug=False)

