describe('Relay demo baseline UI (watch mode)', () => {
  it('captures baseline local relay dashboard and queue pages before SA/Cashier demo', () => {
    cy.visit('http://127.0.0.1:8787/');
    cy.contains('POS Relay Dashboard', { timeout: 30000 }).should('be.visible');
    cy.contains('Outbox Counters (v2 Local-First)', { timeout: 30000 }).should('be.visible');
    cy.contains('Transaction Timeline (Local Sales)', { timeout: 30000 }).should('be.visible');
    cy.screenshot('relay-demo-baseline-dashboard');

    cy.visit('http://127.0.0.1:8787/queue');
    cy.contains('Relay Queue (Real-Time)', { timeout: 30000 }).should('be.visible');
    cy.contains('Latest Events', { timeout: 30000 }).should('be.visible');
    cy.screenshot('relay-demo-baseline-queue');
  });
});
