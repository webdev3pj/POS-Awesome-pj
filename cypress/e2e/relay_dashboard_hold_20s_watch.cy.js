describe('Relay dashboard hold (watch mode)', () => {
  it('opens the local relay dashboard and keeps it visible for 20 seconds', () => {
    cy.readFile('cypress/tmp/latest_cashier_relay_commit.json', { timeout: 10000 }).then((data) => {
      const localSaleRef = String(data?.localSaleRef || '').trim();
      const url =
        localSaleRef
          ? `http://127.0.0.1:8787/?tx_pos_profile=${encodeURIComponent('PJ7 CASHIER')}&tx_search=${encodeURIComponent(localSaleRef)}&tx_limit=20`
          : 'http://127.0.0.1:8787/';

      cy.visit(url);
      cy.contains('POS Relay Dashboard', { timeout: 30000 }).should('be.visible');
      cy.contains('Transaction Timeline (Local Sales)', { timeout: 30000 }).should('be.visible');
      if (localSaleRef) {
        cy.contains(localSaleRef, { timeout: 30000 }).should('exist');
      }

      cy.log(`Holding relay dashboard open for 20 seconds: ${url}`);
      cy.screenshot('relay-dashboard-hold-before');
      cy.wait(20000);
      cy.screenshot('relay-dashboard-hold-after-20s');
    });
  });
});
