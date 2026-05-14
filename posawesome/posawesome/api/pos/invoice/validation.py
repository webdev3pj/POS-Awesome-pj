import frappe
from frappe import _


def validate_shift(doc):
    if not (doc.posa_pos_opening_shift and doc.pos_profile and doc.is_pos):
        return

    shift = frappe.get_cached_doc("POS Opening Shift", doc.posa_pos_opening_shift)
    if shift.status != "Open":
        frappe.throw(_("POS Shift {0} is not open").format(shift.name))
    if shift.pos_profile != doc.pos_profile:
        frappe.throw(
            _("POS Opening Shift {0} is not for the same POS Profile").format(
                shift.name
            )
        )
    if shift.company != doc.company:
        frappe.throw(
            _("POS Opening Shift {0} is not for the same company").format(shift.name)
        )
