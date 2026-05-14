import frappe

from posawesome.posawesome.api.posapp import get_company_domain


def set_patient(doc):
    domain = get_company_domain(doc.company)
    if domain != "Healthcare":
        return
    patient_list = frappe.get_all(
        "Patient", filters={"customer": doc.customer}, page_length=1
    )
    if patient_list:
        doc.patient = patient_list[0].name
