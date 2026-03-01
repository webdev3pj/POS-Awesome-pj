const { loginWithOtp, frappeCall } = require("./_helpers/pos_auth");

function getSessionContext() {
  return frappeCall("posawesome.posawesome.api.posapp.check_opening_shift", {
    user: Cypress.env("username"),
  }).then((r) => {
    const data = (r && r.message) || {};
    if (data.pos_profile && data.pos_profile.name) {
      return data;
    }
    return frappeCall("frappe.client.get_list", {
      doctype: "POS Profile",
      fields: ["name"],
      filters: { disabled: 0 },
      limit_page_length: 20,
    }).then((listResp) => {
      const rows = Array.isArray(listResp && listResp.message) ? listResp.message : [];
      const preferred =
        rows.find((row) => String(row.name || "").trim() === "PJ7 CASHIER") || rows[0] || {};
      expect(preferred.name, "fallback POS profile name").to.be.a("string").and.not.be.empty;
      return frappeCall("frappe.client.get", {
        doctype: "POS Profile",
        name: preferred.name,
      }).then((docResp) => {
        const profile = (docResp && docResp.message) || {};
        expect(profile.name, "resolved POS profile").to.be.a("string").and.not.be.empty;
        return { pos_profile: profile };
      });
    });
  });
}

describe("Cashier Sales Order age policy (cloud + relay metadata)", () => {
  it("returns stale metadata and enforces strict mode selection cutoff", () => {
    loginWithOtp();
    cy.visit("/app/posapp");

    getSessionContext().then((ctx) => {
      const profile = ctx.pos_profile || {};
      const company = profile.company;
      const currency = profile.currency;
      const profileName = profile.name;
      expect(company, "company").to.be.a("string").and.not.be.empty;
      expect(currency, "currency").to.be.a("string").and.not.be.empty;
      expect(profileName, "profile name").to.be.a("string").and.not.be.empty;

      return frappeCall("posawesome.posawesome.api.posapp.search_orders", {
        company,
        currency,
        pos_profile: profileName,
        days_back: 1,
        allow_stale: 1,
        history_days: 30,
      }).then((allResp) => {
        const allRows = Array.isArray(allResp && allResp.message) ? allResp.message : [];
        allRows.forEach((row) => {
          expect(row, "row has order_age_days").to.have.property("order_age_days");
          expect(row, "row has is_stale").to.have.property("is_stale");
        });

        const staleRow = allRows.find((row) => Number(row && row.is_stale ? 1 : 0) === 1);
        return frappeCall("posawesome.posawesome.api.posapp.search_orders", {
          company,
          currency,
          pos_profile: profileName,
          days_back: 1,
          allow_stale: 0,
          history_days: 30,
        }).then((strictResp) => {
          const strictRows = Array.isArray(strictResp && strictResp.message) ? strictResp.message : [];
          if (staleRow && staleRow.name) {
            const found = strictRows.some((row) => String(row.name || "") === String(staleRow.name || ""));
            expect(found, "stale row excluded in strict mode").to.eq(false);
          } else {
            strictRows.forEach((row) => {
              expect(Number(row.order_age_days || 0), "strict result age <= 1").to.be.at.most(1);
            });
          }
        });
      });
    });

    cy.window().then((win) => {
      const relayBase = String(
        (win.localStorage && win.localStorage.getItem("pos_profile_relay_url")) || "http://127.0.0.1:8787"
      )
        .trim()
        .replace(/\/$/, "");
      const relayKey = String((win.localStorage && win.localStorage.getItem("posa_relay_client_key")) || "").trim();
      const headers = relayKey ? { "X-Relay-Client-Key": relayKey } : {};
      cy.request({
        method: "GET",
        url: `${relayBase}/relay/tokens/search?limit=20&statuses_csv=TOKEN_OPEN&max_age_days=1&allow_stale=1&history_days=30`,
        headers,
        failOnStatusCode: false,
      }).then((resp) => {
        expect([200, 401, 403], "relay search status").to.include(resp.status);
        if (resp.status === 200) {
          const rows = Array.isArray(resp.body && resp.body.rows) ? resp.body.rows : [];
          rows.forEach((row) => {
            expect(row, "relay row has order_age_days").to.have.property("order_age_days");
            expect(row, "relay row has is_stale").to.have.property("is_stale");
          });
        }
      });
    });
  });
});
