const { loginWithOtp, frappeCall } = require("./_helpers/pos_auth");

function frappeCallRaw(method, args) {
  return cy.window({ timeout: 30000 }).then((win) => {
    return new Cypress.Promise((resolve) => {
      win.frappe.call({
        method,
        args: args || {},
        callback: (r) => resolve(r || {}),
        error: (err) => resolve({ error: err }),
      });
    });
  });
}

describe("Quotation expiry hard-stop", () => {
  it("blocks conversion of expired quotation", () => {
    loginWithOtp();
    cy.visit("/app/posapp");

    let profile;
    let itemCode = "";
    let itemUom = "Nos";
    let quoteName = "";
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

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

    resolveProfile()
      .then((resolvedProfile) => {
        profile = resolvedProfile || {};
        expect(profile.name, "profile name").to.be.a("string").and.not.be.empty;
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
        return frappeCall("posawesome.posawesome.api.posapp.create_quotation_token", {
          data: {
            pos_profile: profile.name,
            company: profile.company,
            customer: profile.customer,
            currency: profile.currency,
            posting_date: yesterday,
            valid_till: yesterday,
            items: [{ item_code: itemCode, qty: 1, uom: itemUom, rate: 100 }],
          },
        });
      })
      .then((r) => {
        const msg = (r && r.message) || {};
        quoteName = String(msg.quote_name || "").trim();
        expect(quoteName, "quote_name").to.not.be.empty;
        return frappeCallRaw("posawesome.posawesome.api.posapp.convert_quotation_to_sales_order_token", {
          quotation_name: quoteName,
          pos_profile: profile.name,
          confirm_reprice: 1,
        });
      })
      .then((r) => {
        const failed =
          !!(r && r.exc) ||
          !!(r && r._server_messages) ||
          !!(r && r.error) ||
          /expired/i.test(JSON.stringify(r || {}));
        expect(failed, "expired quotation conversion blocked").to.eq(true);
      });
  });
});
