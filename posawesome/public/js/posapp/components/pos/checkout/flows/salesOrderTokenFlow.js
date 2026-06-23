import { evntBus } from "../../../../bus";

export default {
  methods: {
    normalize_order_name(value = this.order_name) {
      return String(value || "").trim();
    },

    reset_after_token_save() {
      this.items = [];
      this.customer = this.pos_profile.customer;
      this.invoice_doc = "";
      this.order_name = "";
      this.discount_amount = 0;
      this.additional_discount_percentage = 0;
      this.delivery_charges_rate = 0;
      this.selcted_delivery_charges = {};
      this.posa_offers = [];
      evntBus.$emit("set_pos_coupons", []);
      this.posa_coupons = [];
      this.return_doc = "";
      this.invoiceType = "Order";
      this.invoiceTypes = ["Invoice", "Order"];
      evntBus.$emit("set_customer_readonly", false);
    },

    get_sales_order_token_payload() {
      return {
        pos_profile: this.pos_profile.name,
        pos_opening_shift: (this.pos_opening_shift && this.pos_opening_shift.name) || "",
        company: this.pos_profile.company,
        customer: this.customer,
        order_name: this.normalize_order_name(),
        currency: this.pos_profile.currency,
        campaign: this.pos_profile.campaign || "",
        posting_date: this.posting_date,
        items: this.get_order_items(),
        discount_amount: flt(this.discount_amount),
        additional_discount_percentage: flt(this.additional_discount_percentage),
        posa_offers: this.posa_offers || [],
        posa_coupons: this.posa_coupons || [],
        posa_delivery_charges: (this.selcted_delivery_charges || {}).name || "",
        posa_delivery_charges_rate: this.delivery_charges_rate || 0,
      };
    },

    create_sales_order_token(payload) {
      return new Promise((resolve, reject) => {
        frappe.call({
          method: "posawesome.posawesome.api.posapp.create_sales_order_token",
          args: { data: payload },
          async: true,
          callback: (r) => {
            if (r && r.exc) {
              reject(new Error(__("Unable to create Sales Order token.")));
              return;
            }
            if (!r || !r.message) {
              reject(new Error(__("Empty response while creating Sales Order token.")));
              return;
            }
            resolve(r.message);
          },
          error: (err) => {
            const message =
              (err && err.message) ||
              __("Unable to create Sales Order token. Please try again.");
            reject(new Error(message));
          },
        });
      });
    },

    build_relay_local_token_meta(relayToken, tokenPayload = {}) {
      const token = relayToken || {};
      const sourceItems =
        Array.isArray(token.items) && token.items.length ? token.items : tokenPayload.items || [];
      const grandTotal = sourceItems.reduce((sum, row) => {
        const qty = flt((row && row.qty) || 0);
        const rate = flt((row && row.rate) || 0);
        return sum + flt((row && row.amount) || qty * rate);
      }, 0);
      const tokenId = String(token.token_id || "").trim();
      return {
        local_only: 1,
        token_id: tokenId,
        token_last4: tokenId ? tokenId.slice(-4) : "",
        sales_order_name: tokenId,
        order_name: tokenPayload.order_name || token.order_name || "",
        posa_order_name: tokenPayload.order_name || token.order_name || "",
        customer: tokenPayload.customer || token.customer_id || this.customer,
        customer_name:
          (this.customer_info && this.customer_info.customer_name) ||
          token.customer_name ||
          tokenPayload.customer ||
          this.customer,
        grand_total: grandTotal,
        currency: this.pos_profile.currency,
        order_taken_at: token.created_at || token.updated_at || new Date().toISOString(),
        sales_associate_user: frappe.session.user,
        sales_associate_name: frappe.session.user_fullname || frappe.session.user,
        sales_order: {
          customer: token.customer_id || tokenPayload.customer || this.customer,
          customer_name:
            (this.customer_info && this.customer_info.customer_name) ||
            token.customer_name ||
            tokenPayload.customer ||
            this.customer,
          items: sourceItems.map((row) => {
            const payload = row && row.payload && typeof row.payload === "object" ? row.payload : {};
            return {
              item_code: row.item_code || payload.item_code,
              item_name: row.item_name || payload.item_name || "",
              qty: flt((row && row.qty) || payload.qty || 0),
              uom: row.uom || payload.uom || "",
              rate: flt((row && row.rate) || payload.rate || 0),
              amount: flt((row && row.amount) || payload.amount || 0),
            };
          }),
        },
      };
    },

    async create_sales_order_token_relay_local(tokenPayload) {
      const relayBaseUrl = this.get_relay_base_url();
      if (!relayBaseUrl) {
        throw new Error(__("Relay URL is not configured for offline Sales Order tokens."));
      }
      const items = (this.items || []).map((item) => ({
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
      }));
      const relayPayload = {
        pos_profile_id: this.pos_profile.name,
        cashier_user_id: frappe.session.user,
        customer_id: this.customer,
        customer_name:
          (this.customer_info && this.customer_info.customer_name) || this.customer,
        order_name: tokenPayload.order_name || "",
        source_doctype: "Sales Order",
        source_name: "",
        role: this.current_role || this.get_current_role() || "",
        items: items,
      };

      const resp = await fetch(`${relayBaseUrl}/relay/token/create`, {
        method: "POST",
        headers: this.get_relay_client_headers({ "Content-Type": "application/json" }),
        body: JSON.stringify(relayPayload),
      });
      let body = {};
      try {
        body = (await resp.json()) || {};
      } catch (e) {
        body = {};
      }
      if (!resp.ok || !body.ok || !body.token) {
        throw new Error(body.message || __("Unable to create Sales Order token on local relay."));
      }
      const meta = this.build_relay_local_token_meta(body.token, tokenPayload || {});
      meta.outbox_event_id = body.outbox_event_id || null;
      meta.created_locally_on_relay = 1;
      return meta;
    },

    escape_html(value) {
      return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    },

    token_slip_date_time(meta) {
      const raw = String((meta && meta.order_taken_at) || "");
      if (!raw) {
        return {
          dateLabel: frappe.datetime.str_to_user(this.posting_date || frappe.datetime.nowdate()),
          timeLabel: frappe.datetime.now_time().split(".")[0],
        };
      }
      const normalized = raw.replace("T", " ").replace("Z", "");
      const [datePart, timePartRaw] = normalized.split(" ");
      return {
        dateLabel: datePart ? frappe.datetime.str_to_user(datePart) : raw,
        timeLabel: (timePartRaw || "").split(".")[0] || frappe.datetime.now_time().split(".")[0],
      };
    },

    token_slip_qr_payload(meta) {
      const dt = this.token_slip_date_time(meta);
      return JSON.stringify({
        type: "POS-SO-TOKEN",
        sales_order: meta.sales_order_name,
        token_id: meta.token_id,
        token_last4: meta.token_last4,
        order_name: meta.order_name || meta.posa_order_name || "",
        customer_name: meta.customer_name,
        grand_total: meta.grand_total,
        currency: meta.currency,
        sales_associate_user: meta.sales_associate_user || frappe.session.user,
        sales_associate_name:
          meta.sales_associate_name || frappe.session.user_fullname || frappe.session.user,
        order_date: dt.dateLabel,
        order_time: dt.timeLabel,
        site: window.location.origin,
      });
    },

    print_sales_order_token_slip(meta) {
      const printWindow = window.open("", "", "height=700,width=420");
      if (!printWindow) {
        evntBus.$emit("show_mesage", {
          text: __("Popup blocked. Please allow popups to print token slips."),
          color: "warning",
        });
        return;
      }

      const dt = this.token_slip_date_time(meta);
      const soName = this.escape_html(meta.sales_order_name || "");
      const tokenLast4 = this.escape_html(meta.token_last4 || "");
      const orderName = this.escape_html(meta.order_name || meta.posa_order_name || "");
      const customerName = this.escape_html(meta.customer_name || "");
      const saName = this.escape_html(
        meta.sales_associate_name || frappe.session.user_fullname || frappe.session.user
      );
      const currency = this.escape_html(this.currencySymbol(meta.currency) || "");
      const grandTotal = this.escape_html(this.formtCurrency(meta.grand_total || 0));

      printWindow.document.write(`
        <html>
          <head>
            <title>Sales Order Token Slip</title>
            <meta charset="utf-8" />
            <script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"><\/script>
            <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"><\/script>
            <style>
              body {
                width: 80mm;
                margin: 0 auto;
                padding: 8px;
                font-family: Arial, sans-serif;
                color: #111;
              }
              .center { text-align: center; }
              .title { font-size: 16px; font-weight: bold; margin-bottom: 6px; }
              .muted { color: #555; font-size: 11px; }
              .row { margin: 3px 0; font-size: 12px; }
              .token-last4 { font-size: 28px; font-weight: bold; letter-spacing: 2px; margin: 8px 0 4px; }
              .total { font-size: 15px; font-weight: bold; margin: 6px 0; }
              .divider { border-top: 1px dashed #999; margin: 8px 0; }
              #qrcode { width: 128px; height: 128px; margin: 0 auto; }
              #barcode-wrap { margin-top: 8px; text-align: center; }
              #barcode { width: 100%; max-width: 280px; }
              .fallback { font-size: 11px; color: #a33; margin-top: 4px; display: none; }
            </style>
          </head>
          <body>
            <div class="center title">Sales Order Token</div>
            <div class="center muted">Full SO: ${soName}</div>
            <div class="center token-last4">${tokenLast4}</div>
            <div class="divider"></div>
            <div class="row"><b>Order Name:</b> ${orderName}</div>
            <div class="row"><b>Customer:</b> ${customerName}</div>
            <div class="row"><b>Sales Associate:</b> ${saName}</div>
            <div class="row"><b>Date:</b> ${this.escape_html(dt.dateLabel)}</div>
            <div class="row"><b>Time:</b> ${this.escape_html(dt.timeLabel)}</div>
            <div class="row total"><b>Grand Total:</b> ${currency} ${grandTotal}</div>
            <div class="divider"></div>
            <div id="qrcode" class="center"></div>
            <div id="barcode-wrap">
              <svg id="barcode"></svg>
              <div class="muted">${soName}</div>
            </div>
            <div id="render-fallback" class="fallback center">
              QR/Barcode render failed. Use SO Number / Last4 above.
            </div>
            <script>
              (function() {
                var failed = false;
                try {
                  if (window.QRCode) {
                    new QRCode(document.getElementById('qrcode'), {
                      text: ${JSON.stringify("")} + ${JSON.stringify(this.token_slip_qr_payload(meta))},
                      width: 128,
                      height: 128,
                      correctLevel: QRCode.CorrectLevel.M
                    });
                  } else {
                    failed = true;
                  }
                  if (window.JsBarcode) {
                    JsBarcode('#barcode', ${JSON.stringify(meta.token_id || meta.sales_order_name || "")}, {
                      format: 'CODE128',
                      width: 1.5,
                      height: 40,
                      displayValue: false,
                      margin: 0
                    });
                  } else {
                    failed = true;
                  }
                } catch (e) {
                  failed = true;
                }
                if (failed) {
                  var fb = document.getElementById('render-fallback');
                  if (fb) fb.style.display = 'block';
                }
                window.focus();
                setTimeout(function() { window.print(); }, 300);
              })();
            <\/script>
          </body>
        </html>
      `);

      printWindow.document.close();
    },

    show_sales_order_token_dialog(meta) {
      const vm = this;
      const dt = this.token_slip_date_time(meta);
      const tokenLast4 = this.escape_html(meta.token_last4 || "");
      const soName = this.escape_html(meta.sales_order_name || "");
      const orderName = this.escape_html(meta.order_name || meta.posa_order_name || "");
      const customerName = this.escape_html(meta.customer_name || "");
      const grandTotal = `${this.currencySymbol(meta.currency)} ${this.formtCurrency(meta.grand_total || 0)}`;
      const d = new frappe.ui.Dialog({
        title: __("Sales Order Token"),
        fields: [
          {
            fieldname: "token",
            fieldtype: "HTML",
            options: `
              <div style="text-align:center;font-size:42px;padding:0.5rem 0;"><b>${tokenLast4}</b></div>
              <div style="text-align:center;padding-bottom:0.5rem;"><small><b>SO:</b> ${soName}</small></div>
              <div style="font-size:13px;line-height:1.5;">
                <div><b>${__("Order Name")}:</b> ${orderName}</div>
                <div><b>${__("Customer")}:</b> ${customerName}</div>
                <div><b>${__("Sales Associate")}:</b> ${this.escape_html(meta.sales_associate_name || frappe.session.user_fullname || frappe.session.user)}</div>
                <div><b>${__("Date")}:</b> ${this.escape_html(dt.dateLabel)} &nbsp; <b>${__("Time")}:</b> ${this.escape_html(dt.timeLabel)}</div>
                <div><b>${__("Grand Total")}:</b> ${this.escape_html(grandTotal)}</div>
              </div>
              <div style="padding-top:0.75rem;text-align:center;color:#085294;font-size:13px;font-weight:600;">
                ${this.escape_html(__("Use the 'Print Token Slip' button below to print and hand this token to the customer."))}
              </div>`,
          },
          {
            fieldname: "relay_note",
            fieldtype: "HTML",
            options: `<div style="text-align:center;color:#1e88e5;padding-top:0.25rem;"><small>${frappe._(
              meta.local_only
                ? "Sales Order token created on local relay (offline mode). It will sync to cloud later."
                : "Sales Order token created. Relay token sync is best-effort."
            )}</small></div>`,
          },
        ],
        primary_action_label: __("Print Token Slip"),
        primary_action() {
          vm.print_sales_order_token_slip(meta);
          d.hide();
        },
        secondary_action_label: __("Close"),
      });
      d.show();
    },

    sync_relay_token_for_sales_order(meta) {
      const relayEnabled = this.relayWorkflowEnabled();
      const relayBaseUrl = this.get_relay_base_url();
      if (!relayEnabled || !relayBaseUrl || !meta || !meta.sales_order) {
        return;
      }

      const soDoc = meta.sales_order || {};
      const tokenPayload = {
        token_id: meta.token_id || meta.sales_order_name,
        pos_profile_id: this.pos_profile.name,
        cashier_user_id: frappe.session.user,
        customer_id: soDoc.customer || meta.customer,
        customer_name: soDoc.customer_name || meta.customer_name,
        order_name: meta.order_name || meta.posa_order_name || soDoc.posa_order_name || "",
        source_doctype: "Sales Order",
        source_name: meta.sales_order_name,
        role: this.current_role || "",
        items: (soDoc.items || []).map((row) => ({
          item_code: row.item_code,
          item_name: row.item_name,
          qty: row.qty,
          uom: row.uom,
          rate: row.rate,
          amount: row.amount,
        })),
      };

      fetch(`${relayBaseUrl}/relay/token/create`, {
        method: "POST",
        headers: this.get_relay_client_headers({ "Content-Type": "application/json" }),
        body: JSON.stringify(tokenPayload),
      }).catch(() => {
        evntBus.$emit("show_mesage", {
          text: __("Sales Order token created, but relay token sync failed. You can continue."),
          color: "warning",
        });
      });
    },

    async save_sales_order_token_and_reset() {
      this.current_role = this.get_current_role();
      if (!this.customer) {
        evntBus.$emit("show_mesage", {
          text: __(`There is no Customer !`),
          color: "error",
        });
        return null;
      }
      if (!this.items.length) {
        evntBus.$emit("show_mesage", {
          text: __(`There is no Items !`),
          color: "error",
        });
        return null;
      }
      const orderName = this.normalize_order_name();
      if (!orderName) {
        evntBus.$emit("show_mesage", {
          text: __("Order Name is required before saving the order."),
          color: "error",
        });
        return null;
      }
      this.order_name = orderName;
      if (!this.validate()) {
        return null;
      }
      if (!this.pos_profile.posa_allow_sales_order) {
        evntBus.$emit("show_mesage", {
          text: __("POS Profile is not configured to allow Sales Orders."),
          color: "error",
        });
        return null;
      }

      try {
        const payload = this.get_sales_order_token_payload();
        let result = null;
        let usedRelayOfflineFallback = false;
        try {
          result = await this.create_sales_order_token(payload);
        } catch (cloudErr) {
          if (!this.relayWorkflowEnabled() || !this.get_relay_base_url()) {
            throw cloudErr;
          }
          result = await this.create_sales_order_token_relay_local(payload);
          usedRelayOfflineFallback = true;
        }
        this.show_sales_order_token_dialog(result);
        if (!usedRelayOfflineFallback) {
          this.sync_relay_token_for_sales_order(result);
        }
        evntBus.$emit("workflow_monitor_refresh_requested");
        this.reset_after_token_save();
        evntBus.$emit("show_mesage", {
          text: __(
            usedRelayOfflineFallback
              ? "Sales Order token created on local relay (offline): {0}"
              : "Sales Order token created: {0}",
            [result.sales_order_name || result.token_id || ""]
          ),
          color: usedRelayOfflineFallback ? "warning" : "success",
        });
        frappe.utils.play_sound("submit");
        return result;
      } catch (e) {
        evntBus.$emit("show_mesage", {
          text: e.message || __("Unable to create Sales Order token."),
          color: "error",
        });
        frappe.utils.play_sound("error");
        return null;
      }
    },
  },
};
