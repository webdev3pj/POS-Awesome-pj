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

function clickLoginSubmitNearPassword() {
  return cy.get('body', { timeout: 30000 }).then(($body) => {
    const pwdSelector = findFirstSelector($body, ["#login_password", "input[name='pwd']", "input[type='password']"]);
    expect(pwdSelector, 'password field selector').to.be.a('string');

    cy.get(pwdSelector, { timeout: 30000 })
      .first()
      .should('be.visible')
      .then(($pwd) => {
        const $form = $pwd.closest('form');
        if ($form.length) {
          const loginBtn = $form.find('button, .btn').filter((_, el) => /^login$/i.test((el.innerText || '').trim()));
          if (loginBtn.length) {
            cy.wrap(loginBtn[0]).click({ force: true });
            return;
          }
        }

        // Fallback for custom login layouts that do not wrap inputs in a form.
        clickFirstAvailable([
          "button.btn-login",
          ".btn-login",
          "button[type='submit']",
          ".page-card-actions .btn-primary",
        ]);
      });
  });
}

function waitForSafeTotpWindow(minRemainingSeconds = 6) {
  return cy.window({ timeout: 30000 }).then((win) => {
    const nowSec = Math.floor(win.Date.now() / 1000);
    const secIntoWindow = nowSec % 30;
    const remaining = 30 - secIntoWindow;
    if (remaining <= minRemainingSeconds) {
      const waitMs = (remaining + 1) * 1000;
      cy.log(`Waiting ${waitMs}ms for next TOTP window`);
      cy.wait(waitMs);
    }
  });
}

function submitOtpCodeWithRetry(totpUri, maxRetries = 1) {
  const otpSelectors = [
    '#login_token',
    "input[name='otp']",
    "input[name='token']",
    "input[name='login_token']",
    "input[autocomplete='one-time-code']",
  ];
  const verifySelectors = [
    '#verify_token',
    "button[type='submit']",
    '.page-card-actions .btn-primary',
    'button.btn-primary',
  ];

  const attempt = (retryIndex = 0) => {
    return cy.get('body', { timeout: 30000 }).then(($body) => {
      const otpSelector = findFirstSelector($body, otpSelectors);
      if (!otpSelector) return;

      return waitForSafeTotpWindow().then(() =>
        cy.task('generateTotp', { otpauthUri: totpUri }).then((otpCode) => {
        const code = String(otpCode || '').trim();
        expect(code, 'generated OTP code').to.match(/^\d{6}$/);

        cy.get(otpSelector, { timeout: 30000 })
          .first()
          .should('be.visible')
          .clear({ force: true })
          .type(code, { log: false });

        clickFirstAvailable(verifySelectors);

        // If server rejects an OTP at the code boundary, retry once with a fresh code.
        cy.wait(1500);
        cy.get('body').then(($after) => {
          const stillOnOtp = !!findFirstSelector($after, otpSelectors);
          const invalidLogin = /invalid login/i.test(($after.text() || '').trim());
          if (stillOnOtp && invalidLogin) {
            if (retryIndex >= maxRetries) {
              throw new Error('OTP verification failed after retry. Check server time and OTP secret.');
            }
            cy.log('OTP rejected; waiting for next TOTP window before retry');
            cy.wait(31000);
            return attempt(retryIndex + 1);
          }
        });
        })
      );
    });
  };

  return attempt(0);
}

function getSalesOrderTokenDialog() {
  return cy.get('body', { timeout: 60000 }).then(($body) => {
    const visibleFrappeModal = [...$body.find('.modal.show, .modal.in')].find((el) =>
      /sales order token/i.test((el.innerText || '').trim())
    );
    if (visibleFrappeModal) {
      return cy.wrap(visibleFrappeModal);
    }

    const visibleVuetifyDialog = [...$body.find('.v-dialog--active')].find((el) =>
      /sales order token/i.test((el.innerText || '').trim())
    );
    if (visibleVuetifyDialog) {
      return cy.wrap(visibleVuetifyDialog);
    }

    throw new Error('Sales Order Token dialog was not found (neither Frappe modal nor Vuetify dialog).');
  });
}

function pickFirstUsableRow(selector) {
  return cy.get(selector, { timeout: 60000 }).then(($rows) => {
    const usable = [...$rows].find((el) => {
      const text = (el.innerText || '').trim();
      if (!text) return false;
      if (/no data available/i.test(text)) return false;
      const tdCount = el.querySelectorAll('td').length;
      return tdCount > 1;
    });
    if (!usable) return null;
    return cy.wrap(usable);
  });
}

function extractNumeric(text) {
  const num = parseFloat(String(text || '').replace(/[^0-9.-]/g, ''));
  return Number.isFinite(num) ? num : 0;
}

function getDisplayedTotalQty($body) {
  const totalQtyBlock = [...$body.find('.v-input')].find((el) =>
    /total qty/i.test((el.innerText || '').trim())
  );
  if (!totalQtyBlock) return null;
  const input = totalQtyBlock.querySelector('input');
  if (input && typeof input.value === 'string') return extractNumeric(input.value);
  return extractNumeric(totalQtyBlock.innerText || '');
}

function ensureCartHasItem() {
  cy.get('body', { timeout: 30000 }).then(($body) => {
    const totalQty = getDisplayedTotalQty($body);
    if (totalQty !== null && totalQty > 0) return;
    throw new Error('Cart is still empty after item click. Item row click did not add item to invoice.');
  });
}

function cartHasItemNow() {
  return cy.get('body').then(($body) => {
    const totalQty = getDisplayedTotalQty($body);
    return totalQty !== null && totalQty > 0;
  });
}

function clickFirstSellableItem() {
  return cy.get('body', { timeout: 60000 }).then(($body) => {
    if ($body.find('.selection .v-data-table tbody tr').length > 0) {
      return pickFirstUsableRow('.selection .v-data-table tbody tr').then((row) => {
        if (!row) {
          throw new Error('Item table rows are present but no usable item row found (only placeholders).');
        }
        cy.wrap(row).click({ force: true });
      });
    }
    if ($body.find('.selection .v-card').length > 0) {
      return cy.get('.selection .v-card').first().click({ force: true });
    }
    throw new Error('No visible item rows/cards found for SA flow test. Check PJ7 CASHIER item setup.');
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
  clickLoginSubmitNearPassword();

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
    return submitOtpCodeWithRetry(totpUri, 2);
  });

  cy.location('pathname', { timeout: 90000 }).should('match', /^\/app(\/|$)/);
}

describe('SA frontend workflow (watch mode)', () => {
  it('validates SA flow, token dialog, and workflow ticket rail', () => {
    const profileName = 'PJ7 CASHIER';
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.get_items').as('getItems');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.get_relay_workflow_monitor_board').as(
      'monitorBoard'
    );

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
    cy.contains('.v-dialog--active .v-input', 'POS Profile', { timeout: 30000 })
      .find("input:not([type='hidden'])")
      .first()
      .should('be.visible')
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
        cy.contains('.v-dialog--active .v-input', 'POS Profile')
          .find("input:not([type='hidden'])")
          .first()
          .type('{enter}', { force: true });
      }
    });

    // Submit the SA no-cash start-session dialog (Vuetify renders button text uppercase).
    cy.contains('.v-dialog--active .v-btn', /submit/i, { timeout: 30000 }).click({ force: true });

    // Ensure the start-session dialog has closed before interacting with the POS screen.
    cy.contains('.v-dialog--active .v-card__title', 'Start POS Session', { timeout: 30000 }).should('not.exist');
    cy.get('body', { timeout: 60000 }).then(($body) => {
      const activeTitles = [...$body.find('.v-dialog--active .v-card__title')].map((el) =>
        (el.innerText || '').trim()
      );
      if (activeTitles.some((t) => /start pos session/i.test(t))) {
        throw new Error('Start POS Session dialog is still active after Submit; SA session bootstrap did not complete.');
      }
    });

    // Wait for item feed to load after SA session starts.
    cy.wait('@getItems', { timeout: 120000 }).then((interception) => {
      const status = interception?.response?.statusCode;
      expect(status, 'get_items status').to.eq(200);
      const items = interception?.response?.body?.message;
      if (Array.isArray(items)) {
        cy.log(`get_items returned ${items.length} item(s) for POS UI load`);
      }
    });

    // POS screen loads; SA should not be able to pay.
    // Accept either hidden PAY button or visible-but-disabled PAY button.
    cy.get('body', { timeout: 60000 }).then(($body) => {
      const payButtons = [...$body.find('.v-btn')].filter((el) =>
        ((el.innerText || '').trim() || '').toUpperCase() === 'PAY'
      );

      if (!payButtons.length) {
        cy.log('PAY button not present for SA (acceptable).');
        return;
      }

      const visiblePay = payButtons.find((el) => Cypress.$(el).is(':visible'));
      if (!visiblePay) {
        cy.log('PAY button hidden for SA (acceptable).');
        return;
      }

      cy.wrap(visiblePay).should(($btn) => {
        const disabled =
          $btn.is(':disabled') ||
          $btn.attr('disabled') !== undefined ||
          $btn.hasClass('v-btn--disabled');
        expect(disabled, 'PAY button disabled for SA').to.eq(true);
      });
    });

    // Add first available item (card or list row); retry once with a double-click fallback.
    clickFirstSellableItem();

    cy.wait(500);
    cartHasItemNow().then((hasItem) => {
      if (!hasItem) {
        cy.log('First item click did not add to cart; retrying with double click.');
        cy.get('body').then(($body2) => {
          if ($body2.find('.selection .v-data-table tbody tr').length > 0) {
            pickFirstUsableRow('.selection .v-data-table tbody tr').then((row) => {
              if (!row) {
                throw new Error('No usable item row found for retry (item list appears empty or placeholder-only).');
              }
              cy.wrap(row).dblclick({ force: true });
            });
            return;
          }
          if ($body2.find('.selection .v-card').length > 0) {
            cy.get('.selection .v-card').first().dblclick({ force: true });
            return;
          }
        });
      }
    });

    cy.wait(500);
    ensureCartHasItem();

    cy.window().then((win) => {
      const fakePrintWindow = {
        document: {
          write() {},
          close() {},
        },
        focus() {},
        print() {},
      };
      cy.stub(win, 'open').callsFake(() => fakePrintWindow).as('windowOpen');
    });

    cy.contains('.v-btn', 'Save/New', { timeout: 30000 }).click({ force: true });

    cy.contains('body', 'Sales Order Token', { timeout: 60000 }).should('be.visible');
    getSalesOrderTokenDialog().as('tokenDialog');

    cy.get('@tokenDialog').should('contain.text', 'Customer');
    cy.get('@tokenDialog').should('contain.text', 'Sales Associate');
    cy.get('@tokenDialog').should('contain.text', 'Grand Total');
    cy.get('@tokenDialog').should('contain.text', 'SO:');

    cy.get('@tokenDialog').within(() => {
      cy.contains('button, .v-btn', /^Print$/i).click({ force: true });
    });
    cy.get('@windowOpen').should('have.been.called');

    cy.wait('@monitorBoard', { timeout: 60000 }).its('response.statusCode').should('eq', 200);

    // Ticket rail visible and expandable.
    cy.get('.workflow-ticket-rail', { timeout: 30000 }).should('exist');
    cy.get('.workflow-ticket-rail .v-btn').first().click({ force: true });

    cy.contains('.workflow-ticket-rail-panel', 'Order Monitor', { timeout: 30000 }).should('exist');
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
