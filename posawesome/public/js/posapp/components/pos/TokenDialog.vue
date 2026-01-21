<template>
  <v-dialog v-model="dialog" max-width="500" persistent>
    <v-card>
      <v-card-title class="primary white--text">
        <v-icon class="mr-2" color="white">mdi-ticket-confirmation</v-icon>
        {{ __('Token Generated') }}
      </v-card-title>
      
      <v-card-text class="text-center py-6">
        <!-- Token Number -->
        <div class="token-number mb-4">
          <div class="text-subtitle-1 grey--text mb-1">{{ __('Token Number') }}</div>
          <div class="text-h3 primary--text font-weight-bold">{{ tokenData.token_number }}</div>
        </div>
        
        <!-- QR Code -->
        <div class="qr-code-container mb-4" v-if="tokenData.qr_code">
          <img 
            :src="'data:image/png;base64,' + tokenData.qr_code" 
            alt="Token QR Code"
            class="qr-code-img"
          />
        </div>
        
        <!-- Customer Info -->
        <div class="customer-info mb-4">
          <div class="text-subtitle-1 grey--text mb-1">{{ __('Customer') }}</div>
          <div class="text-h6">{{ tokenData.customer_name }}</div>
        </div>
        
        <!-- Amount -->
        <div class="amount-info mb-4">
          <div class="text-subtitle-1 grey--text mb-1">{{ __('Total Amount') }}</div>
          <div class="text-h5 success--text font-weight-bold">
            {{ currencySymbol }} {{ formtCurrency(tokenData.total_amount) }}
          </div>
        </div>
        
        <!-- Sales Associate -->
        <div class="sales-info mb-2" v-if="tokenData.sales_associate_name">
          <div class="text-caption grey--text">
            <v-icon small>mdi-account</v-icon>
            {{ __('Sales Associate') }}: {{ tokenData.sales_associate_name }}
          </div>
        </div>
        
        <!-- Sales Person (Commission) -->
        <div class="sales-person-info mb-2" v-if="tokenData.sales_person_name">
          <div class="text-caption grey--text">
            <v-icon small>mdi-account-tie</v-icon>
            {{ __('Sales Person') }}: {{ tokenData.sales_person_name }}
          </div>
        </div>
        
        <!-- DateTime -->
        <div class="datetime-info">
          <div class="text-subtitle-2 grey--text">
            {{ formatDateTime(tokenData.token_datetime) }}
          </div>
        </div>
        
        <!-- Items Summary -->
        <v-expansion-panels flat class="mt-4" v-if="tokenData.items && tokenData.items.length">
          <v-expansion-panel>
            <v-expansion-panel-header>
              {{ __('Items') }} ({{ tokenData.total_qty }})
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-simple-table dense>
                <template v-slot:default>
                  <thead>
                    <tr>
                      <th class="text-left">{{ __('Item') }}</th>
                      <th class="text-center">{{ __('Qty') }}</th>
                      <th class="text-right">{{ __('Amount') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in tokenData.items" :key="item.item_code">
                      <td>{{ item.item_name }}</td>
                      <td class="text-center">{{ item.qty }}</td>
                      <td class="text-right">{{ formtCurrency(item.amount) }}</td>
                    </tr>
                  </tbody>
                </template>
              </v-simple-table>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
      
      <v-divider></v-divider>
      
      <v-card-actions class="pa-4">
        <v-btn
          color="primary"
          outlined
          @click="printToken"
          class="mr-2"
        >
          <v-icon left>mdi-printer</v-icon>
          {{ __('Print') }}
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn
          color="success"
          @click="closeAndContinue"
        >
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
  name: 'TokenDialog',
  mixins: [format],
  
  data() {
    return {
      dialog: false,
      tokenData: {
        name: '',
        token_number: '',
        customer_name: '',
        total_amount: 0,
        total_qty: 0,
        token_datetime: '',
        sales_associate_name: '',
        sales_person_name: '',
        qr_code: '',
        items: []
      },
      currencySymbol: ''
    };
  },
  
  methods: {
    openDialog(data, currency) {
      this.tokenData = data;
      this.currencySymbol = currency || '';
      this.dialog = true;
    },
    
    closeAndContinue() {
      this.dialog = false;
      evntBus.$emit('token_dialog_closed');
    },
    
    formatDateTime(datetime) {
      if (!datetime) return '';
      const date = new Date(datetime);
      return date.toLocaleString();
    },
    
    printToken() {
      const printWindow = window.open('', '', 'height=600,width=400');
      const itemsHtml = this.tokenData.items.map(item => `
        <tr>
          <td style="padding: 4px 8px; border-bottom: 1px solid #eee;">${item.item_name}</td>
          <td style="padding: 4px 8px; border-bottom: 1px solid #eee; text-align: center;">${item.qty}</td>
          <td style="padding: 4px 8px; border-bottom: 1px solid #eee; text-align: right;">${this.formtCurrency(item.amount)}</td>
        </tr>
      `).join('');
      
      const salesAssociateInfo = this.tokenData.sales_associate_name 
        ? `<p><strong>Served by:</strong> ${this.tokenData.sales_associate_name}</p>` 
        : '';
      
      printWindow.document.write(`
        <html>
          <head>
            <title>Token Receipt</title>
            <style>
              @media print {
                body {
                  width: 80mm;
                  margin: 0 auto;
                  font-family: 'Courier New', monospace;
                  font-size: 12px;
                }
              }
              body {
                width: 80mm;
                margin: 0 auto;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 10px;
              }
              .center { text-align: center; }
              .token-number {
                font-size: 32px;
                font-weight: bold;
                margin: 15px 0;
                padding: 10px;
                border: 2px dashed #333;
              }
              .qr-code { margin: 15px 0; }
              .qr-code img { width: 150px; height: 150px; }
              .divider {
                border-top: 1px dashed #333;
                margin: 10px 0;
              }
              table {
                width: 100%;
                border-collapse: collapse;
                font-size: 11px;
              }
              th {
                border-bottom: 1px solid #333;
                padding: 4px 8px;
                text-align: left;
              }
              .total {
                font-size: 16px;
                font-weight: bold;
                margin: 10px 0;
              }
              .footer {
                margin-top: 20px;
                padding-top: 10px;
                border-top: 1px dashed #333;
                font-size: 11px;
              }
            </style>
          </head>
          <body>
            <div class="center">
              <h3>TOKEN RECEIPT</h3>
              <div class="token-number">${this.tokenData.token_number}</div>
              <div class="qr-code">
                <img src="data:image/png;base64,${this.tokenData.qr_code}" alt="QR Code" />
              </div>
            </div>
            
            <div class="divider"></div>
            
            <p><strong>Customer:</strong> ${this.tokenData.customer_name}</p>
            <p><strong>Date/Time:</strong> ${this.formatDateTime(this.tokenData.token_datetime)}</p>
            ${salesAssociateInfo}
            
            <div class="divider"></div>
            
            <table>
              <thead>
                <tr>
                  <th>Item</th>
                  <th style="text-align: center;">Qty</th>
                  <th style="text-align: right;">Amount</th>
                </tr>
              </thead>
              <tbody>
                ${itemsHtml}
              </tbody>
            </table>
            
            <div class="divider"></div>
            
            <div class="center total">
              Total: ${this.currencySymbol} ${this.formtCurrency(this.tokenData.total_amount)}
            </div>
            
            <div class="footer center">
              <p>Please proceed to cashier</p>
              <p>with this receipt</p>
            </div>
          </body>
        </html>
      `);
      
      printWindow.document.close();
      printWindow.focus();
      setTimeout(() => {
        printWindow.print();
        printWindow.close();
      }, 250);
    }
  },
  
  mounted() {
    evntBus.$on('open_token_dialog', (data, currency) => {
      this.openDialog(data, currency);
    });
  },
  
  beforeDestroy() {
    evntBus.$off('open_token_dialog');
  }
};
</script>

<style scoped>
.qr-code-img {
  width: 200px;
  height: 200px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 8px;
  background: white;
}

.token-number {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
}
</style>
