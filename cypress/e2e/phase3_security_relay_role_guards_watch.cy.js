describe("Phase 3 relay role guards (watch mode)", () => {
  it("rejects mutating relay requests when role is missing or unauthorized", () => {
    const relayBase = "http://127.0.0.1:8787";

    cy.request({
      method: "POST",
      url: `${relayBase}/relay/commit-invoice`,
      failOnStatusCode: false,
      body: {
        role: "cline-Picker",
        idempotency_key: "SECURITY-SMOKE",
      },
    }).then((resp) => {
      expect(resp.status).to.eq(403);
      expect(resp.body).to.include({ ok: false, code: "RELAY_ROLE_NOT_AUTHORIZED" });
      expect(String(resp.body.message || "")).to.match(/not allowed/i);
    });

    cy.request({
      method: "POST",
      url: `${relayBase}/relay/pick/update`,
      failOnStatusCode: false,
      body: {
        role: "cline-Cashier",
        local_sale_ref: "LSR-TEST-SECURITY",
        picking_status: "PICK_IN_PROGRESS",
      },
    }).then((resp) => {
      expect(resp.status).to.eq(403);
      expect(resp.body).to.include({ ok: false, code: "RELAY_ROLE_NOT_AUTHORIZED" });
    });

    cy.request({
      method: "POST",
      url: `${relayBase}/relay/token/create`,
      failOnStatusCode: false,
      body: {
        pos_profile_id: "PJ7 CASHIER",
        role: "cline-Dispatch",
        cashier_user_id: "cline@pjjamaica.com",
        customer_id: "RETAIL PJ7 WALK IN",
        customer_name: "RETAIL PJ7 WALK IN",
        items: [],
      },
    }).then((resp) => {
      expect(resp.status).to.eq(403);
      expect(resp.body).to.include({ ok: false, code: "RELAY_ROLE_NOT_AUTHORIZED" });
    });

    cy.request({
      method: "POST",
      url: `${relayBase}/relay/session/open`,
      failOnStatusCode: false,
      body: {
        pos_profile_id: "PJ7 CASHIER",
        cashier_user_id: "cline@pjjamaica.com",
        device_id: "POS-SECURITY",
      },
    }).then((resp) => {
      expect(resp.status).to.eq(400);
      expect(resp.body).to.include({ ok: false, code: "RELAY_ROLE_REQUIRED" });
    });
  });
});
