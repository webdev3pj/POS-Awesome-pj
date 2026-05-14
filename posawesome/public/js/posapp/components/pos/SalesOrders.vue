<template>
  <v-row justify="center">
    <v-dialog v-model="draftsDialog" max-width="900px">
      <!-- <template v-slot:activator="{ on, attrs }">
              <v-btn color="primary" dark v-bind="attrs" v-on="on">Open Dialog</v-btn>
            </template>-->
      <v-card>
        <v-card-title>
          <span class="headline primary--text">{{
            __("Select Sales Orders")
          }}</span>
        </v-card-title>
        <v-card-text class="pa-0">
          <v-container>
            <v-row class="mb-4">
              <v-text-field
                color="primary"
                :label="frappe._('Order Name / Token')"
                background-color="white"
                hide-details
                v-model="order_name"
                dense
                clearable
                class="mx-4"
              ></v-text-field>
              <v-btn
                text
                class="ml-2"
                color="primary"
                dark
                @click="search_orders"
                >{{ __("Search") }}</v-btn
              >
            </v-row>
            <v-row no-gutters>
              <v-col cols="12" class="pa-1">
                <template>
                  <v-data-table
                    :headers="headers"
                    :items="dialog_data"
                    item-key="name"
                    class="elevation-1"
                    :single-select="singleSelect"
                    show-select
                    v-model="selected"
                  >
                    <!-- <template v-slot:item.posting_time="{ item }">
                          {{ item.posting_time.split(".")[0] }}
                        </template> -->
                    <template v-slot:item.grand_total="{ item }">
                      {{ currencySymbol(item.currency) }}
                      {{ formtCurrency(item.grand_total) }}
                    </template>
                    <template v-slot:item.order_age_days="{ item }">
                      <span>{{ Number(item.order_age_days || 0) }}</span>
                    </template>
                    <template v-slot:item.is_stale="{ item }">
                      <v-chip
                        x-small
                        :color="orderIsStale(item) ? 'warning' : 'success'"
                        :outlined="!orderIsStale(item)"
                        text-color="white"
                      >
                        {{ orderIsStale(item) ? __("Stale") : __("Fresh") }}
                      </v-chip>
                    </template>
                  </v-data-table>
                </template>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="error" dark @click="close_dialog">Close</v-btn>
          <v-btn
            v-if="selected.length"
            color="success"
            dark
            @click="submit_dialog"
            >Select</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-row>
</template>

<script>
import { evntBus } from "../../bus";
import format from "../../format";
export default {
  // props: ["draftsDialog"],
  mixins: [format],
  data: () => ({
    draftsDialog: false,
    singleSelect: true,
    pos_profile: {},
    selected: [],
    dialog_data: {},
    order_name: "",
    headers: [
      {
        text: __("Customer"),
        value: "customer_name",
        align: "start",
        sortable: true,
      },
      {
        text: __("Date"),
        align: "start",
        sortable: true,
        value: "transaction_date",
      },
      //   {
      //     text: __("Time"),
      //     align: "start",
      //     sortable: true,
      //     value: "posting_time",
      //   },
      {
        text: __("Order"),
        value: "name",
        align: "start",
        sortable: true,
      },
      {
        text: __("Order Name"),
        value: "posa_order_name",
        align: "start",
        sortable: true,
      },
      {
        text: __("Amount"),
        value: "grand_total",
        align: "end",
        sortable: false,
      },
      {
        text: __("Age (Days)"),
        value: "order_age_days",
        align: "center",
        sortable: true,
      },
      {
        text: __("Freshness"),
        value: "is_stale",
        align: "center",
        sortable: true,
      },
    ],
  }),
  watch: {},
  methods: {
    soPolicy() {
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
    orderIsStale(item) {
      if (Number(item && item.is_stale ? 1 : 0) === 1) return true;
      const p = this.soPolicy();
      const age = Number((item && item.order_age_days) || 0);
      return age > p.maxAge;
    },
    close_dialog() {
      this.draftsDialog = false;
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
    relay_order_fallback_enabled() {
      return (
        parseInt((this.pos_profile && this.pos_profile.custom_have_token) || 0, 10) === 1 &&
        !!this.get_relay_base_url()
      );
    },
    normalize_relay_token_row(row = {}) {
      const createdAt = String(row.created_at || "").trim();
      const transaction_date = createdAt
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
          uom: line.uom || payload.uom || payload.stock_uom || "",
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
      const grand_total = flt(row.grand_total || 0);

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
        company: (this.pos_profile && this.pos_profile.company) || "",
        currency: (this.pos_profile && this.pos_profile.currency) || "",
        pos_profile: (this.pos_profile && this.pos_profile.name) || "",
        posting_date: transaction_date,
        transaction_date: transaction_date,
        grand_total: grand_total,
        rounded_total: flt(row.rounded_total || grand_total),
        net_total: flt(row.net_total || grand_total),
        total: flt(row.total || grand_total),
        items: items,
        discount_amount: 0,
        additional_discount_percentage: 0,
        posa_offers: [],
        posa_coupons: [],
      };
    },
    async fetch_relay_token_rows(searchText = "") {
      const base = this.get_relay_base_url();
      if (!base) {
        throw new Error(__("Relay URL is not configured."));
      }
      const policy = this.soPolicy();
      const params = new URLSearchParams();
      params.set("limit", "100");
      params.set("statuses_csv", "TOKEN_OPEN");
      params.set("max_age_days", String(policy.maxAge));
      params.set("allow_stale", policy.allowStale ? "1" : "0");
      params.set("history_days", String(policy.historyDays));
      if (searchText) params.set("search", searchText);
      const resp = await fetch(`${base}/relay/tokens/search?${params.toString()}`, {
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
        throw new Error(payload.message || __("Unable to search relay orders."));
      }
      return payload.rows || [];
    },
    async search_orders_via_relay() {
      const searchText = String(this.order_name || "").trim();
      const rows = await this.fetch_relay_token_rows(searchText);
      this.dialog_data = rows.map((row) => this.normalize_relay_token_row(row));
      return true;
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
    search_orders() {
      const vm = this;
      return new Promise((resolve) => {
        let cloudFailed = false;
        const policy = vm.soPolicy();
        frappe.call({
          method: "posawesome.posawesome.api.posapp.search_orders",
          args: {
            order_name: vm.order_name,
            company: this.pos_profile.company,
            currency: this.pos_profile.currency,
            pos_profile: this.pos_profile.name,
            days_back: policy.maxAge,
            allow_stale: policy.allowStale ? 1 : 0,
            history_days: policy.historyDays,
          },
          async: true,
          callback: async function (r) {
            if (r && r.exc) {
              cloudFailed = true;
            } else if (r && r.message) {
	              const cloudRows = Array.isArray(r.message) ? r.message : [];
	              if (cloudRows.length > 0) {
	                vm.dialog_data = cloudRows;
	                resolve(true);
	                if (vm.relay_order_fallback_enabled()) {
	                  vm.fetch_relay_token_rows(String(vm.order_name || "").trim())
	                    .then((relayRows) => {
	                      vm.dialog_data = vm.merge_sales_order_rows(
	                        cloudRows,
	                        relayRows.map((row) => vm.normalize_relay_token_row(row))
	                      );
	                    })
	                    .catch(() => {});
	                }
	                return;
	              }
              if (!vm.relay_order_fallback_enabled()) {
                vm.dialog_data = r.message;
                resolve(true);
                return;
              }
              cloudFailed = true;
            } else {
              cloudFailed = true;
            }
            if (!cloudFailed) {
              resolve(true);
              return;
            }
            if (!vm.relay_order_fallback_enabled()) {
              resolve(false);
              return;
            }
            try {
              await vm.search_orders_via_relay();
              evntBus.$emit("show_mesage", {
                text: __("Loaded Sales Orders from local relay (cloud unavailable)."),
                color: "warning",
              });
            } catch (e) {
              evntBus.$emit("show_mesage", {
                text: (e && e.message) || __("Unable to search Sales Orders."),
                color: "error",
              });
            }
            resolve(true);
          },
          error: async function () {
            if (vm.relay_order_fallback_enabled()) {
              try {
                await vm.search_orders_via_relay();
                evntBus.$emit("show_mesage", {
                  text: __("Loaded Sales Orders from local relay (cloud unavailable)."),
                  color: "warning",
                });
              } catch (e) {
                evntBus.$emit("show_mesage", {
                  text: (e && e.message) || __("Unable to search Sales Orders."),
                  color: "error",
                });
              }
            }
            resolve(true);
          },
        });
      });
    },

    clearSelected() {
      this.selected = [];
    },

    async submit_dialog() {
      if (this.selected.length > 0) {
        if (this.orderIsStale(this.selected[0])) {
          evntBus.$emit("show_mesage", {
            text: __("Selected Sales Order is stale based on POS profile policy."),
            color: "warning",
          });
        }
        if (this.selected[0].relay_offline_order) {
          evntBus.$emit("load_order", this.selected[0]);
          this.draftsDialog = false;
          return;
        }
        var invoice_doc_for_load = {};
        await frappe.call({
          method:
            "posawesome.posawesome.api.posapp.create_sales_invoice_from_order",
          args: {
            sales_order: this.selected[0].name,
            pos_profile: this.pos_profile.name,
          },
          callback: function (r) {
            if (r.message) {
              invoice_doc_for_load = r.message;
            }
          },
        });
        if (invoice_doc_for_load.items) {
          const selectedItems = this.selected[0].items;
          const loadedItems = invoice_doc_for_load.items;

          const loadedItemsMap = {};
          loadedItems.forEach((item) => {
            loadedItemsMap[item.item_code] = item;
          });

          // Iterate through selectedItems and update or discard items
          for (let i = 0; i < selectedItems.length; i++) {
            const selectedItem = selectedItems[i];
            const loadedItem = loadedItemsMap[selectedItem.item_code];

            if (loadedItem) {
              // Update the fields of selected item with loaded item's values
              selectedItem.qty = loadedItem.qty;
              selectedItem.amount = loadedItem.amount;
              selectedItem.uom = loadedItem.uom;
              selectedItem.rate = loadedItem.rate;
              // Update other fields as needed
            } else {
              // If 'item_code' doesn't exist in loadedItems, discard the item
              selectedItems.splice(i, 1);
              i--; // Adjust the index as items are removed
            }
          }
        }
        evntBus.$emit("load_order", this.selected[0]);
        this.draftsDialog = false;
      }
    },
  },
  created: function () {
    evntBus.$on("open_orders", (data) => {
      this.clearSelected();
      this.draftsDialog = true;
      this.dialog_data = data;
      this.order_name = "";
    });
  },
  mounted() {
    evntBus.$on("register_pos_profile", (data) => {
      this.pos_profile = data.pos_profile;
    });
  },
};
</script>
