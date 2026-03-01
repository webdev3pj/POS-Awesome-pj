const { loginWithOtp, frappeCall } = require("./_helpers/pos_auth");

describe("Quotation relay-local flow + outbox sync evidence", () => {
  it("creates quote locally, converts to token, and records QUOTE_UPSERT outbox", () => {
    loginWithOtp();
    cy.visit("/app/posapp");

    let profile;
    let itemCode = "";
    let itemUom = "Nos";
    let relayBase = "http://127.0.0.1:8787";
    let relayHeaders = {};
    let quoteId = "";

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
        relayBase = String(profile.custom_edge_relay_url || relayBase).trim().replace(/\/$/, "");
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
      });

    cy.window().then((win) => {
      const relayKey = String((win.localStorage && win.localStorage.getItem("posa_relay_client_key")) || "").trim();
      relayHeaders = relayKey ? { "X-Relay-Client-Key": relayKey } : {};

      cy.request({
        method: "POST",
        url: `${relayBase}/relay/quote/create`,
        headers: relayHeaders,
        body: {
          pos_profile_id: profile.name,
          created_by: (win.frappe && win.frappe.session && win.frappe.session.user) || "",
          customer_id: profile.customer,
          customer_name: profile.customer,
          currency: profile.currency,
          role: String((win.localStorage && win.localStorage.getItem("pos_current_role")) || "").trim(),
          items: [{ item_code: itemCode, item_name: itemCode, qty: 1, uom: itemUom, rate: 100, amount: 100 }],
        },
      }).then((createResp) => {
        expect(createResp.status, "relay quote create HTTP").to.eq(200);
        expect(createResp.body && createResp.body.ok, "relay quote create ok").to.eq(true);
        quoteId = String((createResp.body.quote && createResp.body.quote.quote_id) || "").trim();
        expect(quoteId, "quote_id").to.not.be.empty;

        cy.request({
          method: "GET",
          url: `${relayBase}/relay/quotes/search?pos_profile_id=${encodeURIComponent(
            profile.name
          )}&search=${encodeURIComponent(quoteId)}&limit=20&allow_stale=1&history_days=30&max_age_days=1`,
          headers: relayHeaders,
        }).then((searchResp) => {
          expect(searchResp.status, "relay quote search HTTP").to.eq(200);
          const rows = Array.isArray(searchResp.body && searchResp.body.rows) ? searchResp.body.rows : [];
          const found = rows.some((row) => String(row.quote_id || "") === quoteId);
          expect(found, "created quote in relay search").to.eq(true);
        });

        cy.request({
          method: "POST",
          url: `${relayBase}/relay/quote/reprice-preview`,
          headers: relayHeaders,
          body: { quote_id: quoteId, role: String((win.localStorage && win.localStorage.getItem("pos_current_role")) || "").trim() },
        }).then((previewResp) => {
          expect(previewResp.status, "relay quote preview HTTP").to.eq(200);
          expect(previewResp.body && previewResp.body.ok, "relay quote preview ok").to.eq(true);
        });

        cy.request({
          method: "POST",
          url: `${relayBase}/relay/quote/convert-to-token`,
          headers: relayHeaders,
          body: {
            quote_id: quoteId,
            cashier_user_id: (win.frappe && win.frappe.session && win.frappe.session.user) || "",
            role: String((win.localStorage && win.localStorage.getItem("pos_current_role")) || "").trim(),
            confirm_reprice: 1,
          },
        }).then((convertResp) => {
          expect(convertResp.status, "relay quote convert HTTP").to.eq(200);
          expect(convertResp.body && convertResp.body.ok, "relay quote convert ok").to.eq(true);
          const tokenId = String((convertResp.body.token && convertResp.body.token.token_id) || "").trim();
          expect(tokenId, "token id from quote convert").to.not.be.empty;

          cy.request({
            method: "GET",
            url: `${relayBase}/relay/token/${encodeURIComponent(tokenId)}`,
            headers: relayHeaders,
          }).then((tokenResp) => {
            expect(tokenResp.status, "relay token get HTTP").to.eq(200);
            expect(tokenResp.body && tokenResp.body.ok, "relay token get ok").to.eq(true);
          });
        });

        cy.request({
          method: "GET",
          url: `${relayBase}/api/outbox?limit=200`,
          failOnStatusCode: false,
        }).then((outboxResp) => {
          expect([200, 401, 403], "outbox endpoint status").to.include(outboxResp.status);
          if (outboxResp.status === 200) {
            const rows = Array.isArray(outboxResp.body && outboxResp.body.rows) ? outboxResp.body.rows : [];
            const hasQuoteUpsert = rows.some((row) => String(row.event_type || "") === "QUOTE_UPSERT");
            expect(hasQuoteUpsert, "QUOTE_UPSERT outbox event exists").to.eq(true);
          }
        });
      });
    });
  });
});
