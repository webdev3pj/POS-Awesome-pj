function findFirstSelector($root, selectors) {
  return selectors.find((selector) => $root.find(selector).length > 0);
}

function typeIntoFirstAvailable(selectors, value, options = {}) {
  cy.get('body', { timeout: 30000 }).then(($body) => {
    const selector = findFirstSelector($body, selectors);
    expect(selector, `selector from list: ${selectors.join(', ')}`).to.be.a('string');
    cy.get(selector, { timeout: 30000 })
      .first()
      .should('be.visible')
      .clear({ force: true })
      .type(value, options);
  });
}

function clickFirstAvailable(selectors) {
  cy.get('body', { timeout: 30000 }).then(($body) => {
    const selector = findFirstSelector($body, selectors);
    expect(selector, `selector from list: ${selectors.join(', ')}`).to.be.a('string');
    cy.get(selector, { timeout: 30000 }).first().should('be.visible').click({ force: true });
  });
}

function loginWithOtp() {
  const username = Cypress.env('username');
  const password = Cypress.env('password');
  const totpUri = Cypress.env('totpUri');

  expect(Cypress.config('baseUrl'), 'CYPRESS_baseUrl').to.be.a('string').and.not.be.empty;
  expect(username, 'CYPRESS_username').to.be.a('string').and.not.be.empty;
  expect(password, 'CYPRESS_password').to.be.a('string').and.not.be.empty;
  expect(totpUri, 'CYPRESS_totpUri').to.be.a('string').and.not.be.empty;

  cy.clearCookies();
  cy.clearLocalStorage();
  cy.visit('/login');

  typeIntoFirstAvailable(
    ['#login_email', "input[name='usr']", "input[name='login_email']", "input[type='email']"],
    username
  );
  typeIntoFirstAvailable(
    ['#login_password', "input[name='pwd']", "input[type='password']"],
    password,
    { log: false }
  );
  clickFirstAvailable([
    'button.btn-login',
    '.btn-login',
    "button[type='submit']",
    '.page-card-actions .btn-primary',
  ]);

  cy.wait(1500);
  cy.get('body', { timeout: 30000 }).then(($body) => {
    const otpSelector = findFirstSelector($body, [
      '#login_token',
      "input[name='otp']",
      "input[name='token']",
      "input[name='login_token']",
      "input[autocomplete='one-time-code']",
    ]);

    if (!otpSelector) return;

    cy.task('generateTotp', { otpauthUri: totpUri }).then((otpCode) => {
      const code = String(otpCode || '').trim();
      expect(code).to.match(/^\d{6}$/);
      cy.get(otpSelector, { timeout: 30000 })
        .first()
        .should('be.visible')
        .clear({ force: true })
        .type(code, { log: false });
      clickFirstAvailable([
        '#verify_token',
        "button[type='submit']",
        '.page-card-actions .btn-primary',
        'button.btn-primary',
      ]);
    });
  });

  cy.location('pathname', { timeout: 90000 }).should('match', /^\/app(\/|$)/);
}

describe('SA frontend workflow (watch mode)', () => {
  it('validates SA flow, token dialog, and workflow ticket rail', () => {
    const profileName = 'PJ7 CASHIER';

    loginWithOtp();

    cy.visit('/app/posapp');

    cy.get('body', { timeout: 60000 }).should('contain.text', 'POS');

    cy.get('body', { timeout: 60000 }).then(($body) => {
      if ($body.text().includes('multiple operational roles')) {
        throw new Error(
          'Precondition failed: cline has multiple cline-* operational roles. Set cline to SA-only (cline-Sales Associate) before running this spec.'
        );
      }
    });

    cy.contains('Role:', { timeout: 30000 }).should('be.visible');
    cy.contains('Sales Associate', { timeout: 30000 }).should('be.visible');

    // SA mode should not show cashier opening amounts table.
    cy.get('body').should('contain.text', 'cashier-only');
    cy.get('body').should('not.contain.text', 'Opening Amount');

    // Select POS Profile: PJ7 CASHIER in the opening dialog.
    cy.get('.v-dialog--active .v-autocomplete input', { timeout: 30000 })
      .eq(1)
      .click({ force: true })
      .clear({ force: true })
      .type(profileName, { force: true });

    cy.get('body').then(($body) => {
      const option = [...$body.find('.v-list-item__title')].find((el) =>
        (el.innerText || '').trim() === profileName
      );
      if (option) {
        cy.wrap(option).click({ force: true });
      } else {
        cy.get('.v-dialog--active .v-autocomplete input').eq(1).type('{enter}', { force: true });
      }
    });

    cy.contains('.v-btn', 'Submit', { timeout: 30000 }).click({ force: true });

    // POS screen loads; SA should not be able to pay.
    cy.contains('.v-btn', 'PAY', { timeout: 60000 })
      .should('be.visible')
      .and(($btn) => {
        const disabled = $btn.is(':disabled') || $btn.attr('disabled') !== undefined || $btn.hasClass('v-btn--disabled');
        expect(disabled, 'PAY button disabled for SA').to.eq(true);
      });

    // Add first available item (card or list row).
    cy.get('body', { timeout: 60000 }).then(($body) => {
      if ($body.find('.selection .v-data-table tbody tr').length > 0) {
        cy.get('.selection .v-data-table tbody tr').first().click({ force: true });
        return;
      }
      if ($body.find('.selection .v-card').length > 0) {
        cy.get('.selection .v-card').first().click({ force: true });
        return;
      }
      throw new Error('No visible item rows/cards found for SA flow test. Check PJ7 CASHIER item setup.');
    });

    cy.window().then((win) => {
      cy.stub(win, 'open').as('windowOpen');
    });

    cy.contains('.v-btn', 'Save/New', { timeout: 30000 }).click({ force: true });

    cy.contains('.v-dialog--active .v-card__title', 'Sales Order Token', { timeout: 60000 }).should('be.visible');
    cy.get('.v-dialog--active').should('contain.text', 'Customer');
    cy.get('.v-dialog--active').should('contain.text', 'Sales Associate');
    cy.get('.v-dialog--active').should('contain.text', 'Grand Total');
    cy.get('.v-dialog--active').should('contain.text', 'SO:');

    cy.contains('.v-btn', 'Print').click({ force: true });
    cy.get('@windowOpen').should('have.been.called');

    // Ticket rail visible and expandable.
    cy.get('.workflow-ticket-rail', { timeout: 30000 }).should('be.visible');
    cy.get('.workflow-ticket-rail .v-btn').first().click({ force: true });

    cy.contains('.workflow-ticket-rail-panel', 'Order Monitor', { timeout: 30000 }).should('be.visible');
    cy.get('.workflow-ticket-rail-panel').should('contain.text', 'Profile');
    cy.get('.workflow-ticket-rail-panel').should('contain.text', 'Date');
    cy.get('.workflow-ticket-rail-panel').should('contain.text', 'SA');

    // Mine filter should be available and keep a row visible once rows exist.
    cy.contains('.workflow-ticket-rail-panel .v-btn', 'Mine').click({ force: true });

    cy.get('body').then(($body) => {
      const rowExists = $body.find('.workflow-ticket-row').length > 0;
      if (rowExists) {
        cy.get('.workflow-ticket-row').first().should('contain.text', 'SA');
        cy.get('.workflow-ticket-row').first().should('contain.text', 'Total');
      } else {
        // Keep failure explicit for watch-mode debugging if backend sync/UI refresh timing misses.
        throw new Error('No workflow ticket row appeared after SA token creation. Check monitor scope/session behavior and deployed build.');
      }
    });
  });
});