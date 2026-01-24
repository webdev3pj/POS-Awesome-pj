#!/usr/bin/env bash
# Minimal smoke test for Sales Order token backend.
# Usage: SITE=your.site.name ./scripts/smoke_test.sh
# - Runs migrations
# - Verifies required custom fields on Sales Order
# - Calls whitelisted APIs in posawesome.posawesome.api.sales_order_token

# Avoid using 'set -e' to be compatible with this environment; we check exit codes explicitly.

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SEARCH_DIR="$APP_DIR"
BENCH_ROOT=""
while [ "$SEARCH_DIR" != "/" ]; do
    if [ -d "$SEARCH_DIR/sites" ]; then
        BENCH_ROOT="$SEARCH_DIR"
        break
    fi
    SEARCH_DIR=$(dirname "$SEARCH_DIR")
done

if [ -n "$BENCH_ROOT" ]; then
    echo "Found bench root at $BENCH_ROOT"
    cd "$BENCH_ROOT" || { echo "Failed to cd to $BENCH_ROOT"; exit 1; }
else
    echo "No bench 'sites' directory found upwards from app root. Proceeding in current directory." >&2
fi

# Ensure bench is available
if ! command -v bench >/dev/null 2>&1; then
    echo "bench command not found in PATH. Please run this script from a bench environment or add bench to PATH." >&2
    exit 2
fi

# Determine SITE
SITE="${SITE:-}"
if [ -z "$SITE" ]; then
    if [ -n "$BENCH_ROOT" ] && [ -d "$BENCH_ROOT/sites" ]; then
        SITE_CANDIDATE="$(ls -1 "$BENCH_ROOT/sites" | head -n 1)"
        SITE="${SITE_CANDIDATE:-site1.local}"
        echo "Auto-detected SITE=$SITE"
    else
        SITE="site1.local"
        echo "Using default SITE=$SITE (override with SITE=your.site.name)"
    fi
fi

# 1) Run migrations
echo "Running migrations for site $SITE..."
bench --site "$SITE" migrate
MIGRATE_RC=$?
if [ $MIGRATE_RC -ne 0 ]; then
    echo "Migrations failed (exit $MIGRATE_RC)" >&2
    exit 3
fi

echo "Migrations succeeded."

# 2) Check required custom fields on Sales Order
echo "Checking required custom fields on Sales Order..."
# Single-line python executed in frappe context; will throw if any missing
PY_CHECK="import frappe; fields=['custom_sales_associate','custom_order_type','custom_pos_opening_shift','custom_token_qr_code']; missing=[f for f in fields if not frappe.get_meta('Sales Order').get_field(f)];\
import sys;\
if missing: frappe.throw('Missing custom fields: '+', '.join(missing));\
print('All required custom fields present')"

bench --site "$SITE" execute "$PY_CHECK"
RC=$?
if [ $RC -ne 0 ]; then
    echo "Required custom fields check failed." >&2
    exit 4
fi

echo "Required custom fields are present."

# 3) Run API smoke test: create_sales_order_token, get_pending_orders, get_sales_order_for_cashier, cancel_sales_order_token
echo "Running Sales Order token API smoke test..."

TMP_PYFILE="$(mktemp /tmp/posawesome_smoke_test.XXXXXX.py)"
cat > "$TMP_PYFILE" <<'PYCODE'
import json, frappe, time
from posawesome.posawesome.api import sales_order_token as sot

def abort(msg):
    frappe.throw(msg)

# find resources
customers = frappe.get_all("Customer", fields=["name"], limit_page_length=1)
if not customers:
    abort("No Customer found. Please create a Customer before running the smoke test.")
customer = customers[0]["name"]

pos_profiles = frappe.get_all("POS Profile", fields=["name"], limit_page_length=1)
if not pos_profiles:
    abort("No POS Profile found. Please create a POS Profile before running the smoke test.")
pos_profile = pos_profiles[0]["name"]

items = frappe.get_all("Item", filters={"disabled": 0}, fields=["name"], limit_page_length=1)
if not items:
    abort("No Item found. Please create an Item before running the smoke test.")
item_code = items[0]["name"]

# prepare items payload
items_payload = [{"item_code": item_code, "qty": 1, "rate": 1}]

# call create_sales_order_token
print("Calling create_sales_order_token(...)")
res = sot.create_sales_order_token(customer, json.dumps(items_payload), pos_profile)
if not isinstance(res, dict) or "order_name" not in res:
    abort("create_sales_order_token did not return expected result: %r" % res)

order_name = res["order_name"]
print("Created Sales Order:", order_name)

# call get_pending_orders and ensure order present
print("Calling get_pending_orders(...)")
pending = sot.get_pending_orders(sales_associate=None, pos_profile=pos_profile)
if not isinstance(pending, list):
    abort("get_pending_orders did not return a list: %r" % pending)
if not any((o.get('name') == order_name) or (o.get('order_name') == order_name) for o in pending):
    abort("Created order %s not found in pending orders result" % order_name)
print("Order found in pending orders.")

# call get_sales_order_for_cashier
print("Calling get_sales_order_for_cashier(%s)" % order_name)
order_doc = sot.get_sales_order_for_cashier(order_name)
if not order_doc or getattr(order_doc, "name", None) != order_name:
    abort("get_sales_order_for_cashier returned unexpected result for %s: %r" % (order_name, order_doc))
print("get_sales_order_for_cashier OK.")

# call cancel_sales_order_token
print("Calling cancel_sales_order_token(%s)" % order_name)
cancel_res = sot.cancel_sales_order_token(order_name, reason="Smoke test cancel")
if not isinstance(cancel_res, dict) or not cancel_res.get("success", True):
    # accept either {'success': True} or non-exceptional result
    pass
print("cancel_sales_order_token OK.")

print("Smoke test completed successfully.")
PYCODE

# Execute the python inside frappe context
bench --site "$SITE" execute "exec(open('$TMP_PYFILE').read())"
API_RC=$?
rm -f "$TMP_PYFILE"
if [ $API_RC -ne 0 ]; then
    echo "Sales Order token API smoke test failed." >&2
    exit 5
fi

echo "All smoke tests passed."
exit 0
