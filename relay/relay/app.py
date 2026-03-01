import os
import hmac
import hashlib
import ipaddress
import threading
from urllib.parse import urlparse
from flask import Flask, flash, jsonify, redirect, render_template, request

from .storage import (
    commit_invoice_atomic,
    convert_local_quote_to_token,
    create_token,
    close_cashier_session,
    enqueue_event,
    enqueue_outbox_event,
    flag_dispatch_mismatch,
    get_local_quote,
    get_local_sale_detail,
    get_relay_monitor_board,
    get_pick_queue,
    get_token,
    init_db,
    list_local_quotes,
    list_local_sales,
    list_relay_tokens,
    list_outbox,
    list_queue,
    preview_local_quote_reprice,
    cleanup_outbox_rows,
    load_config,
    open_cashier_session,
    outbox_counts,
    refresh_items_cache,
    release_sale,
    queue_counts,
    search_items_cache,
    save_config,
    upsert_local_quote,
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

    RELAY_ROLE_GROUPS = {
        "fulfillment_any": (
            "cline-Sales Associate",
            "cline-Cashier",
            "cline-Picker",
            "cline-Dispatch",
            "cline-Supervisor",
        ),
        "token_create": ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "quote_action": ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "session_cashier": ("cline-Cashier", "cline-Supervisor"),
        "commit_invoice": ("cline-Cashier", "cline-Supervisor"),
        "pick_update": ("cline-Picker", "cline-Supervisor"),
        "dispatch_release": ("cline-Dispatch", "cline-Supervisor"),
        "dispatch_mismatch": ("cline-Dispatch", "cline-Supervisor"),
        "token_void": ("cline-Supervisor",),
    }

    def _json_error(code, message, status_code=400, extra=None):
        payload = {"ok": False, "code": code, "message": message}
        if isinstance(extra, dict):
            payload.update(extra)
        return jsonify(payload), int(status_code)

    def _client_ip():
        xff = (request.headers.get("X-Forwarded-For") or "").strip()
        if xff:
            return xff.split(",")[0].strip()
        return (request.remote_addr or "").strip()

    def _client_allowed_by_subnet():
        cfg = load_config()
        ip_text = _client_ip()
        if not ip_text:
            return False
        try:
            ip = ipaddress.ip_address(ip_text)
            if ip.is_loopback:
                return True
            subnet = (cfg.get("allowed_subnet") or "").strip()
            if not subnet:
                return True
            net = ipaddress.ip_network(subnet, strict=False)
            return ip in net
        except Exception:
            # Fail open on parsing issues; auth key remains the stronger control when enabled.
            return True

    def _relay_client_auth_enabled(cfg=None):
        cfg = cfg or load_config()
        expected = str(cfg.get("relay_client_auth_key") or "").strip()
        required = bool(cfg.get("relay_client_auth_required")) or bool(expected)
        return required, expected

    def _require_relay_client_auth():
        cfg = load_config()
        if not _client_allowed_by_subnet():
            return _json_error(
                "CLIENT_OUTSIDE_ALLOWED_SUBNET",
                "Relay request origin is outside the allowed subnet.",
                403,
                {"client_ip": _client_ip(), "allowed_subnet": cfg.get("allowed_subnet")},
            )

        required, expected = _relay_client_auth_enabled(cfg)
        if not required:
            return None
        provided = (request.headers.get("X-Relay-Client-Key") or "").strip()
        if not expected:
            return _json_error(
                "RELAY_CLIENT_AUTH_MISCONFIGURED",
                "Relay client auth is enabled but no relay_client_auth_key is configured.",
                503,
            )
        if not provided or not hmac.compare_digest(provided, expected):
            return _json_error("RELAY_CLIENT_AUTH_FAILED", "Invalid relay client key.", 401)
        return None

    def _extract_role(payload):
        payload = payload or {}
        return str(payload.get("role") or payload.get("session_role") or "").strip()

    def _request_origin_url():
        origin = (request.headers.get("Origin") or "").strip()
        if origin:
            return origin
        referer = (request.headers.get("Referer") or "").strip()
        if not referer:
            return ""
        try:
            parsed = urlparse(referer)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass
        return ""

    def _classify_source_env(origin_url):
        origin_url = str(origin_url or "").strip()
        if not origin_url:
            return "unknown"
        try:
            host = (urlparse(origin_url).netloc or "").lower().strip()
        except Exception:
            host = ""
        if not host:
            return "unknown"
        if host == "devpjjamaica.v.frappe.cloud":
            return "cloud_dev"
        if host.endswith(".frappe.cloud"):
            return "cloud_frappe"
        if host.startswith("pj.local") or host.startswith("localhost") or host.startswith("127.0.0.1"):
            return "local_staging"
        return "other"

    def _request_source_meta():
        origin_url = _request_origin_url()
        return {
            "source_origin": origin_url,
            "source_env": _classify_source_env(origin_url),
            "source_user_agent": (request.headers.get("User-Agent") or "").strip(),
        }

    def _require_relay_role(payload, allowed_roles, role_field="role"):
        allowed_roles = tuple(str(r).strip() for r in (allowed_roles or []) if str(r).strip())
        role = _extract_role(payload)
        if not role:
            return _json_error(
                "RELAY_ROLE_REQUIRED",
                f"{role_field} is required for this relay action.",
                400,
                {"allowed_roles": list(allowed_roles)},
            )
        if allowed_roles and role not in allowed_roles:
            return _json_error(
                "RELAY_ROLE_NOT_AUTHORIZED",
                f"Role {role} is not allowed for this relay action.",
                403,
                {"role": role, "allowed_roles": list(allowed_roles)},
            )
        return None

    @app.after_request
    def add_cors_headers(response):
        # Allow POS browser clients (served from cloud origin) to post to the local relay
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Relay-Client-Key"
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
                "relay_client_auth_required": str(request.form.get("relay_client_auth_required") or "").strip().lower() in ("1", "true", "on", "yes"),
                "relay_client_auth_key": (request.form.get("relay_client_auth_key") or "").strip(),
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

    @app.route("/api/outbox/cleanup", methods=["POST", "OPTIONS"])
    def api_outbox_cleanup():
        if request.method == "OPTIONS":
            return ("", 204)
        # Cleanup is local-operator tooling; require loopback caller plus relay auth if enabled.
        if not _client_ip() or _client_ip() not in ("127.0.0.1", "::1"):
            return _json_error("LOOPBACK_REQUIRED", "Outbox cleanup is allowed only from localhost.", 403)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        result = cleanup_outbox_rows(
            limit=int(payload.get("limit") or 200),
            statuses=payload.get("statuses") or [],
            event_types=payload.get("event_types") or [],
            created_before=payload.get("created_before") or "",
            error_contains=payload.get("error_contains") or "",
            local_ref_contains=payload.get("local_ref_contains") or "",
            delete=bool(payload.get("delete")),
        )
        return jsonify({"ok": True, **result})

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
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["token_create"])
        if role_err:
            return role_err
        if isinstance(payload, dict):
            payload.setdefault("_relay_source", _request_source_meta())
        event_id = enqueue_event("token_create", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/pick", methods=["POST"])
    def relay_pick():
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["pick_update"])
        if role_err:
            return role_err
        if isinstance(payload, dict):
            payload.setdefault("_relay_source", _request_source_meta())
        event_id = enqueue_event("pick_update", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/release", methods=["POST"])
    def relay_release():
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["dispatch_release"])
        if role_err:
            return role_err
        if isinstance(payload, dict):
            payload.setdefault("_relay_source", _request_source_meta())
        event_id = enqueue_event("dispatch_release", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/submit-invoice", methods=["POST", "OPTIONS"])
    def relay_submit_invoice():
        if request.method == "OPTIONS":
            return ("", 204)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err

        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["commit_invoice"])
        if role_err:
            return role_err
        if isinstance(payload, dict):
            payload.setdefault("_relay_source", _request_source_meta())
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
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err

        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["token_create"])
        if role_err:
            return role_err
        expiry_minutes = int(payload.get("expiry_minutes") or 120)
        source_meta = _request_source_meta()
        token = create_token(payload, expiry_minutes=expiry_minutes, source_meta=source_meta)

        outbox_event_id = enqueue_outbox_event(
            "TOKEN_CREATED",
            {
                "token_id": token.get("token_id"),
                "payload": payload,
            },
            local_ref=token.get("token_id"),
            source_meta=source_meta,
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

    @app.route("/relay/tokens/search", methods=["GET"])
    def relay_tokens_search_v2():
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err

        pos_profile_id = (request.args.get("pos_profile_id") or "").strip() or None
        search = (request.args.get("q") or request.args.get("search") or "").strip() or None
        limit = int(request.args.get("limit") or 100)
        limit = max(1, min(500, limit))

        raw_statuses = []
        raw_statuses.extend(request.args.getlist("status"))
        raw_statuses.extend(request.args.getlist("statuses"))
        if not raw_statuses:
            csv = (request.args.get("statuses_csv") or request.args.get("statuses") or "").strip()
            if csv:
                raw_statuses.extend(csv.split(","))
        statuses = [str(s).strip() for s in raw_statuses if str(s).strip()]

        try:
            max_age_days = max(0, int(request.args.get("max_age_days") or 1))
        except Exception:
            max_age_days = 1
        try:
            history_days = max(max_age_days, int(request.args.get("history_days") or 30))
        except Exception:
            history_days = max(max_age_days, 30)
        allow_stale = str(request.args.get("allow_stale") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        rows = list_relay_tokens(
            pos_profile_id=pos_profile_id,
            search=search,
            statuses=statuses,
            limit=limit,
            max_age_days=max_age_days,
            allow_stale=allow_stale,
            history_days=history_days,
        )
        return jsonify(
            {
                "ok": True,
                "rows": rows,
                "count": len(rows),
                "policy": {
                    "max_age_days": max_age_days,
                    "allow_stale": 1 if allow_stale else 0,
                    "history_days": history_days,
                },
            }
        )

    @app.route("/relay/quote/create", methods=["POST", "OPTIONS"])
    def relay_quote_create_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["quote_action"])
        if role_err:
            return role_err

        valid_until = str(payload.get("valid_until") or "").strip()
        if not valid_until:
            try:
                validity_days = max(1, int(payload.get("validity_days") or 7))
            except Exception:
                validity_days = 7
            from datetime import datetime as _dt, timedelta as _td

            valid_until = (_dt.utcnow() + _td(days=validity_days)).date().isoformat()
            payload["valid_until"] = valid_until
        try:
            quote = upsert_local_quote(payload, source_meta=_request_source_meta())
        except Exception as exc:
            return jsonify({"ok": False, "code": "QUOTE_CREATE_FAILED", "message": str(exc)}), 400

        outbox_event_id = enqueue_outbox_event(
            "QUOTE_UPSERT",
            {
                "quote_id": quote.get("quote_id"),
                "payload": payload,
            },
            local_ref=quote.get("quote_id"),
            source_meta=_request_source_meta(),
        )
        return jsonify({"ok": True, "quote": quote, "outbox_event_id": outbox_event_id})

    @app.route("/relay/quotes/search", methods=["GET"])
    def relay_quotes_search_v2():
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        pos_profile_id = (request.args.get("pos_profile_id") or "").strip() or None
        search = (request.args.get("q") or request.args.get("search") or "").strip() or None
        limit = int(request.args.get("limit") or 100)
        limit = max(1, min(500, limit))

        raw_statuses = []
        raw_statuses.extend(request.args.getlist("status"))
        raw_statuses.extend(request.args.getlist("statuses"))
        if not raw_statuses:
            csv = (request.args.get("statuses_csv") or request.args.get("statuses") or "").strip()
            if csv:
                raw_statuses.extend(csv.split(","))
        statuses = [str(s).strip() for s in raw_statuses if str(s).strip()]

        try:
            max_age_days = max(0, int(request.args.get("max_age_days") or 7))
        except Exception:
            max_age_days = 7
        try:
            history_days = max(max_age_days, int(request.args.get("history_days") or 30))
        except Exception:
            history_days = max(max_age_days, 30)
        allow_stale = str(request.args.get("allow_stale") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        rows = list_local_quotes(
            pos_profile_id=pos_profile_id,
            search=search,
            statuses=statuses,
            limit=limit,
            max_age_days=max_age_days,
            allow_stale=allow_stale,
            history_days=history_days,
        )
        return jsonify(
            {
                "ok": True,
                "rows": rows,
                "count": len(rows),
                "policy": {
                    "max_age_days": max_age_days,
                    "allow_stale": 1 if allow_stale else 0,
                    "history_days": history_days,
                },
            }
        )

    @app.route("/relay/quote/reprice-preview", methods=["POST", "OPTIONS"])
    def relay_quote_reprice_preview_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["quote_action"])
        if role_err:
            return role_err
        quote_id = str(payload.get("quote_id") or "").strip()
        if not quote_id:
            return jsonify({"ok": False, "code": "QUOTE_ID_REQUIRED"}), 400
        result = preview_local_quote_reprice(quote_id)
        if not result.get("ok"):
            return jsonify(result), 404 if result.get("code") == "QUOTE_NOT_FOUND" else 409
        return jsonify(result)

    @app.route("/relay/quote/convert-to-token", methods=["POST", "OPTIONS"])
    def relay_quote_convert_to_token_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["quote_action"])
        if role_err:
            return role_err
        quote_id = str(payload.get("quote_id") or "").strip()
        if not quote_id:
            return jsonify({"ok": False, "code": "QUOTE_ID_REQUIRED"}), 400

        result = convert_local_quote_to_token(
            quote_id=quote_id,
            cashier_user_id=payload.get("cashier_user_id"),
            role=payload.get("role"),
            confirm_reprice=payload.get("confirm_reprice"),
            source_meta=_request_source_meta(),
        )
        if not result.get("ok"):
            code = result.get("code")
            if code == "QUOTE_NOT_FOUND":
                return jsonify(result), 404
            if code == "QUOTE_REPRICE_CONFIRM_REQUIRED":
                return jsonify(result), 409
            if code == "QUOTE_EXPIRED":
                return jsonify(result), 409
            return jsonify(result), 400

        quote = get_local_quote(quote_id)
        token = result.get("token") or {}
        token_outbox_event_id = enqueue_outbox_event(
            "TOKEN_CREATED",
            {
                "token_id": token.get("token_id"),
                "payload": {
                    "pos_profile_id": (quote or {}).get("pos_profile_id"),
                    "customer_id": (quote or {}).get("customer_id"),
                    "customer_name": (quote or {}).get("customer_name"),
                },
            },
            local_ref=token.get("token_id"),
            source_meta=_request_source_meta(),
        )
        quote_outbox_event_id = enqueue_outbox_event(
            "QUOTE_UPSERT",
            {
                "quote_id": quote_id,
                "payload": (quote or {}).get("payload") or {},
            },
            local_ref=quote_id,
            source_meta=_request_source_meta(),
        )

        return jsonify(
            {
                "ok": True,
                "quote_id": quote_id,
                "quote": quote,
                "token": token,
                "preview": result.get("preview") or {},
                "outbox_event_id": token_outbox_event_id,
                "quote_outbox_event_id": quote_outbox_event_id,
            }
        )

    @app.route("/relay/token/<token_id>/void", methods=["POST", "OPTIONS"])
    def relay_token_void_v2(token_id):
        if request.method == "OPTIONS":
            return ("", 204)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["token_void"], role_field="supervisor role")
        if role_err:
            return role_err
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
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["session_cashier"])
        if role_err:
            return role_err
        source_meta = _request_source_meta()
        session = open_cashier_session(payload, source_meta=source_meta)
        outbox_event_id = enqueue_outbox_event(
            "SESSION_OPEN",
            payload,
            local_ref=session.get("session_id"),
            source_meta=source_meta,
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
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["session_cashier"])
        if role_err:
            return role_err
        session_id = payload.get("session_id")
        if not session_id:
            return jsonify({"ok": False, "code": "SESSION_ID_REQUIRED"}), 400

        result = close_cashier_session(session_id, close_note=payload.get("close_note"))
        if result.get("ok"):
            source_meta = _request_source_meta()
            outbox_event_id = enqueue_outbox_event(
                "SESSION_CLOSE",
                payload,
                local_ref=session_id,
                source_meta=source_meta,
            )
            result["outbox_event_id"] = outbox_event_id
        status_code = 200 if result.get("ok") else 404
        return jsonify(result), status_code

    @app.route("/relay/customer/upsert", methods=["POST", "OPTIONS"])
    def relay_customer_upsert_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["fulfillment_any"])
        if role_err:
            return role_err
        source_meta = _request_source_meta()
        customer = upsert_customer(payload)
        outbox_event_id = enqueue_outbox_event(
            "CUSTOMER_UPSERT",
            payload,
            local_ref=customer.get("customer_id"),
            source_meta=source_meta,
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
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["fulfillment_any"])
        if role_err:
            return role_err
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
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err
        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["fulfillment_any"])
        if role_err:
            return role_err
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
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err

        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["commit_invoice"])
        if role_err:
            return role_err
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

        source_meta = _request_source_meta()
        commit_result = commit_invoice_atomic(payload, source_meta=source_meta)
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
                source_meta=source_meta,
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

    @app.route("/relay/workflow/monitor-board", methods=["GET"])
    def relay_workflow_monitor_board_v2():
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err

        pos_profile_id = (request.args.get("pos_profile") or request.args.get("pos_profile_id") or "").strip() or None
        business_date = (request.args.get("business_date") or "").strip() or None
        mine_only = str(request.args.get("mine_only") or "").strip().lower() in ("1", "true", "yes", "on")
        include_released = str(request.args.get("include_released") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        user_id = (request.args.get("user_id") or "").strip() or None
        limit = int(request.args.get("limit_page_length") or request.args.get("limit") or 200)
        limit = max(1, min(500, limit))

        board = get_relay_monitor_board(
            pos_profile_id=pos_profile_id,
            business_date=business_date,
            mine_only=mine_only,
            user_id=user_id,
            include_released=include_released,
            limit=limit,
        )
        return jsonify({"ok": True, **board})

    @app.route("/relay/pick/update", methods=["POST", "OPTIONS"])
    def relay_pick_update_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err

        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["pick_update"])
        if role_err:
            return role_err
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
            source_meta=_request_source_meta(),
        )
        if result.get("ok"):
            source_meta = _request_source_meta()
            outbox_event_id = enqueue_outbox_event(
                "PICK_EVENT",
                payload,
                local_ref=local_sale_ref,
                source_meta=source_meta,
            )
            result["outbox_event_id"] = outbox_event_id
        status_code = 200 if result.get("ok") else 409
        return jsonify(result), status_code

    @app.route("/relay/dispatch/release", methods=["POST", "OPTIONS"])
    def relay_dispatch_release_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err

        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["dispatch_release"])
        if role_err:
            return role_err
        local_sale_ref = payload.get("local_sale_ref")
        if not local_sale_ref:
            return jsonify({"ok": False, "code": "LOCAL_SALE_REF_REQUIRED"}), 400
        proof_ack_name = str(payload.get("proof_ack_name") or "").strip()
        proof_mode = str(payload.get("proof_mode") or "").strip().lower()
        line_snapshot = payload.get("line_snapshot") if isinstance(payload.get("line_snapshot"), list) else []
        if not proof_ack_name:
            return (
                jsonify(
                    {
                        "ok": False,
                        "code": "DISPATCH_PROOF_ACK_REQUIRED",
                        "message": "proof_ack_name is required",
                    }
                ),
                400,
            )
        if proof_mode not in ("counter", "delivery", "other"):
            return (
                jsonify(
                    {
                        "ok": False,
                        "code": "DISPATCH_PROOF_MODE_REQUIRED",
                        "message": "proof_mode must be one of counter|delivery|other",
                    }
                ),
                400,
            )
        if not line_snapshot:
            return (
                jsonify(
                    {
                        "ok": False,
                        "code": "DISPATCH_LINE_SNAPSHOT_REQUIRED",
                        "message": "line_snapshot is required",
                    }
                ),
                400,
            )

        result = release_sale(
            local_sale_ref=local_sale_ref,
            dispatcher_user_id=payload.get("dispatcher_user_id"),
            allow_partial=bool(payload.get("allow_partial")),
            notes=payload.get("notes"),
            payload=payload,
            source_meta=_request_source_meta(),
        )
        if result.get("ok"):
            source_meta = _request_source_meta()
            outbox_event_id = enqueue_outbox_event(
                "RELEASE_EVENT",
                payload,
                local_ref=local_sale_ref,
                source_meta=source_meta,
            )
            result["outbox_event_id"] = outbox_event_id
        status_code = 200 if result.get("ok") else 409
        return jsonify(result), status_code

    @app.route("/relay/dispatch/mismatch", methods=["POST", "OPTIONS"])
    def relay_dispatch_mismatch_v2():
        if request.method == "OPTIONS":
            return ("", 204)
        auth_err = _require_relay_client_auth()
        if auth_err:
            return auth_err

        payload = request.get_json(silent=True) or {}
        role_err = _require_relay_role(payload, RELAY_ROLE_GROUPS["dispatch_mismatch"])
        if role_err:
            return role_err

        local_sale_ref = str(payload.get("local_sale_ref") or "").strip()
        if not local_sale_ref:
            return jsonify({"ok": False, "code": "LOCAL_SALE_REF_REQUIRED"}), 400

        reason_code = str(payload.get("reason_code") or "").strip().upper()
        reason_text = str(payload.get("reason_text") or "").strip()
        if not reason_code and not reason_text:
            return (
                jsonify(
                    {
                        "ok": False,
                        "code": "MISMATCH_REASON_REQUIRED",
                        "message": "reason_code or reason_text is required",
                    }
                ),
                400,
            )

        result = flag_dispatch_mismatch(
            local_sale_ref=local_sale_ref,
            dispatcher_user_id=payload.get("dispatcher_user_id"),
            reason_code=reason_code,
            reason_text=reason_text,
            requires_cashier_adjustment=bool(payload.get("requires_cashier_adjustment")),
            payload=payload,
            source_meta=_request_source_meta(),
        )
        if result.get("ok"):
            outbox_payload = {
                "local_sale_ref": local_sale_ref,
                "sales_invoice": payload.get("sales_invoice") or payload.get("cloud_invoice_name") or "",
                "pos_profile_id": payload.get("pos_profile_id") or payload.get("pos_profile") or "",
                "picking_status": "PICK_EXCEPTION",
                "notes": reason_text or payload.get("notes") or "",
                "source": "dispatch_mismatch",
            }
            outbox_event_id = enqueue_outbox_event(
                "PICK_EVENT",
                outbox_payload,
                local_ref=local_sale_ref,
                source_meta=_request_source_meta(),
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

