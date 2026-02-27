describe("Phase 3 relay role guards (watch mode)", () => {
  const relayBase = Cypress.env("relayBase") || "http://127.0.0.1:8787";

  const requestJson = (path, body = {}) =>
    cy.request({
      method: "POST",
      url: `${relayBase}${path}`,
      failOnStatusCode: false,
      body,
    });

  const expectRoleRequired = (path, body = {}) => {
    requestJson(path, body).then((resp) => {
      expect(resp.status, `${path} missing role status`).to.eq(400);
      expect(resp.body, `${path} missing role body`).to.include({
        ok: false,
        code: "RELAY_ROLE_REQUIRED",
      });
    });
  };

  const expectRoleDenied = (path, body = {}, expectedRole) => {
    requestJson(path, body).then((resp) => {
      expect(resp.status, `${path} unauthorized role status`).to.eq(403);
      expect(resp.body, `${path} unauthorized role body`).to.include({
        ok: false,
        code: "RELAY_ROLE_NOT_AUTHORIZED",
      });
      expect(String(resp.body.message || ""), `${path} unauthorized role message`).to.include(
        expectedRole,
      );
    });
  };

  it("rejects missing-role and wrong-role writes across v2 relay endpoints", () => {
    expectRoleRequired("/relay/session/open", {
      pos_profile_id: "PJ7 CASHIER",
      cashier_user_id: "cline@pjjamaica.com",
      device_id: "POS-SECURITY-V2",
    });

    expectRoleDenied(
      "/relay/session/open",
      {
        pos_profile_id: "PJ7 CASHIER",
        cashier_user_id: "cline@pjjamaica.com",
        device_id: "POS-SECURITY-V2",
        role: "cline-Picker",
      },
      "cline-Picker",
    );

    expectRoleRequired("/relay/token/create", {
      pos_profile_id: "PJ7 CASHIER",
      cashier_user_id: "cline@pjjamaica.com",
      customer_id: "RETAIL PJ7 WALK IN",
      customer_name: "RETAIL PJ7 WALK IN",
      items: [{ item_code: "W80C", item_name: '8" GROOVE JOINT PLIERS', qty: 1, rate: 1350, amount: 1350, uom: "Nos" }],
    });

    expectRoleDenied(
      "/relay/token/create",
      {
        pos_profile_id: "PJ7 CASHIER",
        cashier_user_id: "cline@pjjamaica.com",
        customer_id: "RETAIL PJ7 WALK IN",
        customer_name: "RETAIL PJ7 WALK IN",
        items: [{ item_code: "W80C", item_name: '8" GROOVE JOINT PLIERS', qty: 1, rate: 1350, amount: 1350, uom: "Nos" }],
        role: "cline-Dispatch",
      },
      "cline-Dispatch",
    );

    expectRoleRequired("/relay/commit-invoice", {
      idempotency_key: "SECURITY-COMMIT-V2",
    });

    expectRoleDenied(
      "/relay/commit-invoice",
      {
        role: "cline-Picker",
        idempotency_key: "SECURITY-COMMIT-V2",
      },
      "cline-Picker",
    );

    expectRoleRequired("/relay/pick/update", {
      local_sale_ref: "LSR-TEST-SECURITY",
      picking_status: "PICK_IN_PROGRESS",
    });

    expectRoleDenied(
      "/relay/pick/update",
      {
        role: "cline-Cashier",
        local_sale_ref: "LSR-TEST-SECURITY",
        picking_status: "PICK_IN_PROGRESS",
      },
      "cline-Cashier",
    );

    expectRoleRequired("/relay/dispatch/release", {
      local_sale_ref: "LSR-TEST-SECURITY",
    });

    expectRoleDenied(
      "/relay/dispatch/release",
      {
        role: "cline-Picker",
        local_sale_ref: "LSR-TEST-SECURITY",
      },
      "cline-Picker",
    );
  });

  it("rejects missing-role and wrong-role writes across legacy relay endpoints", () => {
    expectRoleRequired("/relay/token", {
      pos_profile_id: "PJ7 CASHIER",
      customer_id: "RETAIL PJ7 WALK IN",
      customer_name: "RETAIL PJ7 WALK IN",
      items: [{ item_code: "W80C", item_name: '8" GROOVE JOINT PLIERS', qty: 1, rate: 1350, amount: 1350, uom: "Nos" }],
    });

    expectRoleDenied(
      "/relay/token",
      {
        pos_profile_id: "PJ7 CASHIER",
        customer_id: "RETAIL PJ7 WALK IN",
        customer_name: "RETAIL PJ7 WALK IN",
        items: [{ item_code: "W80C", item_name: '8" GROOVE JOINT PLIERS', qty: 1, rate: 1350, amount: 1350, uom: "Nos" }],
        role: "cline-Dispatch",
      },
      "cline-Dispatch",
    );

    expectRoleRequired("/relay/pick", {
      local_sale_ref: "LSR-TEST-SECURITY",
      picking_status: "PICK_IN_PROGRESS",
    });

    expectRoleDenied(
      "/relay/pick",
      {
        role: "cline-Cashier",
        local_sale_ref: "LSR-TEST-SECURITY",
        picking_status: "PICK_IN_PROGRESS",
      },
      "cline-Cashier",
    );

    expectRoleRequired("/relay/release", {
      local_sale_ref: "LSR-TEST-SECURITY",
    });

    expectRoleDenied(
      "/relay/release",
      {
        role: "cline-Picker",
        local_sale_ref: "LSR-TEST-SECURITY",
      },
      "cline-Picker",
    );

    expectRoleRequired("/relay/submit-invoice", {
      invoice: {},
      data: {},
    });

    expectRoleDenied(
      "/relay/submit-invoice",
      {
        role: "cline-Picker",
        invoice: {},
        data: {},
      },
      "cline-Picker",
    );
  });

  it("allows authorized roles to get past relay auth gates", () => {
    requestJson("/relay/session/open", {
      pos_profile_id: "PJ7 CASHIER",
      cashier_user_id: "cline@pjjamaica.com",
      device_id: "POS-SECURITY-ALLOW",
      role: "cline-Cashier",
    }).then((resp) => {
      expect(resp.status, "session/open allowed role status").to.eq(200);
      expect(resp.body).to.have.nested.property("session.session_id");
    });

    requestJson("/relay/commit-invoice", {
      role: "cline-Cashier",
    }).then((resp) => {
      expect(resp.status, "commit-invoice allowed role reaches payload validation").to.eq(400);
      expect(resp.body).to.include({
        ok: false,
        code: "IDEMPOTENCY_KEY_REQUIRED",
      });
    });

    requestJson("/relay/token/create", {
      pos_profile_id: "PJ7 CASHIER",
      cashier_user_id: "cline@pjjamaica.com",
      customer_id: "RETAIL PJ7 WALK IN",
      customer_name: "RETAIL PJ7 WALK IN",
      role: "cline-Sales Associate",
      items: [{ item_code: "W80C", item_name: '8" GROOVE JOINT PLIERS', qty: 1, rate: 1350, amount: 1350, uom: "Nos" }],
    }).then((resp) => {
      expect(resp.status, "token/create allowed role status").to.eq(200);
      expect(resp.body).to.include({ ok: true });
      expect(resp.body).to.have.property("token");
    });
  });
});
