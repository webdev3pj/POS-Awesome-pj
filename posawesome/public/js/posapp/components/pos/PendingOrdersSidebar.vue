<template>
  <div class="pending-orders-sidebar" :class="{ 'expanded': isExpanded }">
    <!-- Collapsed State - Just shows count badge -->
    <div 
      class="sidebar-toggle"
      @click="toggleSidebar"
      :title="isExpanded ? __('Collapse') : __('Pending Orders')"
    >
      <v-badge
        :content="pendingCount"
        :value="pendingCount > 0"
        color="purple"
        overlap
        offset-x="10"
        offset-y="10"
      >
        <v-icon :color="pendingCount > 0 ? 'purple' : 'grey'" size="28">
          mdi-receipt-text-outline
        </v-icon>
      </v-badge>
      <span v-if="isExpanded" class="toggle-text ml-2">{{ __('Pending') }}</span>
      <v-icon v-if="isExpanded" small class="ml-auto">mdi-chevron-left</v-icon>
    </div>

    <!-- Expanded State - Shows order list -->
    <div v-if="isExpanded" class="sidebar-content">
      <div class="sidebar-header">
        <span class="text-subtitle-2 font-weight-bold">
          {{ __('Pending Orders') }}
        </span>
        <v-chip small color="purple" dark class="ml-2">{{ pendingCount }}</v-chip>
        <v-btn icon x-small class="ml-auto" @click="loadPendingOrders" :loading="loading">
          <v-icon small>mdi-refresh</v-icon>
        </v-btn>
      </div>

      <v-divider></v-divider>

      <!-- Order List -->
      <div class="order-list" v-if="pendingOrders.length">
        <div 
          v-for="order in pendingOrders" 
          :key="order.name"
          class="order-item"
          @click="selectOrder(order)"
        >
          <div class="order-header">
            <span class="order-number">{{ order.name }}</span>
            <span class="order-amount">{{ formtCurrency(order.grand_total) }}</span>
          </div>
          <div class="order-details">
            <span class="customer-name">{{ order.customer_name }}</span>
            <span class="order-date">{{ formatDate(order.transaction_date) }}</span>
          </div>
          <div class="order-status">
            <v-chip x-small :color="getStatusColor(order.status)" dark>
              {{ order.status }}
            </v-chip>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="empty-state">
        <v-icon size="40" color="grey lighten-1">mdi-receipt-text-outline</v-icon>
        <div class="text-caption grey--text mt-2">{{ __('No pending orders') }}</div>
      </div>

      <!-- Quick Stats -->
      <div class="sidebar-footer" v-if="pendingOrders.length">
        <div class="stat-row">
          <span class="stat-label">{{ __('Total Value') }}:</span>
          <span class="stat-value">{{ formtCurrency(totalPendingAmount) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { evntBus } from '../../bus';
import format from '../../format';

export default {
  name: 'PendingOrdersSidebar',
  mixins: [format],

  data() {
    return {
      isExpanded: false,
      loading: false,
      pendingOrders: [],
      posProfile: null,
      refreshInterval: null,
      isSalesAssociate: false
    };
  },

  computed: {
    pendingCount() {
      return this.pendingOrders.length;
    },

    totalPendingAmount() {
      return this.pendingOrders.reduce((sum, order) => sum + parseFloat(order.grand_total || 0), 0);
    }
  },

  mounted() {
    // Listen for profile updates
    evntBus.$on('register_pos_profile', (data) => {
      this.posProfile = data.pos_profile;
      this.checkUserRole();
      if (this.isSalesAssociate) {
        this.loadPendingOrders();
        this.startAutoRefresh();
      }
    });

    // Listen for new orders created
    evntBus.$on('sales_order_created', () => {
      this.loadPendingOrders();
    });

    // Check role on mount
    this.checkUserRole();
  },

  beforeDestroy() {
    this.stopAutoRefresh();
    evntBus.$off('register_pos_profile');
    evntBus.$off('sales_order_created');
  },

  methods: {
    checkUserRole() {
      // Check if user has Sales Associate role
      frappe.call({
        method: 'posawesome.posawesome.api.posapp.get_current_user_roles',
        callback: (r) => {
          if (r.message) {
            this.isSalesAssociate = r.message.includes('POS Sales Associate');
          }
        }
      });
    },

    toggleSidebar() {
      this.isExpanded = !this.isExpanded;
      if (this.isExpanded && this.isSalesAssociate) {
        this.loadPendingOrders();
      }
    },

    async loadPendingOrders() {
      if (!this.isSalesAssociate) return;

      this.loading = true;
      try {
        const response = await frappe.call({
          method: 'posawesome.posawesome.api.sales_order_token.get_pending_orders',
          args: {
            sales_associate: frappe.session.user
          }
        });

        if (response.message) {
          this.pendingOrders = response.message;
        }
      } catch (error) {
        console.error('Error loading pending orders:', error);
      } finally {
        this.loading = false;
      }
    },

    selectOrder(order) {
      // Emit event to load order (for future use if Sales Associate can view their orders)
      evntBus.$emit('view_pending_order', order);
      
      // Show message
      frappe.msgprint({
        title: __('Order Details'),
        message: __('Order {0} for {1}<br>Amount: {2}<br>Status: {3}', 
          [order.name, order.customer_name, this.formtCurrency(order.grand_total), order.status]),
        indicator: 'blue'
      });
    },

    formatDate(dateStr) {
      if (!dateStr) return '';
      const date = new Date(dateStr);
      return date.toLocaleDateString();
    },

    getStatusColor(status) {
      const colors = {
        'To Deliver and Bill': 'purple',
        'To Bill': 'orange',
        'To Deliver': 'blue',
        'Completed': 'green',
        'Cancelled': 'red'
      };
      return colors[status] || 'grey';
    },

    startAutoRefresh() {
      // Refresh every 30 seconds
      this.refreshInterval = setInterval(() => {
        if (this.isExpanded && this.isSalesAssociate) {
          this.loadPendingOrders();
        }
      }, 30000);
    },

    stopAutoRefresh() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
      }
    }
  }
};
</script>

<style scoped>
.pending-orders-sidebar {
  position: fixed;
  right: 0;
  top: 100px;
  width: 60px;
  background: white;
  border: 1px solid #e0e0e0;
  border-right: none;
  border-radius: 8px 0 0 8px;
  box-shadow: -2px 2px 8px rgba(0,0,0,0.1);
  transition: width 0.3s ease;
  z-index: 999;
  max-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.pending-orders-sidebar.expanded {
  width: 320px;
}

.sidebar-toggle {
  padding: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  background: white;
  border-radius: 8px 0 0 8px;
  transition: background-color 0.2s;
}

.sidebar-toggle:hover {
  background-color: #f5f5f5;
}

.toggle-text {
  font-size: 14px;
  font-weight: 500;
  color: #424242;
}

.sidebar-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 12px;
  display: flex;
  align-items: center;
  background-color: #f5f5f5;
}

.order-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.order-item {
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
}

.order-item:hover {
  background-color: #f9f3ff;
  border-color: #9c27b0;
  transform: translateX(-2px);
}

.order-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.order-number {
  font-size: 13px;
  font-weight: 600;
  color: #9c27b0;
}

.order-amount {
  font-size: 13px;
  font-weight: 700;
  color: #2e7d32;
}

.order-details {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #666;
  margin-bottom: 4px;
}

.customer-name {
  font-weight: 500;
}

.order-status {
  margin-top: 4px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid #e0e0e0;
  background-color: #f9f9f9;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
}

.stat-label {
  color: #666;
}

.stat-value {
  font-weight: 600;
  color: #424242;
}
</style>
