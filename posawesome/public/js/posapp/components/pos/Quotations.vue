<template>
  <v-row justify="center">
    <v-dialog v-model="quotesDialog" max-width="980px">
      <v-card>
        <v-card-title>
          <span class="headline primary--text">{{ __("Select Quotations") }}</span>
        </v-card-title>
        <v-card-text class="pa-0">
          <v-container>
            <v-row class="mb-4">
              <v-text-field
                color="primary"
                :label="frappe._('Quote ID')"
                background-color="white"
                hide-details
                v-model="quote_name"
                dense
                clearable
                class="mx-4"
              ></v-text-field>
              <v-btn text class="ml-2" color="primary" dark @click="search_quotations">
                {{ __("Search") }}
              </v-btn>
            </v-row>
            <v-row no-gutters>
              <v-col cols="12" class="pa-1">
                <v-data-table
                  :headers="headers"
                  :items="dialog_data"
                  item-key="name"
                  class="elevation-1"
                  :single-select="singleSelect"
                  show-select
                  v-model="selected"
                >
                  <template v-slot:item.grand_total="{ item }">
                    {{ currencySymbol(item.currency) }}
                    {{ formtCurrency(item.grand_total) }}
                  </template>
                  <template v-slot:item.is_stale="{ item }">
                    <v-chip
                      x-small
                      :color="Number(item.is_stale || 0) === 1 ? 'warning' : 'success'"
                      :outlined="Number(item.is_stale || 0) !== 1"
                      :text-color="Number(item.is_stale || 0) === 1 ? 'white' : ''"
                    >
                      {{ Number(item.is_stale || 0) === 1 ? __("Stale") : __("Fresh") }}
                    </v-chip>
                  </template>
                  <template v-slot:item.is_expired="{ item }">
                    <v-chip
                      x-small
                      :color="Number(item.is_expired || 0) === 1 ? 'error' : 'success'"
                      :outlined="Number(item.is_expired || 0) !== 1"
                      :text-color="Number(item.is_expired || 0) === 1 ? 'white' : ''"
                    >
                      {{ Number(item.is_expired || 0) === 1 ? __("Expired") : __("Valid") }}
                    </v-chip>
                  </template>
                </v-data-table>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="error" dark @click="close_dialog">{{ __("Close") }}</v-btn>
          <v-btn v-if="selected.length" color="primary" dark @click="print_selected_quotation">{{ __("Print") }}</v-btn>
          <v-btn v-if="selected.length" color="success" dark @click="submit_dialog">{{ __("Select") }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-row>
</template>

<script>
import { evntBus } from "../../bus";
import format from "../../format";
import { resolveCurrentRole } from "../../utils/posRole";

export default {
  mixins: [format],
  data: () => ({
    quotesDialog: false,
    singleSelect: true,
    pos_profile: {},
    selected: [],
    dialog_data: [],
    quote_name: "",
    headers: [
      { text: __("Customer"), value: "customer_name", align: "start", sortable: true },
      { text: __("Date"), value: "transaction_date", align: "start", sortable: true },
      { text: __("Valid Till"), value: "valid_till", align: "start", sortable: true },
      { text: __("Quote"), value: "name", align: "start", sortable: true },
      { text: __("Amount"), value: "grand_total", align: "end", sortable: false },
      { text: __("Age"), value: "order_age_days", align: "center", sortable: true },
      { text: __("Freshness"), value: "is_stale", align: "center", sortable: true },
      { text: __("Validity"), value: "is_expired", align: "center", sortable: true },
    ],
  }),
  methods: {
    close_dialog() {
      this.quotesDialog = false;
    },
    quotationPolicy() {
      const maxAge = Math.max(
        0,
        Number((this.pos_profile && this.pos_profile.posa_sales_order_lookup_max_age_days) || 1) || 1
      );
      const allowStale =
        Number((this.pos_profile && this.pos_profile.posa_allow_stale_sales_order_fetch) || 0) === 1;
      const historyDays = Math.max(
        maxAge,
        Number((this.pos_profile && this.pos_profile.posa_stale_sales_order_history_days) || 30) || 30
      );
      return { maxAge, allowStale, historyDays };
    },
    getCurrentRole() {
      return resolveCurrentRole();
    },
    normalize_relay_url(relayUrl) {
      return String(relayUrl || "").trim().replace(/\/$/, "");
    },
    relay_config_storage_key() {
      const site =
        (frappe.boot && (frappe.boot.sitename || frappe.boot.site_name)) ||
        window.location.host ||
        "site";
      const profile = String((this.pos_profile && this.pos_profile.name) || "default").trim() || "default";
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
      return String(
        (browserConfig && browserConfig.relay_url) ||
          ""
      )
        .trim()
        .replace(/\/$/, "");
    },
    get_relay_client_headers(extra = {}) {
      const headers = { ...extra };
      try {
        const relayKey = (localStorage.getItem("posa_relay_client_key") || "").trim();
        if (relayKey) headers["X-Relay-Client-Key"] = relayKey;
      } catch (e) {}
      return headers;
    },
    relay_quote_fallback_enabled() {
      return (
        parseInt((this.pos_profile && this.pos_profile.custom_have_token) || 0, 10) === 1 &&
        !!this.get_relay_base_url()
      );
    },
    normalize_relay_quote_row(row = {}) {
      const createdAt = String(row.created_at || "").trim();
      const transaction_date = createdAt
        ? createdAt.replace("T", " ").slice(0, 10)
        : frappe.datetime.nowdate();
      return {
        name: row.quote_id || "",
        quote_id: row.quote_id || "",
        relay_offline_quote: 1,
        customer_name: row.customer_name || row.customer_id || "",
        customer: row.customer_id || row.customer_name || "",
        transaction_date,
        valid_till: row.valid_until || "",
        grand_total: flt(row.latest_total || row.base_total || 0),
        currency: row.currency || (this.pos_profile && this.pos_profile.currency) || "",
        order_age_days: Number(row.order_age_days || 0),
        is_stale: Number(row.is_stale || 0),
        is_expired: Number(row.is_expired || 0),
        status: row.status || "OPEN",
      };
    },
    normalize_relay_token_to_order_doc(token = {}) {
      const createdAt = String(token.created_at || "").trim();
      const transactionDate = createdAt
        ? createdAt.replace("T", " ").slice(0, 10)
        : frappe.datetime.nowdate();
      const items = (token.items || []).map((line, idx) => {
        const payload = line && line.payload && typeof line.payload === "object" ? line.payload : {};
        const qty = flt(line.qty || payload.qty || 0);
        const rate = flt(line.rate || payload.rate || 0);
        return {
          item_code: line.item_code || payload.item_code,
          item_name: line.item_name || payload.item_name || line.item_code || "",
          qty,
          rate,
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
          posa_row_id: payload.posa_row_id || `${token.token_id || "TOKEN"}-${idx + 1}`,
          sales_order: token.token_id || "",
          sales_order_name: token.token_id || "",
          posa_order_name: token.order_name || token.posa_order_name || "",
          order_name: token.order_name || token.posa_order_name || "",
        };
      });
      const grandTotal = flt(token.grand_total || 0);
      return {
        name: token.token_id || "",
        doctype: "Sales Order",
        relay_offline_order: 1,
        relay_token_status: token.status || "TOKEN_OPEN",
        token_id: token.token_id || "",
        sales_order: token.token_id || "",
        sales_order_name: token.token_id || "",
        posa_order_name: token.order_name || token.posa_order_name || "",
        order_name: token.order_name || token.posa_order_name || "",
        customer: token.customer_id || token.customer_name || "",
        customer_name: token.customer_name || token.customer_id || "",
        company: (this.pos_profile && this.pos_profile.company) || "",
        currency: (this.pos_profile && this.pos_profile.currency) || "",
        pos_profile: (this.pos_profile && this.pos_profile.name) || "",
        posting_date: transactionDate,
        transaction_date: transactionDate,
        grand_total: grandTotal,
        rounded_total: flt(token.rounded_total || grandTotal),
        net_total: flt(token.net_total || grandTotal),
        total: flt(token.total || grandTotal),
        discount_amount: 0,
        additional_discount_percentage: 0,
        posa_offers: [],
        posa_coupons: [],
        items,
      };
    },
    async search_quotes_via_relay() {
      const base = this.get_relay_base_url();
      if (!base) throw new Error(__("Relay URL is not configured."));
      const policy = this.quotationPolicy();
      const params = new URLSearchParams();
      params.set("pos_profile_id", (this.pos_profile && this.pos_profile.name) || "");
      params.set("limit", "100");
      params.set("statuses_csv", "OPEN");
      params.set("max_age_days", String(policy.maxAge));
      params.set("allow_stale", policy.allowStale ? "1" : "0");
      params.set("history_days", String(policy.historyDays));
      if (this.quote_name) params.set("search", this.quote_name);
      const resp = await fetch(`${base}/relay/quotes/search?${params.toString()}`, {
        method: "GET",
        headers: this.get_relay_client_headers({ Accept: "application/json" }),
      });
      let payload = {};
      try {
        payload = (await resp.json()) || {};
      } catch (e) {
        payload = {};
      }
      if (!resp.ok || payload.ok === false) {
        throw new Error(payload.message || __("Unable to search relay quotations."));
      }
      this.dialog_data = (payload.rows || []).map((row) => this.normalize_relay_quote_row(row));
      return true;
    },
    search_quotations() {
      const vm = this;
      const policy = this.quotationPolicy();
      return new Promise((resolve) => {
        frappe.call({
          method: "posawesome.posawesome.api.posapp.search_quotations",
          args: {
            quote_name: vm.quote_name,
            company: this.pos_profile.company,
            currency: this.pos_profile.currency,
            pos_profile: this.pos_profile.name,
            allow_stale: policy.allowStale ? 1 : 0,
            history_days: policy.historyDays,
          },
          async: true,
          callback: async function (r) {
            if (r && !r.exc && r.message) {
              const cloudRows = Array.isArray(r.message) ? r.message : [];
              if (cloudRows.length > 0 || !vm.relay_quote_fallback_enabled()) {
                vm.dialog_data = cloudRows;
                resolve(true);
                return;
              }
            }
            if (!vm.relay_quote_fallback_enabled()) {
              resolve(false);
              return;
            }
            try {
              await vm.search_quotes_via_relay();
              evntBus.$emit("show_mesage", {
                text: __("Loaded Quotations from local relay (cloud unavailable)."),
                color: "warning",
              });
            } catch (e) {
              evntBus.$emit("show_mesage", {
                text: (e && e.message) || __("Unable to search Quotations."),
                color: "error",
              });
            }
            resolve(true);
          },
          error: async function () {
            if (!vm.relay_quote_fallback_enabled()) {
              resolve(false);
              return;
            }
            try {
              await vm.search_quotes_via_relay();
              evntBus.$emit("show_mesage", {
                text: __("Loaded Quotations from local relay (cloud unavailable)."),
                color: "warning",
              });
            } catch (e) {
              evntBus.$emit("show_mesage", {
                text: (e && e.message) || __("Unable to search Quotations."),
                color: "error",
              });
            }
            resolve(true);
          },
        });
      });
    },
    promptOrderName() {
      const value = window.prompt(__("Enter Order Name"));
      return String(value || "").trim();
    },
    async convertCloudQuote(row, orderName) {
      const quoteName = String((row && (row.quote_name || row.name)) || "").trim();
      if (!quoteName) throw new Error(__("Quotation name is missing."));

      const previewResp = await frappe.call({
        method: "posawesome.posawesome.api.posapp.quotation_reprice_preview",
        args: {
          quotation_name: quoteName,
          pos_profile: this.pos_profile.name,
        },
      });
      const preview = (previewResp && previewResp.message) || {};
      if (Number(preview.is_expired || 0) === 1) {
        throw new Error(__("Quotation is expired and cannot be converted."));
      }
      const delta = Number(preview.delta_total || 0);
      if (Math.abs(delta) > 0.0001) {
        const ok = window.confirm(
          __("Quotation total changed by {0}. Convert with latest prices?", [
            `${this.currencySymbol(this.pos_profile.currency)} ${this.formtCurrency(delta)}`,
          ])
        );
        if (!ok) return null;
      }

      const convertResp = await frappe.call({
        method: "posawesome.posawesome.api.posapp.convert_quotation_to_sales_order_token",
        args: {
          quotation_name: quoteName,
          pos_profile: this.pos_profile.name,
          confirm_reprice: 1,
          order_name: orderName,
        },
      });
      const converted = (convertResp && convertResp.message) || {};
      if (!converted.sales_order) {
        throw new Error(__("Quote converted but Sales Order payload is missing."));
      }
      return converted.sales_order;
    },
    async convertRelayQuote(row, orderName) {
      const base = this.get_relay_base_url();
      if (!base) throw new Error(__("Relay URL is not configured."));
      const quoteId = String((row && (row.quote_id || row.name)) || "").trim();
      if (!quoteId) throw new Error(__("Relay quotation id is missing."));

      const previewResp = await fetch(`${base}/relay/quote/reprice-preview`, {
        method: "POST",
        headers: this.get_relay_client_headers({
          "Content-Type": "application/json",
          Accept: "application/json",
        }),
        body: JSON.stringify({ quote_id: quoteId, role: this.getCurrentRole() || "" }),
      });
      const previewBody = await previewResp.json().catch(() => ({}));
      if (!previewResp.ok || previewBody.ok === false) {
        throw new Error(previewBody.message || __("Unable to preview relay quotation repricing."));
      }
      const delta = Number(previewBody.delta_total || 0);
      if (Math.abs(delta) > 0.0001) {
        const ok = window.confirm(
          __("Quotation total changed by {0}. Convert with latest prices?", [
            `${this.currencySymbol(this.pos_profile.currency)} ${this.formtCurrency(delta)}`,
          ])
        );
        if (!ok) return null;
      }

      const convertResp = await fetch(`${base}/relay/quote/convert-to-token`, {
        method: "POST",
        headers: this.get_relay_client_headers({
          "Content-Type": "application/json",
          Accept: "application/json",
        }),
        body: JSON.stringify({
          quote_id: quoteId,
          cashier_user_id: (frappe.session && frappe.session.user) || "",
          role: this.getCurrentRole() || "",
          confirm_reprice: 1,
          order_name: orderName,
        }),
      });
      const convertBody = await convertResp.json().catch(() => ({}));
      if (!convertResp.ok || convertBody.ok === false) {
        throw new Error(convertBody.message || __("Unable to convert relay quotation."));
      }
      const token = convertBody.token || {};
      const tokenId = String(token.token_id || "").trim();
      if (!tokenId) throw new Error(__("Relay conversion did not return token id."));

      const tokenResp = await fetch(`${base}/relay/token/${encodeURIComponent(tokenId)}`, {
        method: "GET",
        headers: this.get_relay_client_headers({ Accept: "application/json" }),
      });
      const tokenBody = await tokenResp.json().catch(() => ({}));
      if (!tokenResp.ok || tokenBody.ok === false || !tokenBody.token) {
        throw new Error(__("Relay token details unavailable after conversion."));
      }
      return this.normalize_relay_token_to_order_doc(tokenBody.token);
    },
    clearSelected() {
      this.selected = [];
    },
    print_selected_quotation() {
      if (!this.selected.length) return;
      const row = this.selected[0] || {};
      if (row.relay_offline_quote) {
        evntBus.$emit("show_mesage", {
          text: __("Relay quotations are not available for ERPNext print."),
          color: "error",
        });
        return;
      }
      const quoteName = String(row.quote_name || row.name || "").trim();
      if (!quoteName) {
        evntBus.$emit("show_mesage", {
          text: __("Quotation name is missing."),
          color: "error",
        });
        return;
      }

      const letterHead = this.pos_profile.letter_head || 0;
      const url =
        frappe.urllib.get_base_url() +
        "/printview?doctype=Quotation&name=" +
        encodeURIComponent(quoteName) +
        "&trigger_print=1" +
        "&no_letterhead=" +
        letterHead;
      const printWindow = window.open(url, "Print");
      if (printWindow) {
        printWindow.addEventListener(
          "load",
          function () {
            printWindow.print();
          },
          true
        );
      }
    },
    async submit_dialog() {
      if (!this.selected.length) return;
      const row = this.selected[0];
      try {
        if (!Array.isArray(row.items) || !row.items.length) {
          evntBus.$emit("show_mesage", {
            text: __("Quotation items are not available to load."),
            color: "error",
          });
          return;
        }
        evntBus.$emit("load_quotation", row);
        this.quotesDialog = false;
        evntBus.$emit("show_mesage", {
          text: __("Quotation loaded."),
          color: "success",
        });
      } catch (e) {
        evntBus.$emit("show_mesage", {
          text: (e && e.message) || __("Quotation load failed."),
          color: "error",
        });
      }
    },
  },
  created() {
    evntBus.$on("open_quotations", (data) => {
      this.clearSelected();
      this.quotesDialog = true;
      this.dialog_data = Array.isArray(data) ? data : [];
      this.quote_name = "";
    });
  },
  mounted() {
    evntBus.$on("register_pos_profile", (data) => {
      this.pos_profile = data.pos_profile;
    });
  },
};
</script>
