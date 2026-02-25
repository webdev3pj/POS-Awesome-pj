function pollLegacyQueueForEvent(eventId, maxAttempts = 15) {
  const targetId = Number(eventId);

  const attempt = (index = 0) => {
    return cy
      .request({
        method: 'GET',
        url: 'http://127.0.0.1:8787/api/queue',
        timeout: 30000,
      })
      .then((resp) => {
        expect(resp.status, 'relay /api/queue status').to.eq(200);
        const rows = Array.isArray(resp.body?.rows) ? resp.body.rows : [];
        const counts = resp.body?.counts || {};
        const match = rows.find((row) => Number(row?.id || 0) === targetId);

        if (match) {
          return { row: match, counts };
        }

        if (index >= maxAttempts) {
          throw new Error(`Queue event id=${targetId} was not visible in /api/queue after ${maxAttempts + 1} polls.`);
        }

        cy.wait(1000);
        return attempt(index + 1);
      });
  };

  return attempt(0);
}

describe('Relay queue UI (watch mode)', () => {
  it('shows queue page updating after a queued legacy relay event is enqueued', () => {
    let baselineTotal = 0;
    let queuedEventId = 0;

    cy.request({
      method: 'GET',
      url: 'http://127.0.0.1:8787/api/queue',
      timeout: 30000,
    }).then((resp) => {
      expect(resp.status).to.eq(200);
      baselineTotal = Number(resp.body?.counts?.total || 0);
      cy.log(`Baseline legacy queue total: ${baselineTotal}`);
    });

    cy.visit('http://127.0.0.1:8787/queue');
    cy.contains('Relay Queue (Real-Time)', { timeout: 30000 }).should('be.visible');
    cy.contains('Latest Events').should('be.visible');
    cy.screenshot('relay-queue-before-enqueue');

    const now = Date.now();
    const demoTokenId = `CYQ-${now}`;

    cy.request({
      method: 'POST',
      url: 'http://127.0.0.1:8787/relay/token',
      body: {
        token_id: demoTokenId,
        pos_profile_id: 'PJ7 CASHIER',
        cashier_user_id: 'cline@pjjamaica.com',
        customer_id: 'RETAIL PJ7 WALK IN',
        customer_name: 'RETAIL PJ7 WALK IN',
        items: [
          {
            item_code: 'W80C',
            item_name: '8" GROOVE JOINT PLIERS',
            qty: 1,
            uom: 'Nos',
            rate: 1350,
            amount: 1350,
          },
        ],
      },
      timeout: 30000,
    }).then((resp) => {
      expect(resp.status, 'legacy /relay/token enqueue status').to.eq(200);
      expect(resp.body?.ok, 'legacy queue enqueue ok').to.eq(true);
      queuedEventId = Number(resp.body?.event_id || 0);
      expect(queuedEventId, 'legacy queued event id').to.be.greaterThan(0);
      cy.log(`Enqueued legacy queue event id=${queuedEventId} token=${demoTokenId}`);
    });

    cy.then(() => {
      return pollLegacyQueueForEvent(queuedEventId).then(({ row, counts }) => {
        expect(Number(counts?.total || 0), 'legacy queue total after enqueue').to.be.greaterThan(baselineTotal);
        expect(String(row?.event_type || '').trim(), 'legacy queue event_type').to.eq('token_create');
        expect(['queued', 'processing', 'done', 'failed']).to.include(
          String(row?.status || '').trim(),
          'legacy queue row status'
        );
      });
    });

    // Reload UI to force visible counter/table refresh (page also auto-refreshes every 5s).
    cy.reload();
    cy.contains('Relay Queue (Real-Time)', { timeout: 30000 }).should('be.visible');
    cy.get('body').should('contain.text', String(queuedEventId));
    cy.get('body').should('contain.text', 'token_create');
    cy.screenshot('relay-queue-after-enqueue');
  });
});
