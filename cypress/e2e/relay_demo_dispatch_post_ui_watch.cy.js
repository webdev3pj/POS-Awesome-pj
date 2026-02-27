describe("Relay demo dispatch post-release UI (watch mode)", () => {
  it("proves dispatch release is visible on relay dashboard + transaction detail", () => {
    cy.readFile("cypress/tmp/latest_dispatch_release.json", {
      timeout: 10000,
      failOnNonExistent: false,
    }).then((dispatchData) => {
      const localSaleRef =
        String((dispatchData && dispatchData.local_sale_ref) || "").trim() || "";
      if (localSaleRef) {
        return cy.wrap({ localSaleRef });
      }

      return cy.readFile("cypress/tmp/picker_dispatch_target.json", { timeout: 10000 }).then((target) => {
        return { localSaleRef: String((target && target.local_sale_ref) || "").trim() };
      });
    })
      .then(({ localSaleRef }) => {
        expect(localSaleRef, "dispatch relay local_sale_ref").to.not.equal("");

        const dashboardUrl = `http://127.0.0.1:8787/?tx_pos_profile=${encodeURIComponent(
          "PJ7 CASHIER"
        )}&tx_search=${encodeURIComponent(localSaleRef)}&tx_limit=20`;

        cy.visit(dashboardUrl);
        cy.contains("POS Relay Dashboard", { timeout: 30000 }).should("be.visible");
        cy.contains("Transaction Timeline (Local Sales)", { timeout: 30000 }).should("be.visible");
        cy.contains(localSaleRef, { timeout: 30000 }).should("exist");
        cy.contains(/RELEASED/i, { timeout: 30000 }).should("exist");
        cy.screenshot("relay-demo-dispatch-post-dashboard-filtered");

        cy.request({
          method: "GET",
          url: `http://127.0.0.1:8787/api/transactions/${encodeURIComponent(localSaleRef)}`,
          timeout: 30000,
        }).then((resp) => {
          expect(resp.status).to.eq(200);
          expect(resp.body && resp.body.ok).to.eq(true);
          const sale = (resp.body && resp.body.sale) || {};
          expect(String(sale.local_sale_ref || "").trim(), "relay sale local_sale_ref").to.eq(localSaleRef);
          expect(String(sale.pick_status || ""), "relay pick_status after dispatch").to.eq(
            "PICKED_READY_FOR_RELEASE"
          );
          expect(String(sale.dispatch_status || ""), "relay dispatch_status after dispatch").to.eq("RELEASED");

          const dispatchEvents = Array.isArray(resp.body && resp.body.dispatch_events)
            ? resp.body.dispatch_events
            : [];
          expect(dispatchEvents.length, "dispatch events present").to.be.greaterThan(0);
          const latestDispatch = dispatchEvents[dispatchEvents.length - 1] || {};
          expect(String(latestDispatch.event_type || ""), "latest dispatch event type").to.eq("RELEASED");

          const pretty = JSON.stringify(resp.body, null, 2);
          cy.document().then((doc) => {
            doc.body.innerHTML = `<div style="background:#0b1220;color:#e5e7eb;font-family:monospace;padding:16px;min-height:100vh"><h3>Relay Dispatch Transaction JSON</h3><pre>${pretty
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")}</pre></div>`;
          });
          cy.contains(localSaleRef, { timeout: 30000 }).should("exist");
          cy.contains("RELEASED", { timeout: 30000 }).should("exist");
          cy.screenshot("relay-demo-dispatch-post-transaction-json");
        });
      });
  });
});
