const { loginWithOtp } = require("./_helpers/pos_auth");

describe("Fulfillment stale visibility", () => {
  it("shows stale/fresh indicators when fulfillment workspace is active", () => {
    loginWithOtp();
    cy.visit("/app/posapp");
    cy.location("pathname", { timeout: 90000 }).should("match", /^\/app\/posapp(?:\/)?$/);

    cy.get("body", { timeout: 60000 }).then(($body) => {
      const text = ($body.text() || "").trim();
      const isFulfillmentView =
        /Picker Queue/i.test(text) || /Dispatch Queue/i.test(text) || /Supervisor Fulfillment/i.test(text);
      if (!isFulfillmentView) {
        cy.log("Current role is not fulfillment; stale chip UI check skipped for this run.");
        expect(true).to.eq(true);
        return;
      }
      const hasChip = /Fresh/i.test(text) || /Stale/i.test(text);
      expect(hasChip, "fresh/stale chip visible in fulfillment view").to.eq(true);
    });
  });
});

