<template>
  <div class="mt-3">
    <v-row dense>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title class="py-2">
            <div class="d-flex align-center justify-space-between" style="width:100%">
              <div>
                <div class="text-subtitle-1 font-weight-bold">{{ roleTitle }}</div>
                <div class="caption grey--text">{{ profileName || __('No POS Profile') }}</div>
              </div>
              <v-btn icon small :disabled="queueLoading" @click="refreshAll">
                <v-icon :class="{ 'spin': queueLoading || detailLoading }">mdi-refresh</v-icon>
              </v-btn>
            </div>
          </v-card-title>
          <v-card-text class="pt-0">
            <v-alert dense outlined type="info" class="mb-2">
              {{ __('Paper-first picking with line-wise edits for exceptions. Picked qty defaults to ordered qty and keeps order UOM/conversion factor.') }}
            </v-alert>
            <div v-if="errorText" class="red--text mb-2">{{ errorText }}</div>
            <v-text-field
              v-model="queueSearch"
              dense
              outlined
              hide-details
              clearable
              prepend-inner-icon="mdi-magnify"
              :label="__('Search LSR / SO / customer')"
              class="mb-2"
            />
            <div class="d-flex flex-wrap mb-2">
              <v-chip
                v-for="f in filters"
                :key="f.value"
                small
                class="mr-1 mb-1"
                :outlined="queueFilter !== f.value"
                :color="queueFilter === f.value ? f.color : ''"
                @click="queueFilter = f.value"
              >
                {{ f.label }}
              </v-chip>
            </div>
            <div class="queue-list">
              <v-list dense>
                <v-list-item
                  v-for="row in filteredRows"
                  :key="row.local_sale_ref"
                  :class="{ active: selectedRef === row.local_sale_ref }"
                  @click="selectRow(row)"
                >
                  <v-list-item-content>
                    <v-list-item-title class="font-weight-bold">
                      {{ row.customer_name || __('Unknown Customer') }}
                    </v-list-item-title>
                    <v-list-item-subtitle>{{ row.local_sale_ref }}</v-list-item-subtitle>
                    <v-list-item-subtitle v-if="row.token_id">{{ __('SO') }}: {{ row.token_id }}</v-list-item-subtitle>
                    <v-list-item-subtitle class="d-flex align-center flex-wrap mt-1">
                      <v-chip x-small class="mr-1 mb-1" :color="pickColor(row.pick_status)" text-color="white">
                        {{ row.pick_status }}
                      </v-chip>
                      <v-chip x-small class="mr-1 mb-1" :color="dispatchColor(row.dispatch_status)" text-color="white">
                        {{ row.dispatch_status }}
                      </v-chip>
                      <span class="caption grey--text">{{ money(row.total) }}</span>
                    </v-list-item-subtitle>
                  </v-list-item-content>
                </v-list-item>
              </v-list>
              <div v-if="!queueLoading && !filteredRows.length" class="text-center grey--text py-3">
                {{ __('No rows') }}
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card>
          <v-card-title class="py-2">
            <div class="d-flex align-center justify-space-between" style="width:100%">
              <div>
                <div class="text-subtitle-1 font-weight-bold">{{ __('Fulfillment Detail') }}</div>
                <div class="caption grey--text">{{ selectedRef || __('Select a queue row') }}</div>
              </div>
              <div class="d-flex align-center" v-if="detail && detail.sale">
                <v-chip small class="mr-1" :color="pickColor(detail.sale.pick_status)" text-color="white">
                  {{ detail.sale.pick_status }}
                </v-chip>
                <v-chip small class="mr-1" :color="dispatchColor(detail.sale.dispatch_status)" text-color="white">
                  {{ detail.sale.dispatch_status }}
                </v-chip>
                <v-chip small :color="syncColor(detail.sale.cloud_sync_status)" text-color="white">
                  {{ detail.sale.cloud_sync_status }}
                </v-chip>
              </div>
            </div>
          </v-card-title>
          <v-card-text class="pt-0">
            <div v-if="detailError" class="red--text mb-2">{{ detailError }}</div>
            <div v-if="detailLoading" class="text-center py-4">
              <v-progress-circular indeterminate color="primary"></v-progress-circular>
            </div>
            <template v-else-if="detail && detail.sale">
              <v-row dense>
                <v-col cols="12" sm="6">
                  <v-card outlined>
                    <v-card-text class="py-2">
                      <div><strong>{{ __('LSR') }}:</strong> {{ detail.sale.local_sale_ref }}</div>
                      <div><strong>{{ __('SO/Token') }}:</strong> {{ detail.sale.token_id || '-' }}</div>
                      <div><strong>{{ __('Cloud SI') }}:</strong> {{ detail.sale.cloud_invoice_name || '-' }}</div>
                      <div><strong>{{ __('Customer') }}:</strong> {{ detail.sale.customer_name || detail.sale.customer_id || '-' }}</div>
                      <div><strong>{{ __('Cashier') }}:</strong> {{ detail.sale.cashier_user_id || '-' }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="12" sm="6">
                  <v-card outlined>
                    <v-card-text class="py-2">
                      <div><strong>{{ __('Total') }}:</strong> {{ money(detail.sale.total) }}</div>
                      <div><strong>{{ __('Created') }}:</strong> {{ dt(detail.sale.created_at) }}</div>
                      <div><strong>{{ __('Updated') }}:</strong> {{ dt(detail.sale.updated_at) }}</div>
                      <div><strong>{{ __('Released By') }}:</strong> {{ detail.sale.released_by || '-' }}</div>
                      <div><strong>{{ __('Released At') }}:</strong> {{ dt(detail.sale.released_at) }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>

              <div class="d-flex flex-wrap align-center mt-2 mb-2" v-if="canPick || canDispatch">
                <v-btn v-if="canPick" small text color="primary" class="mr-1 mb-1" @click="markAllPicked">{{ __('Mark All Picked') }}</v-btn>
                <v-btn v-if="canPick" small color="primary" class="mr-1 mb-1" :loading="actionLoading" @click="pickUpdate('PICK_IN_PROGRESS')">{{ __('Start/Save Picking') }}</v-btn>
                <v-btn v-if="canPick" small color="success" class="mr-1 mb-1" :loading="actionLoading" @click="markPickedReady">{{ __('Mark Picked Ready') }}</v-btn>
                <v-btn v-if="canPick" small color="warning" class="mr-1 mb-1" :loading="actionLoading" @click="pickUpdate('PICK_EXCEPTION')">{{ __('Flag Exception') }}</v-btn>
                <v-btn v-if="canDispatch" small color="success" class="mr-1 mb-1" :loading="actionLoading" :disabled="!canRelease" @click="releaseSale">{{ __('Release Goods') }}</v-btn>
                <v-checkbox
                  v-if="canDispatch"
                  v-model="allowPartialRelease"
                  dense
                  hide-details
                  class="mt-0 ml-2"
                  :label="__('Allow partial/exception release')"
                />
              </div>

              <v-row dense>
                <v-col cols="12" md="7">
                  <v-card outlined>
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Line Items') }}</v-card-title>
                    <v-card-text class="pt-0 px-2">
                      <div class="lines-wrap">
                        <v-simple-table dense>
                          <thead>
                            <tr>
                              <th>{{ __('Item') }}</th>
                              <th class="text-right">{{ __('Ord Qty') }}</th>
                              <th>{{ __('UOM') }}</th>
                              <th class="text-right">{{ __('Conv') }}</th>
                              <th class="text-right">{{ __('Ord Stock') }}</th>
                              <th class="text-right">{{ __('Picked Qty') }}</th>
                              <th class="text-right">{{ __('Picked Stock') }}</th>
                              <th>{{ __('Status') }}</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="line in lineRows" :key="line.id">
                              <td>
                                <div class="font-weight-medium">{{ line.item_code }}</div>
                                <div class="caption grey--text">{{ line.item_name || '-' }}</div>
                                <div class="caption grey--text" v-if="line.stock_uom">{{ __('Stock') }}: {{ line.stock_uom }}</div>
                              </td>
                              <td class="text-right">{{ qty(line.ordered_qty) }}</td>
                              <td>{{ line.uom }}</td>
                              <td class="text-right">{{ qty(line.conversion_factor, 6) }}</td>
                              <td class="text-right">{{ qty(line.ordered_stock_qty) }}</td>
                              <td class="text-right" style="min-width:110px">
                                <v-text-field
                                  v-model="line.picked_qty_input"
                                  dense
                                  hide-details
                                  outlined
                                  type="number"
                                  step="any"
                                  :disabled="!canPick"
                                  @change="onQtyChange(line)"
                                />
                              </td>
                              <td class="text-right">{{ qty(line.picked_stock_qty) }}</td>
                              <td style="min-width:140px">
                                <v-select
                                  v-model="line.pick_status"
                                  dense
                                  hide-details
                                  outlined
                                  :items="lineStatusOptions"
                                  :disabled="!canPick"
                                />
                              </td>
                            </tr>
                          </tbody>
                        </v-simple-table>
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="12" md="5">
                  <v-card outlined class="mb-2">
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Notes') }}</v-card-title>
                    <v-card-text class="pt-0">
                      <v-textarea v-model="pickNotes" v-if="canPick" rows="2" dense outlined auto-grow hide-details :label="__('Picker notes')" class="mb-2"/>
                      <v-textarea v-model="dispatchNotes" v-if="canDispatch" rows="2" dense outlined auto-grow hide-details :label="__('Dispatch notes')" />
                    </v-card-text>
                  </v-card>
                  <v-card outlined class="mb-2">
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Pick History') }}</v-card-title>
                    <v-card-text class="pt-0 events-wrap">
                      <div v-if="!detail.pick_events.length" class="grey--text">{{ __('No pick events') }}</div>
                      <div v-for="e in detail.pick_events.slice().reverse()" :key="`p-${e.id}`" class="mb-2">
                        <div class="caption font-weight-bold">{{ e.event_type }} | {{ dt(e.created_at) }}</div>
                        <div class="caption grey--text">{{ e.picker_user_id || '-' }}</div>
                        <div class="caption" v-if="e.notes">{{ e.notes }}</div>
                      </div>
                    </v-card-text>
                  </v-card>
                  <v-card outlined>
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Dispatch + Sync') }}</v-card-title>
                    <v-card-text class="pt-0 events-wrap">
                      <div v-for="e in detail.dispatch_events.slice().reverse()" :key="`d-${e.id}`" class="mb-2">
                        <div class="caption font-weight-bold">{{ e.event_type }} | {{ dt(e.created_at) }}</div>
                        <div class="caption grey--text">{{ e.dispatcher_user_id || '-' }}</div>
                        <div class="caption" v-if="e.notes">{{ e.notes }}</div>
                      </div>
                      <div v-if="!detail.dispatch_events.length" class="grey--text mb-2">{{ __('No dispatch events') }}</div>
                      <div class="caption font-weight-bold mt-2">{{ __('Outbox') }}</div>
                      <div v-for="o in detail.outbox_events.slice().reverse()" :key="`o-${o.event_id}`" class="caption mb-1">
                        {{ o.event_type }} | {{ o.status }} <span v-if="o.cloud_ref">| {{ o.cloud_ref }}</span>
                      </div>
                      <div v-if="!detail.outbox_events.length" class="grey--text">{{ __('No outbox events') }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </template>
            <div v-else class="grey--text text-center py-4">{{ __('Select a queue row') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { evntBus } from "../../bus";
import format from "../../format";

export default {
  name: "FulfillmentWorkspace",
  mixins: [format],
  props: {
    pos_profile: { type: [Object, String], default: null },
    current_role: { type: String, default: "" },
  },
  data() {
    return {
      queueRows: [],
      queueLoading: false,
      detailLoading: false,
      actionLoading: false,
      errorText: "",
      detailError: "",
      queueSearch: "",
      queueFilter: "all",
      selectedRef: "",
      detail: null,
      lineDrafts: {},
      pickNotes: "",
      dispatchNotes: "",
      allowPartialRelease: false,
      pollTimer: null,
      lineStatusOptions: ["NOT_PICKED", "PICKED", "PARTIAL", "EXCEPTION"],
    };
  },
  computed: {
    roleCode() {
      const p = (this.current_role || "").trim();
      if (p) return p;
      try {
        return (localStorage.getItem("pos_current_role") || "").trim();
      } catch (e) {
        return "";
      }
    },
    canPick() {
      return ["cline-Picker", "cline-Supervisor"].includes(this.roleCode);
    },
    canDispatch() {
      return ["cline-Dispatch", "cline-Supervisor"].includes(this.roleCode);
    },
    roleTitle() {
      if (this.roleCode === "cline-Picker") return __("Picker Queue");
      if (this.roleCode === "cline-Dispatch") return __("Dispatch Queue");
      if (this.roleCode === "cline-Supervisor") return __("Supervisor Fulfillment");
      return __("Fulfillment Queue");
    },
    profileName() {
      if (!this.pos_profile) return "";
      if (typeof this.pos_profile === "string") return this.pos_profile;
      return (this.pos_profile.name || "").trim();
    },
    relayBase() {
      const v =
        this.pos_profile && typeof this.pos_profile === "object"
          ? (this.pos_profile.custom_edge_relay_url || "").trim()
          : "";
      return (v || "http://127.0.0.1:8787").replace(/\/$/, "");
    },
    filters() {
      const rows = [{ value: "all", label: __("All"), color: "primary" }];
      if (this.canPick) {
        rows.push(
          { value: "pending", label: __("Pending"), color: "warning" },
          { value: "in_progress", label: __("In Progress"), color: "primary" },
          { value: "exception", label: __("Exception"), color: "error" },
          { value: "picked_ready", label: __("Picked Ready"), color: "success" }
        );
      }
      if (this.canDispatch) {
        rows.push({ value: "dispatch_ready", label: __("Dispatch Ready"), color: "success" });
      }
      return rows.filter((r, i, a) => a.findIndex((x) => x.value === r.value) === i);
    },
    filteredRows() {
      const s = (this.queueSearch || "").toLowerCase();
      return (this.queueRows || []).filter((r) => {
        const pick = String(r.pick_status || "").toUpperCase();
        const dispatch = String(r.dispatch_status || "").toUpperCase();
        if (this.queueFilter === "pending" && pick !== "PAID_PENDING_PICK") return false;
        if (this.queueFilter === "in_progress" && pick !== "PICK_IN_PROGRESS") return false;
        if (this.queueFilter === "exception" && pick !== "PICK_EXCEPTION") return false;
        if (this.queueFilter === "picked_ready" && pick !== "PICKED_READY_FOR_RELEASE") return false;
        if (this.queueFilter === "dispatch_ready" && !(pick === "PICKED_READY_FOR_RELEASE" && dispatch !== "RELEASED")) return false;
        if (!s) return true;
        return [r.local_sale_ref, r.token_id, r.customer_id, r.customer_name].filter(Boolean).join(" ").toLowerCase().includes(s);
      });
    },
    lineRows() {
      if (!this.detail || !this.detail.lines) return [];
      return this.detail.lines.map((line) => this.lineDrafts[line.id] || this.makeLineDraft(line));
    },
    canRelease() {
      if (!this.detail || !this.detail.sale) return false;
      const sale = this.detail.sale;
      if (String(sale.dispatch_status || "").toUpperCase() === "RELEASED") return false;
      const pick = String(sale.pick_status || "").toUpperCase();
      return parseInt(sale.paid || 0, 10) === 1 && (pick === "PICKED_READY_FOR_RELEASE" || (this.allowPartialRelease && pick === "PICK_EXCEPTION"));
    },
  },
  watch: {
    pos_profile: {
      handler() {
        this.fetchQueue(true);
      },
      deep: true,
    },
    roleCode() {
      if (this.roleCode === "cline-Dispatch" && this.queueFilter === "all") {
        this.queueFilter = "dispatch_ready";
      }
      this.fetchQueue(true);
    },
  },
  mounted() {
    if (this.roleCode === "cline-Dispatch") {
      this.queueFilter = "dispatch_ready";
    }
    this.fetchQueue(true);
    this.pollTimer = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      this.fetchQueue(false, true);
      if (this.selectedRef) this.fetchDetail(this.selectedRef, true);
    }, 5000);
  },
  beforeDestroy() {
    if (this.pollTimer) clearInterval(this.pollTimer);
  },
  methods: {
    showMessage(text, color) {
      evntBus.$emit("show_mesage", { text, color });
    },
    relayHeaders(extra = {}) {
      const headers = { ...extra };
      try {
        const relayKey = (localStorage.getItem("posa_relay_client_key") || "").trim();
        if (relayKey) headers["X-Relay-Client-Key"] = relayKey;
      } catch (e) {}
      return headers;
    },
    async getJson(path) {
      const r = await fetch(`${this.relayBase}${path}`, {
        headers: this.relayHeaders({ Accept: "application/json" }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.message || data.code || `HTTP ${r.status}`);
      return data;
    },
    async postJson(path, payload) {
      const r = await fetch(`${this.relayBase}${path}`, {
        method: "POST",
        headers: this.relayHeaders({ "Content-Type": "application/json", Accept: "application/json" }),
        body: JSON.stringify(payload || {}),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || data.ok === false) throw new Error(data.message || data.code || `HTTP ${r.status}`);
      return data;
    },
    async fetchQueue(preferSelect, quiet) {
      if (!this.profileName) return;
      if (!quiet) this.queueLoading = true;
      this.errorText = "";
      try {
        const q = `?pos_profile_id=${encodeURIComponent(this.profileName)}&limit=200`;
        const data = await this.getJson(`/relay/pick-queue${q}`);
        this.queueRows = Array.isArray(data.rows) ? data.rows : [];
        if (!this.queueRows.some((r) => r.local_sale_ref === this.selectedRef)) {
          this.selectedRef = "";
          this.detail = null;
        }
        if ((preferSelect || !this.selectedRef) && this.filteredRows.length) {
          this.selectRow(this.filteredRows[0]);
        }
      } catch (e) {
        this.errorText = `Relay queue load failed: ${String(e.message || e)}`;
      } finally {
        this.queueLoading = false;
      }
    },
    async selectRow(row) {
      if (!row || !row.local_sale_ref) return;
      this.selectedRef = row.local_sale_ref;
      await this.fetchDetail(this.selectedRef);
    },
    async fetchDetail(localSaleRef, quiet) {
      if (!localSaleRef) return;
      if (!quiet) this.detailLoading = true;
      this.detailError = "";
      try {
        const data = await this.getJson(`/api/transactions/${encodeURIComponent(localSaleRef)}`);
        this.detail = data;
        this.buildDraftsFromDetail();
      } catch (e) {
        this.detailError = `Relay sale detail load failed: ${String(e.message || e)}`;
      } finally {
        this.detailLoading = false;
      }
    },
    buildDraftsFromDetail() {
      const next = {};
      const eventMap = {};
      (this.detail.pick_events || []).forEach((e) => {
        if (!e || !e.payload || !Array.isArray(e.payload.line_updates)) return;
        e.payload.line_updates.forEach((u) => {
          const id = parseInt(u.line_id || u.id || 0, 10);
          if (id) eventMap[id] = u;
        });
      });
      (this.detail.lines || []).forEach((line) => {
        next[line.id] = this.makeLineDraft(line, eventMap[line.id]);
      });
      this.lineDrafts = next;
    },
    makeLineDraft(line, fallback) {
      const payload = line && typeof line.payload === "object" ? line.payload : {};
      const picker = payload && typeof payload.picker === "object" ? payload.picker : {};
      const fb = fallback || {};
      const orderedQty = this.num(line.qty, 0);
      const conv = this.lineConversion(line);
      const ordStock = this.num(payload.stock_qty, orderedQty * conv);
      const pickedQty = this.num(picker.picked_qty != null ? picker.picked_qty : fb.picked_qty, orderedQty);
      const pickedStock = this.num(
        picker.picked_stock_qty != null ? picker.picked_stock_qty : fb.picked_stock_qty,
        pickedQty * conv
      );
      return {
        id: line.id,
        item_code: line.item_code || "",
        item_name: line.item_name || "",
        ordered_qty: orderedQty,
        uom: line.uom || "",
        conversion_factor: conv,
        stock_uom: String(payload.stock_uom || "").trim(),
        ordered_stock_qty: ordStock,
        picked_qty: pickedQty,
        picked_qty_input: String(pickedQty),
        picked_stock_qty: pickedStock,
        pick_status: String(picker.pick_status || fb.pick_status || line.pick_status || "").toUpperCase() || (Math.abs(pickedQty - orderedQty) < 1e-9 ? "PICKED" : "PARTIAL"),
      };
    },
    lineConversion(line) {
      const payload = line && typeof line.payload === "object" ? line.payload : {};
      const direct = parseFloat(payload.conversion_factor);
      if (!isNaN(direct) && direct) return direct;
      const qty = this.num(line.qty, 0);
      const stockQty = parseFloat(payload.stock_qty);
      if (qty && !isNaN(stockQty)) return stockQty / qty;
      return 1;
    },
    num(v, fb) {
      const n = parseFloat(v);
      return isNaN(n) ? (fb == null ? 0 : fb) : n;
    },
    onQtyChange(line) {
      const q = Math.max(0, this.num(line.picked_qty_input, line.ordered_qty));
      line.picked_qty = q;
      line.picked_qty_input = String(q);
      line.picked_stock_qty = q * this.num(line.conversion_factor, 1);
      if (line.pick_status !== "EXCEPTION") {
        line.pick_status = Math.abs(q - line.ordered_qty) < 1e-9 ? "PICKED" : q > 0 ? "PARTIAL" : "NOT_PICKED";
      }
      this.$set(this.lineDrafts, line.id, { ...line });
    },
    markAllPicked() {
      this.lineRows.forEach((line) => {
        line.picked_qty = this.num(line.ordered_qty, 0);
        line.picked_qty_input = String(line.picked_qty);
        line.picked_stock_qty = line.picked_qty * this.num(line.conversion_factor, 1);
        if (line.pick_status !== "EXCEPTION") line.pick_status = "PICKED";
        this.$set(this.lineDrafts, line.id, { ...line });
      });
    },
    buildLineUpdates() {
      return this.lineRows.map((line) => ({
        line_id: line.id,
        item_code: line.item_code,
        ordered_qty: this.num(line.ordered_qty, 0),
        ordered_uom: line.uom || "",
        picked_qty: this.num(line.picked_qty, this.num(line.ordered_qty, 0)),
        picked_uom: line.uom || "",
        conversion_factor: this.num(line.conversion_factor, 1),
        picked_stock_qty: this.num(line.picked_stock_qty, 0),
        pick_status: String(line.pick_status || "").toUpperCase(),
      }));
    },
    lineSummary(updates) {
      const s = { total_count: updates.length, picked_count: 0, partial_count: 0, exception_count: 0, not_picked_count: 0 };
      updates.forEach((u) => {
        const k = String(u.pick_status || "").toUpperCase();
        if (k === "PICKED") s.picked_count += 1;
        else if (k === "PARTIAL") s.partial_count += 1;
        else if (k === "EXCEPTION") s.exception_count += 1;
        else if (k === "NOT_PICKED") s.not_picked_count += 1;
      });
      return s;
    },
    async pickUpdate(status) {
      if (!this.selectedRef) return;
      this.actionLoading = true;
      try {
        const line_updates = this.buildLineUpdates();
        const payload = {
          local_sale_ref: this.selectedRef,
          picking_status: status,
          picker_user_id: (frappe.session && frappe.session.user) || "",
          pos_profile_id: this.profileName,
          role: this.roleCode,
          notes: this.pickNotes || "",
          line_updates,
          line_summary: this.lineSummary(line_updates),
        };
        const r = await this.postJson("/relay/pick/update", payload);
        this.showMessage(`Pick status updated: ${r.pick_status || status}`, "success");
        await this.fetchDetail(this.selectedRef);
        await this.fetchQueue(false);
      } catch (e) {
        this.showMessage(`Pick update failed: ${String(e.message || e)}`, "error");
      } finally {
        this.actionLoading = false;
      }
    },
    markPickedReady() {
      if (this.lineRows.some((l) => ["EXCEPTION", "NOT_PICKED"].includes(String(l.pick_status || "").toUpperCase()))) {
        this.showMessage(__("Cannot mark picked-ready while any line is EXCEPTION/NOT_PICKED."), "warning");
        return;
      }
      this.pickUpdate("PICKED_READY_FOR_RELEASE");
    },
    async releaseSale() {
      if (!this.selectedRef) return;
      this.actionLoading = true;
      try {
        const line_updates = this.buildLineUpdates();
        const r = await this.postJson("/relay/dispatch/release", {
          local_sale_ref: this.selectedRef,
          dispatcher_user_id: (frappe.session && frappe.session.user) || "",
          allow_partial: !!this.allowPartialRelease,
          notes: this.dispatchNotes || "",
          role: this.roleCode,
          line_summary: this.lineSummary(line_updates),
        });
        this.showMessage(`Dispatch updated: ${r.dispatch_status || "RELEASED"}`, "success");
        await this.fetchDetail(this.selectedRef);
        await this.fetchQueue(false);
      } catch (e) {
        this.showMessage(`Dispatch failed: ${String(e.message || e)}`, "error");
      } finally {
        this.actionLoading = false;
      }
    },
    refreshAll() {
      this.fetchQueue(false);
      if (this.selectedRef) this.fetchDetail(this.selectedRef);
    },
    dt(v) {
      if (!v) return "-";
      try {
        if (frappe.datetime && frappe.datetime.str_to_user) return frappe.datetime.str_to_user(v);
      } catch (e) {}
      return String(v);
    },
    money(v) {
      const c = (this.pos_profile && this.pos_profile.currency) || "";
      return `${this.currencySymbol(c)} ${this.formtCurrency(this.num(v, 0))}`;
    },
    qty(v, p) {
      return this.formtFloat(this.num(v, 0), p || this.float_precision || 2);
    },
    pickColor(s) {
      const v = String(s || "").toUpperCase();
      if (v === "PAID_PENDING_PICK") return "warning";
      if (v === "PICK_IN_PROGRESS") return "primary";
      if (v === "PICK_EXCEPTION") return "error";
      if (v === "PICKED_READY_FOR_RELEASE") return "success";
      return "grey";
    },
    dispatchColor(s) {
      return String(s || "").toUpperCase() === "RELEASED" ? "success" : "warning";
    },
    syncColor(s) {
      return String(s || "").toUpperCase() === "SALE_SYNCED_SI_SUBMITTED" ? "success" : "warning";
    },
  },
};
</script>

<style scoped>
.queue-list {
  max-height: 65vh;
  overflow-y: auto;
  border: 1px solid rgba(0,0,0,.06);
  border-radius: 6px;
}
.active {
  background: rgba(33, 150, 243, .08);
}
.lines-wrap {
  max-height: 36vh;
  overflow: auto;
}
.events-wrap {
  max-height: 26vh;
  overflow-y: auto;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
