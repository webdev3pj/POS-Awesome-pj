describe('Relay demo post-run UI (watch mode)', () => {
  it('captures detailed local relay status after SA + Cashier submissions', () => {
    cy.readFile('cypress/tmp/latest_sa_order.json', { timeout: 10000 }).then((sa) => {
      const tokenId = String(sa?.tokenId || '').trim();
      expect(tokenId, 'latest SA token id').to.not.equal('');

      cy.visit('http://127.0.0.1:8787/');
      cy.request({
        method: 'GET',
        url: `http://127.0.0.1:8787/relay/token/${encodeURIComponent(tokenId)}`,
        timeout: 30000,
      }).then((resp) => {
        expect(resp.status).to.eq(200);
        expect(resp.body?.ok).to.eq(true);
        const pretty = JSON.stringify(resp.body, null, 2);
        cy.document().then((doc) => {
          doc.body.innerHTML = `<div style="background:#0b1220;color:#e5e7eb;font-family:monospace;padding:16px;min-height:100vh"><h3>Relay Token JSON</h3><pre>${pretty
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')}</pre></div>`;
        });
        cy.contains(tokenId, { timeout: 30000 }).should('exist');
        cy.contains('TOKEN_', { timeout: 30000 }).should('exist');
        cy.screenshot('relay-demo-postrun-token-json');
      });
    });

    cy.readFile('cypress/tmp/latest_cashier_relay_commit.json', { timeout: 10000 }).then((cashier) => {
      const localSaleRef = String(cashier?.localSaleRef || '').trim();
      expect(localSaleRef, 'latest cashier local_sale_ref').to.not.equal('');

      const dashboardUrl = `http://127.0.0.1:8787/?tx_pos_profile=${encodeURIComponent(
        'PJ7 CASHIER'
      )}&tx_search=${encodeURIComponent(localSaleRef)}&tx_limit=20`;
      cy.visit(dashboardUrl);
      cy.contains('POS Relay Dashboard', { timeout: 30000 }).should('be.visible');
      cy.contains('Transaction Timeline (Local Sales)', { timeout: 30000 }).should('be.visible');
      cy.contains(localSaleRef, { timeout: 30000 }).should('exist');
      cy.screenshot('relay-demo-postrun-dashboard-filtered');

      cy.request({
        method: 'GET',
        url: `http://127.0.0.1:8787/api/transactions/${encodeURIComponent(localSaleRef)}`,
        timeout: 30000,
      }).then((resp) => {
        expect(resp.status).to.eq(200);
        expect(resp.body?.ok).to.eq(true);
        const pretty = JSON.stringify(resp.body, null, 2);
        cy.document().then((doc) => {
          doc.body.innerHTML = `<div style="background:#0b1220;color:#e5e7eb;font-family:monospace;padding:16px;min-height:100vh"><h3>Relay Transaction Detail JSON</h3><pre>${pretty
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')}</pre></div>`;
        });
        cy.contains(localSaleRef, { timeout: 30000 }).should('exist');
        cy.contains('SALE_COMMITTED_LOCAL', { timeout: 30000 }).should('exist');
        cy.contains('PAID_PENDING_PICK', { timeout: 30000 }).should('exist');
        cy.screenshot('relay-demo-postrun-transaction-json');
        cy.log('Pause 20s: observe relay transaction detail (cashier invoice) status');
        cy.wait(20000);
      });
    });

    cy.visit('http://127.0.0.1:8787/queue');
    cy.contains('Relay Queue (Real-Time)', { timeout: 30000 }).should('be.visible');
    cy.contains('Latest Events', { timeout: 30000 }).should('be.visible');
    cy.screenshot('relay-demo-postrun-queue');
  });
});
