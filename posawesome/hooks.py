# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "posawesome"
app_title = "POS Awesome"
app_publisher = "Youssef Restom"
app_description = "POS Awesome"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "youssef@totrox.com"
app_license = "GPLv3"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/posawesome/css/posawesome.css"
# app_include_js = "/assets/posawesome/js/posawesome.js"
app_include_js = [
    "/assets/posawesome/node_modules/vuetify/dist/vuetify.js",
    "posawesome.bundle.js",
    "/assets/posawesome/js/xlsx.full.min.js",
]


# include js, css files in header of web template
# web_include_css = "/assets/posawesome/css/posawesome.css"
# web_include_js = "/assets/posawesome/js/posawesome.js"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}


# include js in doctype views
doctype_js = {
    "POS Profile": "posawesome/api/pos_profile.js",
    "Sales Invoice": "posawesome/api/invoice.js",
    "Company": "posawesome/api/company.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "posawesome.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "posawesome.install.before_install"
# after_install = "posawesome.install.after_install"
# before_uninstall = "posawesome.uninstall.before_uninstall"
after_uninstall = "posawesome.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "posawesome.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

override_doctype_class = {
    "Sales Invoice": "posawesome.overrides.custom_sales_invoice.SalesInvoice"
}
doc_events = {
    "Sales Invoice": {
        "before_save": "posawesome.overrides.selling_commission.run_all_commissions",
        "validate": "posawesome.posawesome.api.invoice.validate",
        "before_submit": "posawesome.posawesome.api.invoice.before_submit",
        "before_cancel": "posawesome.posawesome.api.invoice.before_cancel",
    },
    "Customer": {
        "validate": "posawesome.posawesome.api.customer.validate",
        "after_insert": "posawesome.posawesome.api.customer.after_insert",
    },
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"posawesome.tasks.all"
# 	],
# 	"daily": [
# 		"posawesome.tasks.daily"
# 	],
# 	"hourly": [
# 		"posawesome.tasks.hourly"
# 	],
# 	"weekly": [
# 		"posawesome.tasks.weekly"
# 	]
# 	"monthly": [
# 		"posawesome.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "posawesome.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "posawesome.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "posawesome.task.get_dashboard_data"
# }

# override_doctype_class = {
# "doctype": "method",
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                (
                    "Item Barcode-posa_uom",
                    "Sales Order Item-posa_notes",
                    "Sales Invoice Item-posa_notes",
                    "Sales Invoice Item-posa_row_id",
                    "Sales Order Item-posa_row_id",
                    "Sales Invoice Item-posa_delivery_date",
                    "Batch-posa_batch_price",
                    "Sales Invoice-posa_pos_opening_shift",
                    "Address-posa_delivery_charges",
                    "Sales Invoice-posa_is_printed",
                    "Sales Invoice-stamped",
                    "POS Profile-posa_pos_awesome_settings",
                    "POS Profile-posa_cash_mode_of_payment",
                    "Customer-posa_discount",
                    "POS Profile-posa_allow_delete",
                    "POS Profile-posa_allow_user_to_edit_rate",
                    "POS Profile-posa_allow_user_to_edit_additional_discount",
                    "POS Profile-posa_use_percentage_discount",
                    "POS Profile-posa_max_discount_allowed",
                    "POS Profile-posa_scale_barcode_start",
                    "POS Profile-posa_allow_change_posting_date",
                    "POS Profile-posa_default_card_view",
                    "POS Profile-posa_default_sales_order",
                    "POS Profile-posa_col_1",
                    "POS Profile-posa_allow_user_to_edit_item_discount",
                    "POS Profile-posa_display_items_in_stock",
                    "POS Profile-posa_allow_partial_payment",
                    "POS Profile-posa_allow_credit_sale",
                    "POS Profile-posa_allow_return",
                    "POS Profile-posa_apply_customer_discount",
                    "Company-posa_referral_section",
                    "POS Profile-use_cashback",
                    "Company-posa_auto_referral",
                    "POS Profile-use_customer_credit",
                    "Company-posa_column_break_22",
                    "POS Profile-posa_hide_closing_shift",
                    "Sales Order-posa_additional_notes_section",
                    "Company-posa_customer_offer",
                    "POS Profile-posa_auto_set_batch",
                    "Sales Order-posa_notes",
                    "Company-posa_primary_offer",
                    "POS Profile-posa_display_item_code",
                    "Company-posa_referral_campaign",
                    "POS Profile-posa_allow_zero_rated_items",
                    "POS Profile-hide_expected_amount",
                    "POS Profile-posa_column_break_112",
                    "POS Profile-posa_allow_sales_order",
                    "POS Profile-posa_show_template_items",
                    "Sales Invoice Item-posa_offers",
                    "POS Profile-posa_hide_variants_items",
                    "Sales Invoice Item-posa_offer_applied",
                    "POS Profile-posa_fetch_coupon",
                    "Sales Invoice Item-posa_is_offer",
                    "Customer-posa_birthday",
                    "POS Profile-posa_allow_customer_purchase_order",
                    "Sales Invoice Item-posa_is_replace",
                    "Customer-posa_referral_section",
                    "POS Profile-posa_allow_print_last_invoice",
                    "Customer-posa_referral_code",
                    "POS Profile-posa_display_additional_notes",
                    "Customer-posa_referral_company",
                    "POS Profile-posa_allow_write_off_change",
                    "POS Profile-posa_new_line",
                    "POS Profile-posa_input_qty",
                    "POS Profile-posa_allow_print_draft_invoices",
                    "POS Profile-posa_use_delivery_charges",
                    "POS Profile-posa_auto_set_delivery_charges",
                    "POS Profile-posa_allow_duplicate_customer_names",
                    "POS Profile-pos_awesome_payments",
                    "POS Profile-posa_use_pos_awesome_payments",
                    "Sales Invoice-posa_delivery_charges",
                    "POS Profile-column_break_uolvm",
                    "Sales Invoice-posa_delivery_charges_rate",
                    "POS Profile-posa_allow_make_new_payments",
                    "POS Profile-posa_allow_reconcile_payments",
                    "POS Profile-posa_allow_mpesa_reconcile_payments",
                    "POS Profile-posa_pos_awesome_advance_settings",
                    "POS Profile-posa_allow_submissions_in_background_job",
                    "POS Profile-posa_search_serial_no",
                    "POS Profile-posa_search_batch_no",
                    "POS Profile-posa_tax_inclusive",
                    "POS Profile-column_break_dqsba",
                    "POS Profile-posa_local_storage",
                    "POS Profile-posa_use_server_cache",
                    "POS Profile-posa_server_cache_duration",
                    "POS Profile-column_break_anyol",
                    "POS Profile-pose_use_limit_search",
                    "POS Profile-posa_search_limit",
                    "POS Profile-custom_allow_select_sales_order",
                    "Sales Order-posa_offers",
                    "Sales Order-posa_coupons",
                    "Sales Invoice-posa_offers",
                    "Sales Invoice-posa_coupons",
                    "Sales Invoice-posa_additional_notes_section",
                    "Sales Invoice-posa_notes",
                    "Sales Invoice-posa_column_break_111",
                    "Sales Invoice-posa_delivery_date",
                    "POS Profile-custom_sales_partner_grand_total_limit",
                    "POS Profile-custom_sales_person_grand_total_limit",
                    "POS Profile-custom_section_break_zlymw",
                    "POS Profile-custom_commission_enabled",
                    "POS Profile-custom_commission_request",
                    "POS Profile-custom_column_break_8gvoy",
                    "POS Profile-custom_discount_enabled",
                    "POS Profile-custom_discount_request",
                    "POS Profile-naming_series",
                    "POS Profile-posa_quotation_naming_series",
                    "Item-custom_max_commission_rate",
                    "Item-custom_sales_person_max_commission_rate",
                    "Sales Invoice Item-custom_max_commission_rate",
                    "Sales Invoice Item-custom_sales_person_max_commission_rate",
                    "Sales Invoice-custom_commission_breakdown",
                    "Sales Invoice-custom_commission_paid",
                    "Sales Invoice-custom_partner_commission_paid",
                    "Sales Invoice-custom_sales_person_commission_breakdown",
                    "Sales Invoice-custom_section_break_hpnsx",
                ),
            ]
        ],
    },
    {
        "doctype": "Property Setter",
        "filters": [["module", "in", ("POSAwesome")]],
    },
    {
        "doctype": "Property Setter",
        "filters": [["name", "in", ("Sales Invoice-posa_pos_opening_shift-no_copy")]],
    },
    {
        "doctype": "DocType",
        "filters": [["name", "in", ("POS Relay Workflow State")]],
    },
    {
        "doctype": "Role",
        "filters": [
            ["role_name", "in", ["Sales Commission", "Sales Commission Admin"]]
        ],
    },
]
