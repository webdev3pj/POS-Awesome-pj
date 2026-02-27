describe("Relay demo picker post-update UI (watch mode)", () => {
  it("proves picker updates are visible on relay dashboard + transaction detail", () => {
    cy.readFile("cypress/tmp/latest_picker_update.json", {
      timeout: 10000,
      failOnNonExistent: false,
    }).then((pickerData) => {
      const fallbackRef =
        String((pickerData && pickerData.local_sale_ref) || "").trim() ||
        "";

      if (fallbackRef) {
        return cy.wrap({
          localSaleRef: fallbackRef,
          firstLineId: Number((pickerData && pickerData.first_line_id) || 0),
          pickedQty: Number((pickerData && pickerData.picked_qty) || 0),
        });
      }

      return cy.readFile("cypress/tmp/picker_dispatch_target.json", { timeout: 10000 }).then((target) => {
        return {
          localSaleRef: String((target && target.local_sale_ref) || "").trim(),
          firstLineId: 0,
          pickedQty: 0,
        };
      });
    })
      .then(({ localSaleRef, firstLineId, pickedQty }) => {
        expect(localSaleRef, "picker relay local_sale_ref").to.not.equal("");

        const dashboardUrl = `http://127.0.0.1:8787/?tx_pos_profile=${encodeURIComponent(
          "PJ7 CASHIER"
        )}&tx_search=${encodeURIComponent(localSaleRef)}&tx_limit=20`;

        cy.visit(dashboardUrl);
        cy.contains("POS Relay Dashboard", { timeout: 30000 }).should("be.visible");
        cy.contains("Transaction Timeline (Local Sales)", { timeout: 30000 }).should("be.visible");
        cy.contains(localSaleRef, { timeout: 30000 }).should("exist");
        cy.screenshot("relay-demo-picker-post-dashboard-filtered");

        cy.request({
          method: "GET",
          url: `http://127.0.0.1:8787/api/transactions/${encodeURIComponent(localSaleRef)}`,
          timeout: 30000,
        }).then((resp) => {
          expect(resp.status).to.eq(200);
          expect(resp.body && resp.body.ok).to.eq(true);
          const sale = (resp.body && resp.body.sale) || {};
          expect(String(sale.local_sale_ref || "").trim(), "relay sale local_sale_ref").to.eq(localSaleRef);
          expect(String(sale.pick_status || ""), "relay pick_status after picker").to.eq(
            "PICKED_READY_FOR_RELEASE"
          );
          expect(String(sale.dispatch_status || ""), "dispatch still pending after picker").to.eq("PENDING");

          const lines = Array.isArray(resp.body && resp.body.lines) ? resp.body.lines : [];
          expect(lines.length, "relay lines after picker").to.be.greaterThan(0);

          if (firstLineId > 0) {
            const targetLine = lines.find((line) => Number(line && line.id) === firstLineId);
            expect(targetLine, `line ${firstLineId} exists on relay`).to.be.an("object");
            expect(targetLine.payload, "line payload exists").to.be.an("object");
            expect(targetLine.payload.picker, "line payload.picker exists").to.be.an("object");
            if (pickedQty > 0) {
              expect(Number(targetLine.payload.picker.picked_qty), "persisted picked_qty").to.eq(pickedQty);
            }
          }

          const pretty = JSON.stringify(resp.body, null, 2);
          cy.document().then((doc) => {
            doc.body.innerHTML = `<div style="background:#0b1220;color:#e5e7eb;font-family:monospace;padding:16px;min-height:100vh"><h3>Relay Picker Transaction JSON</h3><pre>${pretty
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")}</pre></div>`;
          });
          cy.contains(localSaleRef, { timeout: 30000 }).should("exist");
          cy.contains("PICKED_READY_FOR_RELEASE", { timeout: 30000 }).should("exist");
          cy.screenshot("relay-demo-picker-post-transaction-json");
        });
      });
  });
});
