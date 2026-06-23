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
            <WorkflowTicketRow
              v-for="row in rows"
              :key="row.workflow_state || row.token_id || row.sales_order || row.sales_invoice"
              :row="row"
              :now-ms="nowMs"
            />
          </v-list>
        </v-card>
      </v-slide-x-transition>
    </div>
  </div>
</template>

<script>
import { evntBus } from '../../../bus';
import WorkflowTicketRow from './WorkflowTicketRow.vue';
import { workflowStatusColor } from './workflowDisplay';

export default {
  components: {
    WorkflowTicketRow,
  },
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
    normalizeRelayUrl(relayUrl) {
      return String(relayUrl || '').trim().replace(/\/$/, '');
    },
    getRelayBaseUrl() {
      try {
        const bootSite =
          (typeof frappe !== 'undefined' &&
            frappe.boot &&
            (frappe.boot.sitename || frappe.boot.site_name)) ||
          '';
        const browserSite =
          typeof window !== 'undefined' && window.location
            ? window.location.host || 'site'
            : 'site';
        const site = bootSite || browserSite;
        const profile =
          this.pos_profile && typeof this.pos_profile === 'object'
            ? String(this.pos_profile.name || 'default').trim() || 'default'
            : 'default';
        const sites = Array.from(new Set([site, bootSite, browserSite].filter(Boolean)));
        let raw = '';
        for (const siteKey of sites) {
          raw =
            localStorage.getItem(`posa_edge_relay_config:${siteKey}:${profile}`) ||
            localStorage.getItem(`posa_edge_relay_config:${siteKey}:__default__`);
          if (raw) break;
        }
        if (!raw) return '';
        const parsed = JSON.parse(raw) || {};
        return this.normalizeRelayUrl(parsed.relay_url);
      } catch (e) {
        return '';
      }
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
    statusColor(status) {
      return workflowStatusColor(status);
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

.workflow-spin {
  animation: workflowSpin 0.9s linear infinite;
}

@keyframes workflowSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
