<template>
  <v-list-item class="workflow-ticket-row">
    <v-list-item-content>
      <div class="workflow-ticket-row-top">
        <div class="workflow-ticket-row-customer">
          {{ row.customer_name || __('Unknown Customer') }}
        </div>
        <v-chip x-small :color="statusColor(row.display_status)" text-color="white">
          {{ row.display_status || __('Unknown') }}
        </v-chip>
      </div>

      <WorkflowStateStrip :row="row" />

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
</template>

<script>
import WorkflowStateStrip from './WorkflowStateStrip.vue';
import { workflowStatusColor } from './workflowDisplay';

export default {
  components: {
    WorkflowStateStrip,
  },
  props: {
    row: {
      type: Object,
      required: true,
    },
    nowMs: {
      type: Number,
      required: true,
    },
  },
  methods: {
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
      return workflowStatusColor(status);
    },
  },
};
</script>

<style scoped>
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
</style>
