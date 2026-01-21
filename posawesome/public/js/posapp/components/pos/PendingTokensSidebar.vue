<template>
  <div class="pending-tokens-sidebar" :class="{ 'expanded': isExpanded }">
    <!-- Collapsed State - Just shows count badge -->
    <div 
      class="sidebar-toggle"
      @click="toggleSidebar"
      :title="isExpanded ? __('Collapse') : __('Pending Tokens')"
    >
      <v-badge
        :content="pendingCount"
        :value="pendingCount > 0"
        color="warning"
        overlap
        offset-x="10"
        offset-y="10"
      >
        <v-icon :color="pendingCount > 0 ? 'warning' : 'grey'" size="28">
          mdi-ticket-outline
        </v-icon>
      </v-badge>
      <span v-if="isExpanded" class="toggle-text ml-2">{{ __('Pending') }}</span>
      <v-icon v-if="isExpanded" small class="ml-auto">mdi-chevron-left</v-icon>
    </div>

    <!-- Expanded State - Shows token list -->
    <div v-if="isExpanded" class="sidebar-content">
      <div class="sidebar-header">
        <span class="text-subtitle-2 font-weight-bold">
          {{ __('Pending Tokens') }}
        </span>
        <v-chip small color="warning" dark class="ml-2">{{ pendingCount }}</v-chip>
        <v-btn icon x-small class="ml-auto" @click="loadPendingTokens" :loading="loading">
          <v-icon small>mdi-refresh</v-icon>
        </v-btn>
      </div>

      <v-divider></v-divider>

      <!-- Token List -->
      <div class="token-list" v-if="pendingTokens.length">
        <div 
          v-for="token in pendingTokens" 
          :key="token.name"
          class="token-item"
          @click="selectToken(token)"
        >
          <div class="token-header">
            <span class="token-number">{{ token.token_number }}</span>
            <span class="token-amount">{{ formtCurrency(token.total_amount) }}</span>
          </div>
          <div class="token-details">
            <span class="customer-name">{{ token.customer_name }}</span>
            <span class="token-time">{{ formatTime(token.token_datetime) }}</span>
          </div>
          <div class="token-associate" v-if="token.sales_associate_name">
            <v-icon x-small class="mr-1">mdi-account</v-icon>
            {{ token.sales_associate_name }}
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="empty-state">
        <v-icon size="40" color="grey lighten-1">mdi-ticket-outline</v-icon>
        <div class="text-caption grey--text mt-2">{{ __('No pending tokens') }}</div>
      </div>

      <!-- Quick Stats -->
      <div class="sidebar-footer" v-if="pendingTokens.length">
        <div class="stat-row">
          <span class="stat-label">{{ __('Total Value') }}:</span>
          <span class="stat-value">{{ formtCurrency(totalPendingAmount) }}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">{{ __('Oldest') }}:</span>
          <span class="stat-value">{{ oldestTokenTime }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { evntBus } from '../../bus';
import format from '../../format';

export default {
  name: 'PendingTokensSidebar',
  mixins: [format],

  data() {
    return {
      isExpanded: false,
      loading: false,
      pendingTokens: [],
      posProfile: null,
      posOpeningShift: null,
      refreshInterval: null,
      isCashier: false
    };
  },

  computed: {
    pendingCount() {
      return this.pendingTokens.length;
    },
    totalPendingAmount() {
      return this.pendingTokens.reduce((sum, token) => sum + (token.total_amount || 0), 0);
    },
    oldestTokenTime() {
      if (!this.pendingTokens.length) return '-';
      const oldest = this.pendingTokens[this.pendingTokens.length - 1];
      return this.formatTime(oldest.token_datetime);
    }
  },

  methods: {
    toggleSidebar() {
      this.isExpanded = !this.isExpanded;
      if (this.isExpanded) {
        this.loadPendingTokens();
      }
    },

    async loadPendingTokens() {
      if (!this.posProfile) return;
      
      this.loading = true;
      try {
        const response = await frappe.call({
          method: 'posawesome.posawesome.api.token.get_pending_tokens',
          args: {
            pos_profile: this.posProfile.name
          }
        });
        this.pendingTokens = response.message || [];
      } catch (error) {
        console.error('Error loading pending tokens:', error);
      } finally {
        this.loading = false;
      }
    },

    selectToken(token) {
      // Open cashier mode with this token pre-selected
      evntBus.$emit('open_cashier_mode_with_token', this.posProfile, this.posOpeningShift, token.token_number);
    },

    formatTime(datetime) {
      if (!datetime) return '';
      const date = new Date(datetime);
      const now = new Date();
      const diff = Math.floor((now - date) / 1000 / 60); // minutes
      
      if (diff < 1) return this.__('Just now');
      if (diff < 60) return `${diff}m ago`;
      if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
      return date.toLocaleDateString();
    },

    checkUserRole() {
      const vm = this;
      frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: "Has Role",
          filters: {
            parent: frappe.session.user,
            parenttype: "User"
          },
          fields: ["role"]
        },
        async: false,
        callback: function(r) {
          if (r.message) {
            const roles = r.message.map(row => row.role);
            vm.isCashier = roles.includes("POS Cashier");
          }
        }
      });
    },

    startAutoRefresh() {
      // Refresh every 30 seconds
      this.refreshInterval = setInterval(() => {
        if (this.isCashier && this.posProfile) {
          this.loadPendingTokens();
        }
      }, 30000);
    }
  },

  mounted() {
    this.checkUserRole();

    evntBus.$on('register_pos_profile', (data) => {
      this.posProfile = data.pos_profile;
      this.posOpeningShift = data.pos_opening_shift;
      
      // Only load for cashiers and if token workflow is enabled
      if (this.isCashier && this.posProfile.posa_enable_token_workflow) {
        this.loadPendingTokens();
        this.startAutoRefresh();
      }
    });

    // Refresh when a token is paid
    evntBus.$on('token_paid', () => {
      this.loadPendingTokens();
    });

    // Refresh when token dialog closes
    evntBus.$on('token_dialog_closed', () => {
      this.loadPendingTokens();
    });
  },

  beforeDestroy() {
    evntBus.$off('register_pos_profile');
    evntBus.$off('token_paid');
    evntBus.$off('token_dialog_closed');
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }
};
</script>

<style scoped>
.pending-tokens-sidebar {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 100;
  background: white;
  border-radius: 0 8px 8px 0;
  box-shadow: 2px 0 8px rgba(0,0,0,0.15);
  transition: all 0.3s ease;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.pending-tokens-sidebar:not(.expanded) {
  width: 50px;
}

.pending-tokens-sidebar.expanded {
  width: 280px;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  padding: 12px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
  min-height: 52px;
}

.sidebar-toggle:hover {
  background: #f5f5f5;
}

.toggle-text {
  font-weight: 500;
  font-size: 14px;
}

.sidebar-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #fafafa;
}

.token-list {
  flex: 1;
  overflow-y: auto;
  max-height: calc(80vh - 180px);
}

.token-item {
  padding: 10px 12px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  transition: background 0.2s;
}

.token-item:hover {
  background: #fff8e1;
}

.token-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.token-number {
  font-weight: 600;
  color: #1976d2;
  font-size: 13px;
}

.token-amount {
  font-weight: 700;
  color: #2e7d32;
  font-size: 14px;
}

.token-details {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}

.customer-name {
  font-weight: 500;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.token-time {
  color: #999;
}

.token-associate {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
}

.sidebar-footer {
  padding: 10px 12px;
  background: #f5f5f5;
  border-top: 1px solid #ddd;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
}

.stat-row:last-child {
  margin-bottom: 0;
}

.stat-label {
  color: #666;
}

.stat-value {
  font-weight: 600;
  color: #333;
}
</style>
