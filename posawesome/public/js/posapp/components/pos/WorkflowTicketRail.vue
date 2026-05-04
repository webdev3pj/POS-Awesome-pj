<template>
  <div>
    <div
      v-if="expanded && isMobile"
      class="workflow-ticket-rail-backdrop"
      @click="toggleExpanded(false)"
    ></div>
    <div
      class="workflow-ticket-rail"
      :class="{ expanded: expanded, mobile: isMobile, desktop: !isMobile }"
    >
      <div class="workflow-ticket-rail-handle">
        <v-badge
          :class="{ 'workflow-ticket-badge-empty': !hasPending }"
          :content="String(pendingCount)"
          :value="true"
          color="error"
          overlap
        >
          <v-btn
            color="primary"
            dark
            small
            fab
            @click="toggleExpanded()"
            :title="expanded ? __('Hide order monitor') : __('Show order monitor')"
          >
            <v-icon>mdi-ticket-outline</v-icon>
          </v-btn>
        </v-badge>
        <div v-if="isMobile" class="workflow-ticket-rail-label">
          {{ expanded ? __('Orders') : pendingCount }}
        </div>
      </div>

      <v-slide-x-transition>
        <v-card
          v-show="expanded"
          class="workflow-ticket-rail-panel"
          elevation="8"
        >
          <div class="workflow-ticket-rail-header">
            <div>
              <div class="workflow-ticket-rail-title">{{ __('Order Monitor') }}</div>
              <div class="workflow-ticket-rail-subtitle">
                {{ monitorScopeLabel }}
              </div>
            </div>
            <v-btn icon small @click="toggleExpanded(false)">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </div>

          <div class="workflow-ticket-rail-filters">
            <v-btn-toggle v-model="filterMode" dense mandatory>
              <v-btn small value="all">{{ __('All (date)') }}</v-btn>
              <v-btn small value="mine">{{ __('Mine') }}</v-btn>
            </v-btn-toggle>
            <v-btn icon small @click="manualRefresh" :disabled="loading">
              <v-icon :class="{ 'workflow-spin': loading }">mdi-refresh</v-icon>
            </v-btn>
          </div>

          <div class="workflow-ticket-rail-summary">
            <v-chip x-small class="mr-1 mb-1" color="primary" text-color="white">
              {{ __('Pending') }}: {{ pendingCount }}
            </v-chip>
            <v-chip
              v-for="chip in summaryChips"
              :key="chip.key"
              x-small
              class="mr-1 mb-1"
              :color="chip.color"
              text-color="white"
            >
              {{ chip.label }}: {{ chip.count }}
            </v-chip>
          </div>

          <div v-if="errorText" class="workflow-ticket-rail-error">
            {{ errorText }}
          </div>

          <div v-if="!profileName" class="workflow-ticket-rail-empty">
            {{ __('Open POS with a profile to monitor workflow orders.') }}
          </div>

          <div v-else-if="!rows.length && !loading" class="workflow-ticket-rail-empty">
            {{ __('No pending orders for this profile/date.') }}
          </div>

          <v-list v-else dense class="workflow-ticket-rail-list">
            <v-list-item
              v-for="row in rows"
              :key="row.workflow_state || row.token_id || row.sales_order || row.sales_invoice"
              class="workflow-ticket-row"
            >
              <v-list-item-content>
                <div class="workflow-ticket-row-top">
                  <div class="workflow-ticket-row-customer">
                    {{ row.customer_name || __('Unknown Customer') }}
                  </div>
                  <v-chip x-small :color="statusColor(row.display_status)" text-color="white">
                    {{ row.display_status || __('Unknown') }}
                  </v-chip>
                </div>
                <div class="workflow-ticket-current-state">
                  {{ workflowCurrentLabel(row) }}
                </div>
                <div
                  class="workflow-state-strip"
                  :aria-label="workflowStateAria(row)"
                >
                  <div
                    v-for="step in workflowSteps(row)"
                    :key="step.key"
                    class="workflow-state-step"
                    :class="'workflow-state-step-' + step.state"
                  >
                    <span class="workflow-state-dot">
                      <v-icon x-small>{{ step.icon }}</v-icon>
                    </span>
                    <span class="workflow-state-label">{{ step.label }}</span>
                  </div>
                </div>
                <div class="workflow-ticket-state-fields">
                  <span>{{ __('Token') }}: {{ row.token_status || '-' }}</span>
                  <span>{{ __('Pick') }}: {{ row.picking_status || '-' }}</span>
                  <span>{{ __('Dispatch') }}: {{ row.dispatch_status || '-' }}</span>
                </div>
                <div class="workflow-ticket-row-meta">
                  <span>{{ __('SA') }}: {{ row.sales_associate_name || row.sales_associate_user || '-' }}</span>
                </div>
                <div class="workflow-ticket-row-meta">
                  <span>{{ __('Taken') }}: {{ formatDateTime(row.order_taken_at) }}</span>
                </div>
                <div class="workflow-ticket-row-meta">
                  <span>{{ __('Time in status') }}: {{ durationSince(row.status_changed_at || row.order_taken_at) }}</span>
                </div>
                <div class="workflow-ticket-row-meta workflow-ticket-row-total">
                  <span>{{ __('Total') }}: {{ formatMoney(row.grand_total, row.currency) }}</span>
                </div>
                <div class="workflow-ticket-row-ids">
                  <small v-if="row.sales_order">SO: {{ row.sales_order }}</small>
                  <small v-if="row.sales_invoice">SI: {{ row.sales_invoice }}</small>
                  <small v-if="row.token_id">{{ __('Token') }}: {{ row.token_id }}</small>
                </div>
              </v-list-item-content>
            </v-list-item>
          </v-list>
        </v-card>
      </v-slide-x-transition>
    </div>
  </div>
</template>

<script>
import { evntBus } from '../../bus';

export default {
  props: {
    pos_profile: {
      type: [Object, String],
      default: null,
    },
    pos_opening_shift: {
      type: [Object, String],
      default: null,
    },
    business_date: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      expanded: false,
      filterMode: 'all',
      rows: [],
      summary: {
        pending_count: 0,
        status_counts: {},
        server_time: '',
      },
      loading: false,
      errorText: '',
      pollTimer: null,
      clockTimer: null,
      nowMs: Date.now(),
      viewportWidth: typeof window !== 'undefined' ? window.innerWidth : 1280,
      visibilityHidden:
        typeof document !== 'undefined' && typeof document.hidden !== 'undefined'
          ? !!document.hidden
          : false,
    };
  },
  computed: {
    profileName() {
      return this.extractDocName(this.pos_profile);
    },
    openingShiftName() {
      return this.extractDocName(this.pos_opening_shift);
    },
    scopeBusinessDate() {
      const explicit = (this.business_date || '').trim();
      if (explicit) return explicit;
      if (typeof frappe !== 'undefined' && frappe.datetime && frappe.datetime.nowdate) {
        return frappe.datetime.nowdate();
      }
      return new Date().toISOString().slice(0, 10);
    },
    mineOnly() {
      return this.filterMode === 'mine';
    },
    pendingCount() {
      return parseInt((this.summary && this.summary.pending_count) || this.rows.length || 0, 10) || 0;
    },
    hasPending() {
      return this.pendingCount > 0;
    },
    isMobile() {
      return this.viewportWidth < 960;
    },
    monitorScopeLabel() {
      const profile = this.profileName || __('No profile');
      const dateLabel = this.scopeBusinessDate || '-';
      return `${__('Profile')}: ${profile} | ${__('Date')}: ${dateLabel}`;
    },
    summaryChips() {
      const raw = (this.summary && this.summary.status_counts) || {};
      return Object.keys(raw)
        .sort()
        .map((key) => ({
          key: key,
          label: __(key),
          count: raw[key],
          color: this.statusColor(key),
        }));
    },
  },
  watch: {
    pos_profile: {
      handler() {
        this.fetchBoard(true);
        this.restartPolling();
      },
      deep: true,
    },
    pos_opening_shift: {
      handler() {
        this.fetchBoard(true);
        this.restartPolling();
      },
      deep: true,
    },
    business_date() {
      this.fetchBoard(true);
      this.restartPolling();
    },
    filterMode() {
      this.fetchBoard(false);
      this.restartPolling();
    },
    expanded() {
      this.refreshClockTimer();
      this.restartPolling();
      this.emitSummaryChanged();
      if (this.expanded) {
        this.fetchBoard(false);
      }
    },
  },
  methods: {
    extractDocName(value) {
      if (!value) return '';
      if (typeof value === 'string') return value;
      return (value.name || '').toString();
    },
    getRelayBaseUrl() {
      const profile = this.pos_profile && typeof this.pos_profile === 'object' ? this.pos_profile : {};
      return String(profile.custom_edge_relay_url || '').trim().replace(/\/$/, '');
    },
    getRelayClientHeaders(extra = {}) {
      const headers = { ...extra };
      try {
        const relayKey = (localStorage.getItem('posa_relay_client_key') || '').trim();
        if (relayKey) headers['X-Relay-Client-Key'] = relayKey;
      } catch (e) {}
      return headers;
    },
    relayFallbackEnabled() {
      const profile = this.pos_profile && typeof this.pos_profile === 'object' ? this.pos_profile : {};
      return parseInt(profile.custom_have_token || 0, 10) === 1 && !!this.getRelayBaseUrl();
    },
    toggleExpanded(forceValue) {
      if (typeof forceValue === 'boolean') {
        this.expanded = forceValue;
        return;
      }
      this.expanded = !this.expanded;
    },
    onToggleRequested() {
      this.toggleExpanded();
    },
    emitSummaryChanged() {
      evntBus.$emit('workflow_monitor_summary_changed', {
        profile_name: this.profileName,
        pending_count: this.pendingCount,
        expanded: this.expanded,
      });
    },
    handleVisibilityChange() {
      this.visibilityHidden = typeof document !== 'undefined' ? !!document.hidden : false;
      this.restartPolling();
      this.refreshClockTimer();
    },
    handleResize() {
      this.viewportWidth = window.innerWidth;
    },
    pollIntervalMs() {
      if (this.expanded && !this.visibilityHidden) {
        return 5000;
      }
      return 12000;
    },
    restartPolling() {
      this.stopPolling();
      if (!this.profileName) {
        return;
      }
      this.scheduleNextPoll();
    },
    scheduleNextPoll() {
      this.stopPolling();
      this.pollTimer = setTimeout(async () => {
        await this.fetchBoard(true);
        this.scheduleNextPoll();
      }, this.pollIntervalMs());
    },
    stopPolling() {
      if (this.pollTimer) {
        clearTimeout(this.pollTimer);
        this.pollTimer = null;
      }
    },
    refreshClockTimer() {
      if (this.clockTimer) {
        clearInterval(this.clockTimer);
        this.clockTimer = null;
      }
      if (this.expanded && !this.visibilityHidden) {
        this.clockTimer = setInterval(() => {
          this.nowMs = Date.now();
        }, 1000);
      }
    },
    requestApi(args) {
      return new Promise((resolve, reject) => {
        frappe.call({
          method: 'posawesome.posawesome.api.posapp.get_relay_workflow_monitor_board',
          args: args,
          async: true,
          callback: (r) => {
            if (r && r.exc) {
              reject(new Error(__('Unable to load workflow monitor.')));
              return;
            }
            resolve((r && r.message) || {});
          },
          error: (err) => {
            reject(
              new Error(
                (err && err.message) || __('Unable to load workflow monitor.')
              )
            );
          },
        });
      });
    },
    async requestRelayApi(args) {
      const base = this.getRelayBaseUrl();
      if (!base) {
        throw new Error(__('Relay monitor is not configured.'));
      }
      const params = new URLSearchParams();
      params.set('pos_profile', (args && args.pos_profile) || this.profileName || '');
      params.set('business_date', (args && args.business_date) || this.scopeBusinessDate || '');
      params.set('mine_only', args && args.mine_only ? '1' : '0');
      params.set('include_released', args && args.include_released ? '1' : '0');
      params.set('limit_page_length', String((args && args.limit_page_length) || 200));
      try {
        if (typeof frappe !== 'undefined' && frappe.session && frappe.session.user) {
          params.set('user_id', frappe.session.user);
        }
      } catch (e) {}

      const resp = await fetch(`${base}/relay/workflow/monitor-board?${params.toString()}`, {
        method: 'GET',
        headers: this.getRelayClientHeaders({ Accept: 'application/json' }),
      });
      let payload = {};
      try {
        payload = (await resp.json()) || {};
      } catch (e) {
        payload = {};
      }
      if (!resp.ok || payload.ok === false) {
        throw new Error(payload.message || __('Unable to load workflow monitor from relay.'));
      }
      return payload;
    },
    async fetchBoard(silent) {
      if (!this.profileName) {
        this.rows = [];
        this.summary = { pending_count: 0, status_counts: {}, server_time: '' };
        this.errorText = '';
        return;
      }

      if (!silent) {
        this.loading = true;
      }

      try {
        const requestArgs = {
          pos_profile: this.profileName,
          business_date: this.scopeBusinessDate,
          scope_mode: 'business_date',
          pos_opening_shift: this.openingShiftName || '',
          mine_only: this.mineOnly ? 1 : 0,
          include_released: 0,
          limit_page_length: 200,
        };
        let payload = null;
        const relayEnabled = this.relayFallbackEnabled();
        if (relayEnabled) {
          try {
            payload = await this.requestRelayApi(requestArgs);
          } catch (relayErr) {
            payload = await this.requestApi(requestArgs);
          }
        } else {
          payload = await this.requestApi(requestArgs);
        }

        this.summary = payload.summary || {
          pending_count: 0,
          status_counts: {},
          server_time: '',
        };
        this.rows = Array.isArray(payload.rows) ? payload.rows : [];
        this.errorText = '';
        this.emitSummaryChanged();
      } catch (e) {
        this.errorText = (e && e.message) || __('Unable to load workflow monitor.');
      } finally {
        this.loading = false;
      }
    },
    manualRefresh() {
      this.fetchBoard(false);
      this.restartPolling();
    },
    onRefreshRequested() {
      this.fetchBoard(true);
      this.restartPolling();
    },
    parseDate(value) {
      if (!value) return null;
      if (value instanceof Date) return isNaN(value.getTime()) ? null : value;
      var raw = String(value).trim();
      if (!raw) return null;
      if (/^\d{4}-\d{2}-\d{2}\s/.test(raw)) {
        raw = raw.replace(' ', 'T');
      }
      var dateObj = new Date(raw);
      if (!isNaN(dateObj.getTime())) return dateObj;
      return null;
    },
    formatDateTime(value) {
      var dt = this.parseDate(value);
      if (!dt) return '-';
      try {
        return dt.toLocaleString();
      } catch (e) {
        return String(value || '-');
      }
    },
    durationSince(value) {
      var dt = this.parseDate(value);
      if (!dt) return '-';
      var deltaMs = Math.max(0, this.nowMs - dt.getTime());
      var totalSec = Math.floor(deltaMs / 1000);
      var days = Math.floor(totalSec / 86400);
      var hours = Math.floor((totalSec % 86400) / 3600);
      var mins = Math.floor((totalSec % 3600) / 60);
      var secs = totalSec % 60;
      if (days > 0) return days + 'd ' + hours + 'h';
      if (hours > 0) return hours + 'h ' + mins + 'm';
      if (mins > 0) return mins + 'm ' + secs + 's';
      return secs + 's';
    },
    formatMoney(amount, currency) {
      var num = parseFloat(amount || 0);
      if (isNaN(num)) num = 0;
      try {
        if (currency) {
          return new Intl.NumberFormat(undefined, {
            style: 'currency',
            currency: currency,
          }).format(num);
        }
      } catch (e) {
        // fallback to plain format
      }
      return (currency ? currency + ' ' : '') + num.toFixed(2);
    },
    statusColor(status) {
      var s = (status || '').toString();
      if (s === 'Unpaid') return 'orange';
      if (s === 'Paid') return 'blue';
      if (s === 'Picking') return 'deep-purple';
      if (s === 'Picked') return 'green';
      if (s === 'On Hold') return 'red darken-1';
      if (s === 'Dispatched') return 'teal';
      return 'grey';
    },
    normalizeWorkflowStatus(value) {
      return String(value || '').trim().toLowerCase();
    },
    workflowCurrentLabel(row) {
      var displayStatus = String((row && row.display_status) || '').trim();
      var tokenStatus = this.normalizeWorkflowStatus(row && row.token_status);
      var pickingStatus = this.normalizeWorkflowStatus(row && row.picking_status);
      var dispatchStatus = this.normalizeWorkflowStatus(row && row.dispatch_status);

      if (displayStatus === 'Dispatched' || dispatchStatus === 'released') {
        return __('Current state: Dispatched / released');
      }
      if (displayStatus === 'On Hold' || dispatchStatus === 'on hold' || pickingStatus === 'exception') {
        return __('Current state: On hold / exception');
      }
      if (displayStatus === 'Picked' || pickingStatus === 'picked') {
        return __('Current state: Picked, ready for dispatch');
      }
      if (displayStatus === 'Picking' || pickingStatus === 'in progress') {
        return __('Current state: Picking in progress');
      }
      if (displayStatus === 'Paid' || tokenStatus === 'paid') {
        return __('Current state: Paid, waiting for picking');
      }
      if (tokenStatus === 'expired') {
        return __('Current state: Token expired');
      }
      if (tokenStatus === 'abandoned') {
        return __('Current state: Token abandoned');
      }
      return __('Current state: Token created, payment pending');
    },
    workflowSteps(row) {
      var tokenStatus = this.normalizeWorkflowStatus(row && row.token_status);
      var pickingStatus = this.normalizeWorkflowStatus(row && row.picking_status);
      var dispatchStatus = this.normalizeWorkflowStatus(row && row.dispatch_status);
      var isPaid = tokenStatus === 'paid';
      var isPicking = pickingStatus === 'in progress';
      var isPicked = pickingStatus === 'picked';
      var isException = pickingStatus === 'exception' || dispatchStatus === 'on hold';
      var isReleased = dispatchStatus === 'released';
      var isTerminalToken = tokenStatus === 'expired' || tokenStatus === 'abandoned';

      var paymentState = 'pending';
      if (isPaid || isPicked || isReleased || isPicking || isException) {
        paymentState = 'done';
      } else if (isTerminalToken) {
        paymentState = 'blocked';
      } else {
        paymentState = 'active';
      }

      var pickState = 'pending';
      if (isPicked || isReleased) {
        pickState = 'done';
      } else if (isException) {
        pickState = 'blocked';
      } else if (isPicking || isPaid) {
        pickState = 'active';
      }

      var dispatchState = 'pending';
      if (isReleased) {
        dispatchState = 'done';
      } else if (isException) {
        dispatchState = 'blocked';
      } else if (isPicked) {
        dispatchState = 'active';
      }

      return [
        {
          key: 'token',
          label: __('Token'),
          icon: 'mdi-ticket-confirmation-outline',
          state: isTerminalToken ? 'blocked' : 'done',
        },
        {
          key: 'payment',
          label: __('Payment'),
          icon: 'mdi-cash-register',
          state: paymentState,
        },
        {
          key: 'pick',
          label: __('Pick'),
          icon: 'mdi-package-variant-closed',
          state: pickState,
        },
        {
          key: 'dispatch',
          label: __('Dispatch'),
          icon: 'mdi-truck-check-outline',
          state: dispatchState,
        },
      ];
    },
    workflowStateAria(row) {
      return [
        this.workflowCurrentLabel(row),
        __('Token') + ': ' + ((row && row.token_status) || '-'),
        __('Pick') + ': ' + ((row && row.picking_status) || '-'),
        __('Dispatch') + ': ' + ((row && row.dispatch_status) || '-'),
      ].join(', ');
    },
  },
  mounted() {
    this.fetchBoard(true);
    this.restartPolling();
    this.refreshClockTimer();
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', this.handleVisibilityChange);
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', this.handleResize);
    }
    this.emitSummaryChanged();
    evntBus.$on('workflow_monitor_refresh_requested', this.onRefreshRequested);
    evntBus.$on('workflow_monitor_toggle_requested', this.onToggleRequested);
  },
  beforeDestroy() {
    this.stopPolling();
    if (this.clockTimer) {
      clearInterval(this.clockTimer);
      this.clockTimer = null;
    }
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    }
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', this.handleResize);
    }
    evntBus.$off('workflow_monitor_refresh_requested', this.onRefreshRequested);
    evntBus.$off('workflow_monitor_toggle_requested', this.onToggleRequested);
  },
};
</script>

<style scoped>
.workflow-ticket-rail-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.28);
  z-index: 89;
}

.workflow-ticket-rail {
  position: fixed;
  left: 14px;
  top: 124px;
  z-index: 90;
  display: flex;
  align-items: flex-start;
}

.workflow-ticket-rail.desktop {
  left: 14px;
  top: 124px;
}

.workflow-ticket-rail.mobile {
  top: 76px;
  left: 6px;
}

.workflow-ticket-rail-handle {
  width: 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.workflow-ticket-rail.desktop .workflow-ticket-rail-handle {
  width: 36px;
  min-height: 42px;
  padding: 4px 0;
  border-radius: 10px;
  border: 1px solid rgba(8, 82, 148, 0.16);
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.1);
  backdrop-filter: blur(3px);
}

.workflow-ticket-rail.desktop .workflow-ticket-rail-handle :deep(.v-badge__badge) {
  min-width: 16px;
  height: 16px;
  font-size: 9px;
  line-height: 16px;
}

.workflow-ticket-rail.desktop .workflow-ticket-badge-empty :deep(.v-badge__badge) {
  background-color: #94a3b8 !important;
  color: #f8fafc !important;
}

.workflow-ticket-rail.desktop .workflow-ticket-rail-handle :deep(.v-btn) {
  width: 28px !important;
  height: 28px !important;
}

.workflow-ticket-rail-label {
  font-size: 11px;
  line-height: 1;
  color: #1f2937;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 10px;
  padding: 4px 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
}

.workflow-ticket-rail-panel {
  width: min(380px, calc(100vw - 70px));
  max-height: calc(100vh - 110px);
  overflow: hidden;
  margin-left: 6px;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
}

.workflow-ticket-rail.mobile .workflow-ticket-rail-panel {
  width: calc(100vw - 72px);
  max-height: calc(100vh - 92px);
}

.workflow-ticket-rail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px 4px;
}

.workflow-ticket-rail.desktop .workflow-ticket-rail-panel {
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.12) !important;
}

.workflow-ticket-rail-title {
  font-weight: 700;
  font-size: 14px;
}

.workflow-ticket-rail-subtitle {
  color: #6b7280;
  font-size: 11px;
  margin-top: 2px;
  word-break: break-all;
}

.workflow-ticket-rail-filters {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 12px 2px;
}

.workflow-ticket-rail-summary {
  padding: 6px 12px 2px;
}

.workflow-ticket-rail-error {
  margin: 4px 12px;
  padding: 6px 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 12px;
}

.workflow-ticket-rail-empty {
  padding: 14px 12px;
  color: #6b7280;
  font-size: 12px;
}

.workflow-ticket-rail-list {
  overflow-y: auto;
  padding-bottom: 6px;
}

.workflow-ticket-row {
  align-items: flex-start;
  border-top: 1px solid #eef2f7;
}

.workflow-ticket-row-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 3px;
}

.workflow-ticket-row-customer {
  font-weight: 600;
  font-size: 12px;
  line-height: 1.2;
  color: #111827;
}

.workflow-ticket-current-state {
  margin: 2px 0 5px;
  color: #0f172a;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.25;
}

.workflow-state-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 4px;
  margin: 5px 0;
}

.workflow-state-step {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 4px 5px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
  color: #64748b;
}

.workflow-state-step-done {
  border-color: #a7f3d0;
  background: #ecfdf5;
  color: #047857;
}

.workflow-state-step-active {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.12);
}

.workflow-state-step-blocked {
  border-color: #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.workflow-state-dot {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.workflow-state-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10px;
  font-weight: 700;
}

.workflow-ticket-state-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 4px 0 5px;
}

.workflow-ticket-state-fields span {
  max-width: 100%;
  padding: 2px 5px;
  border-radius: 5px;
  background: #f1f5f9;
  color: #475569;
  font-size: 10px;
  line-height: 1.25;
}

.workflow-ticket-row-meta {
  color: #374151;
  font-size: 11px;
  line-height: 1.35;
}

.workflow-ticket-row-total {
  font-weight: 600;
  color: #111827;
}

.workflow-ticket-row-ids {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  color: #6b7280;
  font-size: 10px;
}

.workflow-spin {
  animation: workflowSpin 0.9s linear infinite;
}

@keyframes workflowSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
