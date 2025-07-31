from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice as BaseSalesInvoice
from frappe.utils import flt
from frappe import _
import frappe

class SalesInvoice(BaseSalesInvoice):
    def validate_pos(self):
        if self.is_return:
            invoice_total = self.rounded_total or self.grand_total
            if flt(self.paid_amount) + flt(self.write_off_amount) - abs(flt(invoice_total)) > 1.0 / (
                10.0 ** (self.precision("grand_total") + 1.0)
            ):
                frappe.throw(_("Paid amount + Write Off Amount can not be greater than Grand Total"))
