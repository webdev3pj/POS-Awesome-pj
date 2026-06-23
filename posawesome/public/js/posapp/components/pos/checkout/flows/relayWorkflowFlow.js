export default {
  methods: {
    normalize_relay_url(relayUrl) {
      return String(relayUrl || "").trim().replace(/\/$/, "");
    },

    relay_config_storage_key() {
      const site =
        (frappe.boot && (frappe.boot.sitename || frappe.boot.site_name)) ||
        window.location.host ||
        "site";
      const profile =
        String((this.pos_profile && this.pos_profile.name) || "default").trim() || "default";
      return `posa_edge_relay_config:${site}:${profile}`;
    },

    relay_default_config_storage_key() {
      const site =
        (frappe.boot && (frappe.boot.sitename || frappe.boot.site_name)) ||
        window.location.host ||
        "site";
      return `posa_edge_relay_config:${site}:__default__`;
    },

    get_browser_relay_config() {
      try {
        const raw =
          localStorage.getItem(this.relay_config_storage_key()) ||
          localStorage.getItem(this.relay_default_config_storage_key());
        if (!raw) return null;
        const parsed = JSON.parse(raw) || {};
        const relayUrl = this.normalize_relay_url(parsed.relay_url);
        if (!relayUrl) return null;
        return { relay_url: relayUrl };
      } catch (e) {
        return null;
      }
    },

    get_relay_base_url() {
      const browserConfig = this.get_browser_relay_config();
      const raw =
        (browserConfig && browserConfig.relay_url) ||
        (this.relay_status && this.relay_status.profile_relay_url) ||
        (this.relay_status && this.relay_status.relay_url) ||
        "";
      return this.normalize_relay_url(raw);
    },

    so_lookup_policy() {
      const maxAgeDays = Math.max(
        0,
        Number((this.pos_profile && this.pos_profile.posa_sales_order_lookup_max_age_days) || 1) ||
          1
      );
      const allowStale =
        Number((this.pos_profile && this.pos_profile.posa_allow_stale_sales_order_fetch) || 0) ===
        1;
      const historyDays = Math.max(
        maxAgeDays,
        Number((this.pos_profile && this.pos_profile.posa_stale_sales_order_history_days) || 30) ||
          30
      );
      return { maxAgeDays, allowStale, historyDays };
    },

    get_relay_client_headers(extra = {}) {
      const headers = { ...extra };
      try {
        const relayKey = (localStorage.getItem("posa_relay_client_key") || "").trim();
        if (relayKey) headers["X-Relay-Client-Key"] = relayKey;
      } catch (e) {}
      return headers;
    },

    get_explicit_token_ref(source = {}) {
      const doc = source || {};
      const line =
        (Array.isArray(doc.items) ? doc.items.find((row) => row && row.sales_order) : null) || {};
      return String(
        doc.token_id ||
          doc.sales_order ||
          doc.sales_order_name ||
          line.sales_order ||
          ""
      ).trim();
    },

    relay_customer_fallback_enabled() {
      return this.relayWorkflowEnabled() && !!this.get_relay_base_url();
    },

    is_click_event(payload) {
      return !!(payload && typeof payload === "object" && payload.target && payload.preventDefault);
    },

    relayWorkflowEnabled() {
      return this.token_workflow_enabled;
    },

    normalize_relay_token_to_order_doc(row = {}) {
      const createdAt = String(row.created_at || "").trim();
      const transactionDate = createdAt
        ? createdAt.replace("T", " ").slice(0, 10)
        : frappe.datetime.nowdate();
      const items = (row.items || []).map((line, idx) => {
        const payload = line && line.payload && typeof line.payload === "object" ? line.payload : {};
        const qty = flt(line.qty || payload.qty || 0);
        const rate = flt(line.rate || payload.rate || 0);
        return {
          item_code: line.item_code || payload.item_code,
          item_name: line.item_name || payload.item_name || line.item_code || "",
          qty: qty,
          rate: rate,
          amount: flt(line.amount || payload.amount || qty * rate),
          uom: line.uom || payload.uom || "",
          conversion_factor: flt(
            typeof payload.conversion_factor === "undefined" ? 1 : payload.conversion_factor || 1
          ),
          serial_no: payload.serial_no || "",
          batch_no: payload.batch_no || "",
          discount_percentage: flt(payload.discount_percentage || 0),
          discount_amount: flt(payload.discount_amount || 0),
          price_list_rate: flt(payload.price_list_rate || rate),
          posa_notes: payload.posa_notes || "",
          posa_delivery_date: payload.posa_delivery_date || "",
          posa_offers: payload.posa_offers || [],
          posa_offer_applied: !!payload.posa_offer_applied,
          posa_is_offer: !!payload.posa_is_offer,
          posa_is_replace: !!payload.posa_is_replace,
          is_free_item: !!payload.is_free_item,
          posa_row_id: payload.posa_row_id || `${row.token_id || "TOKEN"}-${idx + 1}`,
          sales_order: row.token_id || "",
          sales_order_name: row.token_id || "",
        };
      });
      const grandTotal = flt(row.grand_total || 0);
      return {
        name: row.token_id || "",
        doctype: "Sales Order",
        relay_offline_order: 1,
        relay_token_status: row.status || "TOKEN_OPEN",
        token_id: row.token_id || "",
        sales_order: row.token_id || "",
        sales_order_name: row.token_id || "",
        posa_order_name: row.order_name || row.posa_order_name || "",
        order_name: row.order_name || row.posa_order_name || "",
        customer: row.customer_id || row.customer_name || "",
        customer_name: row.customer_name || row.customer_id || "",
        company: this.pos_profile.company,
        currency: this.pos_profile.currency,
        pos_profile: this.pos_profile.name,
        posting_date: transactionDate,
        transaction_date: transactionDate,
        grand_total: grandTotal,
        rounded_total: flt(row.rounded_total || grandTotal),
        net_total: flt(row.net_total || grandTotal),
        total: flt(row.total || grandTotal),
        discount_amount: 0,
        additional_discount_percentage: 0,
        posa_offers: [],
        posa_coupons: [],
        items: items,
      };
    },

    async fetch_open_orders_from_relay(searchText = "") {
      const base = this.get_relay_base_url();
      if (!base) {
        throw new Error(__("Relay URL is not configured."));
      }
      const policy = this.so_lookup_policy();
      const params = new URLSearchParams();
      params.set("limit", "100");
      params.set("statuses_csv", "TOKEN_OPEN");
      params.set("max_age_days", String(policy.maxAgeDays));
      params.set("allow_stale", policy.allowStale ? "1" : "0");
      params.set("history_days", String(policy.historyDays));
      if (searchText) params.set("search", searchText);
      const resp = await fetch(`${base}/relay/tokens/search?${params.toString()}`, {
        method: "GET",
        headers: this.get_relay_client_headers({ Accept: "application/json" }),
      });
      let body = {};
      try {
        body = (await resp.json()) || {};
      } catch (e) {
        body = {};
      }
      if (!resp.ok || body.ok === false) {
        throw new Error(body.message || __("Unable to load Sales Orders from relay."));
      }
      return (body.rows || []).map((row) => this.normalize_relay_token_to_order_doc(row));
    },

    merge_sales_order_rows(cloudRows = [], relayRows = []) {
      const seen = new Set();
      const keyFor = (row) =>
        String(
          (row && (row.token_id || row.sales_order_name || row.sales_order || row.name)) || ""
        ).trim();
      const merged = [];
      (cloudRows || []).forEach((row) => {
        const key = keyFor(row);
        if (key) seen.add(key);
        merged.push(row);
      });
      (relayRows || []).forEach((row) => {
        const key = keyFor(row);
        if (key && seen.has(key)) return;
        if (key) seen.add(key);
        merged.push(row);
      });
      return merged;
    },

    apply_relay_customer_info(row) {
      let payload = (row && row.payload) || {};
      if (typeof payload === "string") {
        try {
          payload = JSON.parse(payload) || {};
        } catch (e) {
          payload = {};
        }
      }
      const customerId =
        payload.customer_id || payload.name || (row && row.customer_id) || this.customer;
      this.customer_info = {
        loyalty_points:
          typeof payload.loyalty_points === "undefined" ? null : payload.loyalty_points,
        conversion_factor:
          typeof payload.conversion_factor === "undefined" ? null : payload.conversion_factor,
        email_id: payload.email_id || (row && row.email_id) || "",
        mobile_no: payload.mobile_no || (row && row.mobile_no) || "",
        image: payload.image || "",
        loyalty_program: payload.loyalty_program || null,
        customer_price_list: payload.customer_price_list || null,
        customer_group: payload.customer_group || "",
        customer_type: payload.customer_type || "Individual",
        territory: payload.territory || "",
        birthday: payload.birthday || null,
        gender: payload.gender || "",
        tax_id: payload.tax_id || (row && row.tax_id) || "",
        posa_discount: payload.posa_discount || 0,
        name: customerId,
        customer_name: payload.customer_name || (row && row.customer_name) || customerId,
        customer_group_price_list: payload.customer_group_price_list || null,
        primary_address: payload.primary_address || "",
      };
      this.update_price_list();
      return true;
    },

    async fetch_customer_details_from_relay() {
      if (!this.customer || !this.relay_customer_fallback_enabled()) {
        return false;
      }
      const base = this.get_relay_base_url();
      try {
        const resp = await fetch(
          `${base}/relay/customer/search?q=${encodeURIComponent(this.customer)}&limit=20`,
          {
            method: "GET",
            headers: this.get_relay_client_headers({
              Accept: "application/json",
            }),
          }
        );
        const payload = await resp.json();
        if (!resp.ok || !payload.ok) {
          return false;
        }
        const rows = payload.rows || [];
        const row =
          rows.find((r) => r.customer_id === this.customer) ||
          rows.find(
            (r) => ((r.payload || {}).name || (r.payload || {}).customer_id) === this.customer
          ) ||
          rows[0];
        if (!row) {
          return false;
        }
        return this.apply_relay_customer_info(row);
      } catch (e) {
        return false;
      }
    },
  },
};
