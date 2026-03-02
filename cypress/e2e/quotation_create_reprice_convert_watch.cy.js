const { loginWithOtp, frappeCall } = require("./_helpers/pos_auth");

describe("Quotation create/reprice/convert", () => {
  it("creates a quotation, previews repricing, and converts to Sales Order token", () => {
    loginWithOtp();
    cy.visit("/app/posapp");

    let profile;
    let itemCode = "";
    let itemUom = "Nos";
    let quoteName = "";

    const resolveProfile = () =>
      frappeCall("posawesome.posawesome.api.posapp.check_opening_shift", {
        user: Cypress.env("username"),
      }).then((r) => {
        const data = (r && r.message) || {};
        if (data.pos_profile && data.pos_profile.name) return data.pos_profile;
        return frappeCall("frappe.client.get_list", {
          doctype: "POS Profile",
          fields: ["name"],
          filters: { disabled: 0 },
          limit_page_length: 20,
        }).then((listResp) => {
          const rows = Array.isArray(listResp && listResp.message) ? listResp.message : [];
          const preferred =
            rows.find((row) => String(row.name || "").trim() === "PJ7 CASHIER") || rows[0] || {};
          return frappeCall("frappe.client.get", { doctype: "POS Profile", name: preferred.name }).then(
            (docResp) => (docResp && docResp.message) || {}
          );
        });
      });

    return resolveProfile()
      .then((resolvedProfile) => {
        profile = resolvedProfile || {};
        expect(profile.name, "profile name").to.be.a("string").and.not.be.empty;
        expect(profile.company, "company").to.be.a("string").and.not.be.empty;
        expect(profile.currency, "currency").to.be.a("string").and.not.be.empty;
        return frappeCall("frappe.client.get_list", {
          doctype: "Item",
          fields: ["name", "stock_uom"],
          filters: { disabled: 0, is_sales_item: 1 },
          limit_page_length: 1,
        });
      })
      .then((r) => {
        const rows = Array.isArray(r && r.message) ? r.message : [];
        expect(rows.length, "at least one sales item").to.be.greaterThan(0);
        itemCode = String(rows[0].name || "").trim();
        itemUom = String(rows[0].stock_uom || "Nos").trim() || "Nos";
        expect(itemCode, "item code").to.not.be.empty;
        return frappeCall("posawesome.posawesome.api.posapp.create_quotation_token", {
          data: {
            pos_profile: profile.name,
            company: profile.company,
            customer: profile.customer,
            currency: profile.currency,
            posting_date: new Date().toISOString().slice(0, 10),
            items: [{ item_code: itemCode, qty: 1, uom: itemUom, rate: 100 }],
          },
        });
      })
      .then((r) => {
        const msg = (r && r.message) || {};
        quoteName = String(msg.quote_name || "").trim();
        expect(quoteName, "quote_name").to.not.be.empty;
        return frappeCall("posawesome.posawesome.api.posapp.quotation_reprice_preview", {
          quotation_name: quoteName,
          pos_profile: profile.name,
        });
      })
      .then((r) => {
        const preview = (r && r.message) || {};
        expect(preview.quote_name, "preview quote_name").to.eq(quoteName);
        expect(Array.isArray(preview.repriced_lines), "repriced lines").to.eq(true);
        expect(preview.repriced_lines.length, "repriced line count").to.be.greaterThan(0);
        return frappeCall("posawesome.posawesome.api.posapp.convert_quotation_to_sales_order_token", {
          quotation_name: quoteName,
          pos_profile: profile.name,
          confirm_reprice: 1,
        });
      })
      .then((r) => {
        const converted = (r && r.message) || {};
        expect(converted.sales_order_name || converted.token_id, "token/SO name").to.be.a("string").and.not.be.empty;
      });
  });
});
