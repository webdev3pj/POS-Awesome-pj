<template>
  <v-dialog v-model="dialog" max-width="600px" persistent>
    <v-card>
      <v-card-title class="purple white--text">
        <v-icon left color="white">mdi-receipt-text</v-icon>
        <span class="headline">{{ __('Order Created Successfully') }}</span>
        <v-spacer></v-spacer>
        <v-btn icon dark @click="close_dialog">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      
      <v-card-text class="pa-6" style="text-align: center;">
        <div v-if="orderData">
          <!-- QR Code -->
          <div class="qr-code-container my-4">
            <img 
              v-if="orderData.qr_code" 
              :src="orderData.qr_code" 
              style="width: 250px; height: 250px; border: 2px solid #9c27b0;"
              alt="Order QR Code"
            >
          </div>
          
          <!-- Order Details -->
          <v-card outlined class="my-4 pa-4">
            <h2 class="purple--text mb-3">{{ orderData.order_name }}</h2>
            
            <v-divider class="my-3"></v-divider>
            
            <div class="text-left">
              <v-row dense>
                <v-col cols="6" class="text-right font-weight-bold">Order Number:</v-col>
                <v-col cols="6">{{ orderData.order_name }}</v-col>
              </v-row>
              
              <v-row dense>
                <v-col cols="6" class="text-right font-weight-bold">Total Amount:</v-col>
                <v-col cols="6">
                  <span class="text-h6 success--text">
                    {{ currencySymbol(currency) }} {{ formtCurrency(orderData.grand_total) }}
                  </span>
                </v-col>
              </v-row>
              
              <v-row dense>
                <v-col cols="6" class="text-right font-weight-bold">Sales Associate:</v-col>
                <v-col cols="6">{{ orderData.sales_associate }}</v-col>
              </v-row>
              
              <v-row v-if="orderData.commission_applied" dense>
                <v-col cols="6" class="text-right font-weight-bold">Commission:</v-col>
                <v-col cols="6">
                  {{ orderData.commission_rate }}% 
                  ({{ currencySymbol(currency) }} {{ formtCurrency(orderData.commission_amount) }})
                </v-col>
              </v-row>
            </div>
          </v-card>
          
          <!-- Instructions -->
          <v-alert type="info" outlined dense class="my-4">
            <strong>Next Steps:</strong><br>
            Customer should take this order to the cashier for payment.
          </v-alert>
        </div>
      </v-card-text>
      
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" @click="print_order" large>
          <v-icon left>mdi-printer</v-icon>
          {{ __('Print Order') }}
        </v-btn>
        <v-btn color="success" @click="close_dialog" large>
          <v-icon left>mdi-check</v-icon>
          {{ __('Done') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { evntBus } from '../../bus';
import format from '../../format';

export default {
  mixins: [format],
  data: () => ({
    dialog: false,
    orderData: null,
    currency: 'USD'
  }),
  
  mounted() {
    evntBus.$on('open_order_dialog', (data, currency) => {
      this.orderData = data;
      this.currency = currency || 'USD';
      this.dialog = true;
    });
  },
  
  methods: {
    close_dialog() {
      this.dialog = false;
      this.orderData = null;
    },
    
    print_order() {
      if (!this.orderData) return;
      
      // Open Sales Order print view
      const print_url = `/app/sales-order/${this.orderData.order_name}`;
      window.open(print_url, '_blank');
    }
  }
};
</script>

<style scoped>
.qr-code-container {
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
