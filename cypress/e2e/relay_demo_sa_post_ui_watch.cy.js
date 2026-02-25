describe('Relay demo SA post-submit UI (watch mode)', () => {
  it('captures relay UI after SA creates a token/order', () => {
    cy.readFile('cypress/tmp/latest_sa_order.json', { timeout: 10000 }).then((sa) => {
      const tokenId = String(sa?.tokenId || '').trim();
      expect(tokenId, 'latest SA token id').to.not.equal('');

      cy.visit('http://127.0.0.1:8787/');
      cy.contains('POS Relay Dashboard', { timeout: 30000 }).should('be.visible');
      cy.contains('Outbox Counters (v2 Local-First)', { timeout: 30000 }).should('be.visible');
      cy.screenshot('relay-demo-sa-post-dashboard');

      cy.request({
        method: 'GET',
        url: `http://127.0.0.1:8787/relay/token/${encodeURIComponent(tokenId)}`,
        timeout: 30000,
      }).then((resp) => {
        expect(resp.status).to.eq(200);
        expect(resp.body?.ok).to.eq(true);
        expect(String(resp.body?.token?.token_id || '').trim()).to.eq(tokenId);
        expect(String(resp.body?.token?.status || '').trim()).to.match(/^TOKEN_/);

        const pretty = JSON.stringify(resp.body, null, 2);
        cy.document().then((doc) => {
          doc.body.innerHTML = `<div style="background:#0b1220;color:#e5e7eb;font-family:monospace;padding:16px;min-height:100vh"><h3>Relay Token JSON</h3><pre>${pretty
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')}</pre></div>`;
        });
        cy.contains(tokenId, { timeout: 30000 }).should('exist');
        cy.contains('TOKEN_OPEN', { timeout: 30000 }).should('exist');
        cy.screenshot('relay-demo-sa-post-token-json');
        cy.log('Pause 20s: observe relay token (SA Sales Order) detail');
        cy.wait(20000);
      });

      cy.visit('http://127.0.0.1:8787/queue');
      cy.contains('Relay Queue (Real-Time)', { timeout: 30000 }).should('be.visible');
      cy.screenshot('relay-demo-sa-post-queue');
    });
  });
});
