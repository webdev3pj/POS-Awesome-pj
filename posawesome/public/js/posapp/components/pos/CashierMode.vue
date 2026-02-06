<template>
  <v-dialog v-model="dialog" max-width="900" persistent>
    <v-card>
      <v-card-title class="success white--text">
        <v-icon class="mr-2" color="white">mdi-cash-register</v-icon>
        {{ __('Cashier - Scan Order') }}
        <v-spacer></v-spacer>
        <v-btn icon @click="closeDialog" color="white">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      
      <v-card-text class="pt-4">
        <!-- Large Scan Input - Auto-focus for barcode scanner -->
        <v-row>
          <v-col cols="12">
            <v-text-field
              v-model="searchTerm"
              :label="__('Scan QR Code or Enter Order Number (Token/SO-XXX)')"
              outlined
              autofocus
              large
              prepend-inner-icon="mdi-qrcode-scan"
              append-icon="mdi-magnify"
              @click:append="searchOrder"
              @keyup.enter="searchOrder"
              :loading="loading"
              :error-messages="errorMessage"
              clearable
              ref="searchInput"
              class="scan-input"
              :placeholder="__('Ready to scan...')"
            ></v-text-field>
          </v-col>
        </v-row>
        
        <!-- Token Details Card -->
        <v-card v-if="tokenData" class="mt-2" outlined :class="{'paid-token': tokenData.status === 'Paid'}">
          <v-card-title class="pb-0">
            <v-chip 
              :color="getStatusColor(tokenData.status)" 
              dark
              class="mr-2"
              large
            >
              {{ tokenData.status }}
            </v-chip>
            <span class="text-h4 font-weight-bold">{{ tokenData.token_number }}</span>
            <v-spacer></v-spacer>
            <span class="text-subtitle-1 grey--text">{{ formatDateTime(tokenData.token_datetime) }}</span>
          </v-card-title>
          
          <v-card-text>
            <v-row class="mb-2">
              <v-col cols="6">
                <div class="text-subtitle-2 grey--text">{{ __('Customer') }}</div>
                <div class="text-h5">{{ tokenData.customer_name }}</div>
                <div class="text-body-2 grey--text">{{ tokenData.customer }}</div>
              </v-col>
              <v-col cols="6" class="text-right">
                <div class="text-subtitle-2 grey--text">{{ __('Total Amount') }}</div>
                <div class="text-h3 success--text font-weight-bold">
                  {{ currencySymbol }} {{ formtCurrency(tokenData.total_amount) }}
                </div>
              </v-col>
            </v-row>
            
            <v-divider class="my-3"></v-divider>
            
            <!-- Compact Items Table -->
            <v-simple-table dense>
              <template v-slot:default>
                <thead>
                  <tr>
                    <th class="text-left">{{ __('Item') }}</th>
                    <th class="text-center">{{ __('Qty') }}</th>
                    <th class="text-right">{{ __('Rate') }}</th>
                    <th class="text-right">{{ __('Amount') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in tokenData.items" :key="item.item_code">
                    <td>
                      <strong>{{ item.item_code }}</strong><br>
                      <small class="grey--text">{{ item.item_name }}</small>
                    </td>
                    <td class="text-center">{{ item.qty }}</td>
                    <td class="text-right">{{ formtCurrency(item.rate) }}</td>
                    <td class="text-right font-weight-bold">{{ formtCurrency(item.amount) }}</td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr class="grey lighten-4">
                    <td class="text-right font-weight-bold">{{ __('TOTAL') }}</td>
                    <td class="text-center font-weight-bold">{{ tokenData.total_qty }}</td>
                    <td></td>
                    <td class="text-right font-weight-bold text-h6">{{ formtCurrency(tokenData.total_amount) }}</td>
                  </tr>
                </tfoot>
              </template>
            </v-simple-table>
            
            <!-- Info Footer -->
            <div class="mt-3 text-body-2 grey--text">
              <v-icon small>mdi-account</v-icon> {{ __('Sales Associate') }}: {{ tokenData.sales_associate_name || tokenData.sales_associate }}
              <span v-if="tokenData.sales_person" class="ml-4">
                <v-icon small>mdi-account-tie</v-icon> {{ __('Sales Person') }}: {{ tokenData.sales_person_name || tokenData.sales_person }}
              </span>
              <span v-if="tokenData.linked_invoice" class="ml-4">
                <v-icon small>mdi-receipt</v-icon> {{ __('Invoice') }}: 
                <a :href="'/app/sales-invoice/' + tokenData.linked_invoice" target="_blank">
                  {{ tokenData.linked_invoice }}
                </a>
              </span>
            </div>
          </v-card-text>
          
          <!-- Action Buttons - Only for Pending tokens -->
          <v-card-actions v-if="tokenData.status === 'Pending'" class="pa-4 grey lighten-4">
            <v-btn
              color="error"
              text
              @click="cancelToken"
              :loading="cancelLoading"
            >
              <v-icon left>mdi-cancel</v-icon>
              {{ __('Cancel') }}
            </v-btn>
            <v-spacer></v-spacer>
            <v-btn
              color="success"
              x-large
              @click="loadAndPay"
              :loading="processLoading"
              class="px-8"
            >
              <v-icon left large>mdi-cash-check</v-icon>
              {{ __('COLLECT PAYMENT') }}
            </v-btn>
          </v-card-actions>
          
          <!-- Tip for modifying order -->
          <v-alert
            v-if="tokenData && tokenData.status === 'Pending'"
            type="info"
            dense
            text
            class="mx-4 mb-4"
          >
            <v-icon small class="mr-1">mdi-information</v-icon>
            {{ __('Need to modify the order? Click "COLLECT PAYMENT" to load items, then add/remove items before paying.') }}
          </v-alert>
          
          <!-- Already Paid Message -->
          <v-card-actions v-else-if="tokenData.status === 'Paid'" class="pa-4 green lighten-4">
            <v-icon color="success" class="mr-2">mdi-check-circle</v-icon>
            <span class="success--text font-weight-bold">{{ __('This token has already been paid') }}</span>
            <v-spacer></v-spacer>
            <v-btn color="primary" text @click="clearAndScanNext">
              {{ __('Scan Next') }}
            </v-btn>
          </v-card-actions>
        </v-card>
        
        <!-- Pending Tokens List (when no token selected) -->
        <v-card v-if="!tokenData && pendingTokens.length" class="mt-4" outlined>
          <v-card-title class="pb-2">
            <v-icon class="mr-2" color="warning">mdi-clock-outline</v-icon>
            {{ __('Pending Tokens') }} ({{ pendingTokens.length }})
            <v-spacer></v-spacer>
            <v-btn icon small @click="loadPendingTokens">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </v-card-title>
          <v-data-table
            :headers="tokenHeaders"
            :items="pendingTokens"
            :items-per-page="10"
            dense
            @click:row="selectToken"
            class="cursor-pointer"
          >
            <template v-slot:item.token_datetime="{ item }">
              {{ formatDateTime(item.token_datetime) }}
            </template>
            <template v-slot:item.total_amount="{ item }">
              <strong>{{ currencySymbol }} {{ formtCurrency(item.total_amount) }}</strong>
            </template>
            <template v-slot:item.token_number="{ item }">
              <strong class="primary--text">{{ item.token_number }}</strong>
            </template>
            <template v-slot:item.sales_associate_name="{ item }">
              {{ item.sales_associate_name || item.sales_associate }}
            </template>
          </v-data-table>
        </v-card>
        
        <!-- Empty State -->
        <v-card v-if="!tokenData && !pendingTokens.length && searched" class="mt-4 text-center pa-8" outlined>
          <v-icon size="64" color="grey lighten-1">mdi-ticket-outline</v-icon>
          <div class="text-h6 grey--text mt-4">{{ __('No pending tokens') }}</div>
          <div class="text-body-2 grey--text">{{ __('Scan a QR code to retrieve order') }}</div>
        </v-card>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import { evntBus } from '../../bus';
import format from '../../format';

export default {
  name: 'CashierMode',
  mixins: [format],
  
  data() {
    return {
      dialog: false,
      searchTerm: '',
      loading: false,
      cancelLoading: false,
      processLoading: false,
      errorMessage: '',
      tokenData: null,
      pendingTokens: [],
      searched: false,
      currencySymbol: '',
      posProfile: null,
      posOpeningShift: null,
      tokenHeaders: [
        { text: this.__('Token'), value: 'token_number' },
        { text: this.__('Customer'), value: 'customer_name' },
        { text: this.__('Amount'), value: 'total_amount', align: 'right' },
        { text: this.__('Time'), value: 'token_datetime' },
        { text: this.__('Sales Associate'), value: 'sales_associate_name' }
      ]
    };
  },
  
  methods: {
    __: frappe._,
    
    openDialog(posProfile, posOpeningShift) {
      this.posProfile = posProfile;
      this.posOpeningShift = posOpeningShift;
      this.currencySymbol = posProfile?.currency || '';
      this.dialog = true;
      this.tokenData = null;
      this.searchTerm = '';
      this.errorMessage = '';
      this.loadPendingTokens();
      this.$nextTick(() => {
        this.$refs.searchInput?.focus();
      });
    },
    
    closeDialog() {
      this.dialog = false;
      this.tokenData = null;
      this.searchTerm = '';
      this.pendingTokens = [];
      this.searched = false;
    },
    
    async loadPendingTokens() {
      try {
        const response = await frappe.call({
          method: 'posawesome.posawesome.api.token.get_pending_tokens',
          args: {
            pos_profile: this.posProfile?.name,
            pos_opening_shift: this.posOpeningShift?.name
          }
        });
        this.pendingTokens = response.message || [];
        this.searched = true;
      } catch (error) {
        console.error('Error loading pending tokens:', error);
      }
    },
    
    async searchToken() {
      if (!this.searchTerm) {
        this.loadPendingTokens();
        return;
      }
      
      this.loading = true;
      this.errorMessage = '';
      this.tokenData = null;
      
      try {
        const response = await frappe.call({
          method: 'posawesome.posawesome.api.token.get_token',
          args: {
            token_identifier: this.searchTerm
          }
        });
        
        if (response.message) {
          this.tokenData = response.message;
          this.searchTerm = '';
        }
      } catch (error) {
        this.errorMessage = error.message || this.__('Token not found');
      } finally {
        this.loading = false;
      }
    },
    
    async searchOrder() {
      // NEW: Search for both Sales Orders and Tokens
      if (!this.searchTerm) {
        this.loadPendingTokens();
        return;
      }
      
      this.loading = true;
      this.errorMessage = '';
      this.tokenData = null;
      
      try {
        const searchTerm = this.searchTerm.trim();
        
        // Check if it's a Sales Order (starts with "SO-")
        if (searchTerm.startsWith('SO-')) {
          // Retrieve Sales Order and load to POS
          const response = await frappe.call({
            method: 'posawesome.posawesome.api.sales_order_token.get_sales_order_for_cashier',
            args: {
              order_name: searchTerm
            }
          });
          
          if (response.message) {
            // Load Sales Order into POS cart
            await this.loadSalesOrderToPOS(response.message);
            this.closeDialog();
          }
        } else {
          // Try to find as token (backward compatibility)
          const response = await frappe.call({
            method: 'posawesome.posawesome.api.token.get_token',
            args: {
              token_identifier: searchTerm
            }
          });
          
          if (response.message) {
            this.tokenData = response.message;
            this.searchTerm = '';
          }
        }
      } catch (error) {
        this.errorMessage = error.message || this.__('Order/Token not found');
      } finally {
        this.loading = false;
      }
    },
    
    async loadSalesOrderToPOS(salesOrder) {
      // Load Sales Order items into POS cart
      try {
        // Emit event to load order
        evntBus.$emit('load_sales_order', salesOrder);
        
        evntBus.$emit('show_mesage', {
          text: this.__('Order {0} loaded successfully', [salesOrder.name]),
          color: 'success'
        });
      } catch (error) {
        evntBus.$emit('show_mesage', {
          text: error.message || this.__('Error loading order'),
          color: 'error'
        });
      }
    },
    
    selectToken(token) {
      this.searchTerm = token.token_number;
      this.searchToken();
    },
    
    getStatusColor(status) {
      const colors = {
        'Pending': 'warning',
        'Paid': 'success',
        'Cancelled': 'error'
      };
      return colors[status] || 'grey';
    },
    
    formatDateTime(datetime) {
      if (!datetime) return '';
      const date = new Date(datetime);
      return date.toLocaleString();
    },
    
    async cancelToken() {
      if (!confirm(this.__('Are you sure you want to cancel this token?'))) {
        return;
      }
      
      this.cancelLoading = true;
      
      try {
        await frappe.call({
          method: 'posawesome.posawesome.api.token.cancel_token',
          args: {
            token_name: this.tokenData.name
          }
        });
        
        evntBus.$emit('show_mesage', {
          text: this.__('Token cancelled successfully'),
          color: 'success'
        });
        
        this.tokenData = null;
        this.loadPendingTokens();
      } catch (error) {
        evntBus.$emit('show_mesage', {
          text: error.message || this.__('Error cancelling token'),
          color: 'error'
        });
      } finally {
        this.cancelLoading = false;
      }
    },
    
    loadAndPay() {
      // Load token and immediately open payment dialog
      this.processLoading = true;
      evntBus.$emit('load_token_for_payment', this.tokenData);
      // Small delay to ensure items are loaded before opening payment
      setTimeout(() => {
        evntBus.$emit('show_payment', 'true');
        this.processLoading = false;
        this.closeDialog();
      }, 300);
    },
    
    clearAndScanNext() {
      this.tokenData = null;
      this.searchTerm = '';
      this.$nextTick(() => {
        this.$refs.searchInput?.focus();
      });
    },
    
    openDialogWithToken(posProfile, posOpeningShift, tokenNumber) {
      // Open dialog and pre-select a token (called from sidebar)
      this.openDialog(posProfile, posOpeningShift);
      this.$nextTick(() => {
        this.searchTerm = tokenNumber;
        this.searchToken();
      });
    }
  },
  
  mounted() {
    evntBus.$on('open_cashier_mode', (posProfile, posOpeningShift) => {
      this.openDialog(posProfile, posOpeningShift);
    });
    
    evntBus.$on('open_cashier_mode_with_token', (posProfile, posOpeningShift, tokenNumber) => {
      this.openDialogWithToken(posProfile, posOpeningShift, tokenNumber);
    });
  },
  
  beforeDestroy() {
    evntBus.$off('open_cashier_mode');
    evntBus.$off('open_cashier_mode_with_token');
  }
};
</script>

<style scoped>
.cursor-pointer tbody tr {
  cursor: pointer;
}
.cursor-pointer tbody tr:hover {
  background-color: #f5f5f5;
}
.scan-input input {
  font-size: 1.25rem !important;
}
.paid-token {
  border-color: #4caf50 !important;
  border-width: 2px !important;
}
</style>
