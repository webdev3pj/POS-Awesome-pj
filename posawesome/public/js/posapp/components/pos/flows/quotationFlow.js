import { evntBus } from "../../../bus";

export default {
  methods: {
    get_quotation_payload() {
      const payload = this.get_sales_order_token_payload();
      payload.valid_till = frappe.datetime.add_days(
        payload.posting_date || frappe.datetime.nowdate(),
        Math.max(
          1,
          Number((this.pos_profile && this.pos_profile.posa_quotation_validity_days) || 7) || 7
        )
      );
      return payload;
    },

    create_quotation_token_cloud(payload) {
      return new Promise((resolve, reject) => {
        frappe.call({
          method: "posawesome.posawesome.api.posapp.create_quotation_token",
          args: { data: payload },
          async: true,
          callback: (r) => {
            if (r && r.exc) {
              reject(new Error(__("Unable to create Quotation.")));
              return;
            }
            if (!r || !r.message) {
              reject(new Error(__("Empty response while creating Quotation.")));
              return;
            }
            resolve(r.message);
          },
          error: (err) => {
            const message =
              (err && err.message) || __("Unable to create Quotation. Please try again.");
            reject(new Error(message));
          },
        });
      });
    },

    async create_quotation_token_relay_local(payload) {
      const relayBaseUrl = this.get_relay_base_url();
      if (!relayBaseUrl) {
        throw new Error(__("Relay URL is not configured for offline Quotations."));
      }
      const validityDays = Math.max(
        1,
        Number((this.pos_profile && this.pos_profile.posa_quotation_validity_days) || 7) || 7
      );
      const quotePayload = {
        pos_profile_id: this.pos_profile.name,
        created_by: frappe.session.user,
        customer_id: this.customer,
        customer_name:
          (this.customer_info && this.customer_info.customer_name) || this.customer,
        currency: this.pos_profile.currency,
        valid_until:
          payload.valid_till ||
          frappe.datetime.add_days(payload.posting_date || frappe.datetime.nowdate(), validityDays),
        validity_days: validityDays,
        role: this.current_role || this.get_current_role() || "",
        items: (this.items || []).map((item) => ({
          item_code: item.item_code,
          item_name: item.item_name || item.item_code,
          qty: flt(item.qty),
          uom: item.uom,
          rate: flt(item.rate),
          amount: flt(item.qty) * flt(item.rate),
          conversion_factor: flt(
            typeof item.conversion_factor === "undefined" ? 1 : item.conversion_factor || 1
          ),
          serial_no: item.serial_no || "",
          batch_no: item.batch_no || "",
          discount_percentage: flt(item.discount_percentage || 0),
          discount_amount: flt(item.discount_amount || 0),
          price_list_rate: flt(item.price_list_rate || item.rate || 0),
          posa_notes: item.posa_notes || "",
          posa_delivery_date: item.posa_delivery_date || "",
          posa_row_id: item.posa_row_id,
        })),
      };

      const resp = await fetch(`${relayBaseUrl}/relay/quote/create`, {
        method: "POST",
        headers: this.get_relay_client_headers({ "Content-Type": "application/json" }),
        body: JSON.stringify(quotePayload),
      });
      let body = {};
      try {
        body = (await resp.json()) || {};
      } catch (e) {
        body = {};
      }
      if (!resp.ok || !body.ok || !body.quote) {
        throw new Error(body.message || __("Unable to create Quotation on local relay."));
      }
      return {
        quote_name: body.quote.quote_id,
        valid_till: body.quote.valid_until || quotePayload.valid_until,
        is_expired: 0,
        age_days: Number(body.quote.order_age_days || 0),
        grand_total: Number(body.quote.base_total || 0),
        currency: body.quote.currency || this.pos_profile.currency,
        local_only: 1,
        relay_quote: body.quote,
      };
    },

    async save_quote() {
      this.current_role = this.get_current_role();
      if (!this.can_use_quotation_actions) {
        evntBus.$emit("show_mesage", {
          text: __("Quotation actions are disabled for this role/profile."),
          color: "warning",
        });
        return null;
      }
      if (!this.customer) {
        evntBus.$emit("show_mesage", { text: __(`There is no Customer !`), color: "error" });
        return null;
      }
      if (!this.items.length) {
        evntBus.$emit("show_mesage", { text: __(`There is no Items !`), color: "error" });
        return null;
      }
      if (!this.validate()) {
        return null;
      }

      const payload = this.get_quotation_payload();
      try {
        let result = null;
        let usedRelayFallback = false;
        try {
          result = await this.create_quotation_token_cloud(payload);
        } catch (cloudErr) {
          if (!this.relayWorkflowEnabled() || !this.get_relay_base_url()) {
            throw cloudErr;
          }
          result = await this.create_quotation_token_relay_local(payload);
          usedRelayFallback = true;
        }
        const quoteName = result.quote_name || result.name || "";
        const validTill = result.valid_till || "";
        evntBus.$emit("show_mesage", {
          text: usedRelayFallback
            ? __("Quotation {0} created on relay (offline mode). Valid till: {1}", [
                quoteName,
                validTill || "-",
              ])
            : __("Quotation {0} created. Valid till: {1}", [quoteName, validTill || "-"]),
          color: usedRelayFallback ? "warning" : "success",
        });
        this.reset_after_token_save();
        return result;
      } catch (e) {
        evntBus.$emit("show_mesage", {
          text: (e && e.message) || __("Unable to create Quotation."),
          color: "error",
        });
        return null;
      }
    },

    async fetch_quotes_from_relay(searchText = "") {
      const base = this.get_relay_base_url();
      if (!base) throw new Error(__("Relay URL is not configured."));
      const policy = this.so_lookup_policy();
      const params = new URLSearchParams();
      params.set("pos_profile_id", this.pos_profile.name || "");
      params.set("limit", "100");
      params.set("statuses_csv", "OPEN");
      params.set("max_age_days", String(policy.maxAgeDays));
      params.set("allow_stale", policy.allowStale ? "1" : "0");
      params.set("history_days", String(policy.historyDays));
      if (searchText) params.set("search", searchText);
      const resp = await fetch(`${base}/relay/quotes/search?${params.toString()}`, {
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
        throw new Error(body.message || __("Unable to load Quotations from relay."));
      }
      return body.rows || [];
    },
  },
};
