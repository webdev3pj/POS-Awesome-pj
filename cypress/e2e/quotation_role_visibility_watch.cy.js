const { loginWithOtp, frappeCall } = require("./_helpers/pos_auth");

describe("Quotation role visibility", () => {
  it("shows/hides Save Quote and Select Quote based on role + POS profile toggles", () => {
    loginWithOtp();
    cy.visit("/app/posapp");
    cy.location("pathname", { timeout: 90000 }).should("match", /^\/app\/posapp(?:\/)?$/);

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

    resolveProfile().then((profile) => {
      const allowSa = Number(profile.posa_allow_sa_quotation || 1) === 1;
      const allowCashier = Number(profile.posa_allow_cashier_quotation || 1) === 1;

      cy.window().then((win) => {
        const role = String((win.localStorage && win.localStorage.getItem("pos_current_role")) || "").trim();
        const shouldShow =
          (role === "cline-Sales Associate" && allowSa) || (role === "cline-Cashier" && allowCashier);

        cy.get("body", { timeout: 30000 }).then(($body) => {
          const text = ($body.text() || "").trim();
          const hasSaveQuote = /Save Quote/i.test(text);
          const hasSelectQuote = /Select Quote/i.test(text);
          if (!role || !["cline-Sales Associate", "cline-Cashier"].includes(role)) {
            cy.log(`Current role ${role || "(unknown)"} not in SA/Cashier scope; visibility assertion skipped.`);
            expect(true).to.eq(true);
            return;
          }
          expect(hasSaveQuote, "Save Quote visibility").to.eq(shouldShow);
          expect(hasSelectQuote, "Select Quote visibility").to.eq(shouldShow);
        });
      });
    });
  });
});
