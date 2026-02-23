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
    const pwdSelector = findFirstSelector($body, ['#login_password', "input[name='pwd']", "input[type='password']"]);
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
        clickFirstAvailable([
          'button.btn-login',
          '.btn-login',
          "button[type='submit']",
          '.page-card-actions .btn-primary',
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

function submitOtpCodeWithRetry(totpUri, maxRetries = 2) {
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

          cy.wait(1500);
          cy.get('body').then(($after) => {
            const stillOnOtp = !!findFirstSelector($after, otpSelectors);
            const invalidLogin = /invalid login/i.test(($after.text() || '').trim());
            if (stillOnOtp && invalidLogin) {
              if (retryIndex >= maxRetries) {
                throw new Error('OTP verification failed after retries. Check server time and OTP secret.');
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

function frappeCall(method, args, options = {}) {
  const timeout = Number(options.timeout || 60000);
  return cy.window({ timeout: 30000 }).then({ timeout }, (win) => {
    return new Cypress.Promise((resolve, reject) => {
      win.frappe.call({
        method,
        args: args || {},
        callback: (r) => resolve(r),
        error: (err) => reject(err),
      });
    });
  });
}

function extractNumeric(text) {
  const num = parseFloat(String(text || '').replace(/[^0-9.-]/g, ''));
  return Number.isFinite(num) ? num : 0;
}

function getDisplayedTotalQty($body) {
  const totalQtyBlock = [...$body.find('.v-input')].find((el) => /total qty/i.test((el.innerText || '').trim()));
  if (!totalQtyBlock) return null;
  const input = totalQtyBlock.querySelector('input');
  if (input && typeof input.value === 'string') return extractNumeric(input.value);
  return extractNumeric(totalQtyBlock.innerText || '');
}

function ensureCartHasItem() {
  cy.get('body', { timeout: 30000 }).then(($body) => {
    const totalQty = getDisplayedTotalQty($body);
    if (totalQty !== null && totalQty > 0) return;
    throw new Error('Cart is empty. Expected Sales Order items to load into invoice.');
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
    return usable || null;
  });
}

function selectProfileInOpeningDialog(profileName) {
  cy.contains('.v-dialog--active .v-input', 'POS Profile', { timeout: 30000 })
    .find("input:not([type='hidden'])")
    .first()
    .should('be.visible')
    .click({ force: true })
    .clear({ force: true })
    .type(profileName, { force: true });

  cy.get('body').then(($body) => {
    const option = [...$body.find('.v-list-item__title')].find((el) => (el.innerText || '').trim() === profileName);
    if (option) {
      cy.wrap(option).click({ force: true });
    } else {
      cy.contains('.v-dialog--active .v-input', 'POS Profile')
        .find("input:not([type='hidden'])")
        .first()
        .type('{enter}', { force: true });
    }
  });
}

describe('Cashier frontend workflow (watch mode)', () => {
  it('validates cashier open-shift, Select S.O, payments screen, and submit preconditions', () => {
    const profileName = 'PJ7 CASHIER';
    let profileMeta = {
      custom_have_token: 0,
      custom_edge_relay_url: '',
      posa_sales_order_naming_series: '',
      posa_sales_order_lookup_max_age_days: 1,
    };
    let expectedLatestSaOrder = '';

    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.get_items').as('getItems');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.search_orders').as('searchOrders');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.create_sales_invoice_from_order').as('createInvoiceFromOrder');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.get_relay_workflow_monitor_board').as('monitorBoard');

    loginWithOtp();
    cy.visit('/app');

    cy.readFile('cypress/tmp/latest_sa_order.json', { timeout: 5000, log: true })
      .then((data) => {
        expectedLatestSaOrder = String((data && data.salesOrder) || '').trim();
        if (expectedLatestSaOrder) {
          cy.log(`Expecting newest SA order in Select S.O: ${expectedLatestSaOrder}`);
        }
      })
      .catch(() => {
        cy.log('No latest_sa_order.json found; cashier test will use first filtered SO row.');
      });

    frappeCall('frappe.client.get', { doctype: 'POS Profile', name: profileName }).then((resp) => {
      const profile = resp && resp.message ? resp.message : null;
      expect(profile, `POS Profile ${profileName}`).to.be.an('object');
      profileMeta = {
        custom_have_token: Number(profile.custom_have_token || 0),
        custom_edge_relay_url: String(profile.custom_edge_relay_url || '').trim(),
        posa_sales_order_naming_series: String(profile.posa_sales_order_naming_series || '').trim(),
        posa_sales_order_lookup_max_age_days: Number(profile.posa_sales_order_lookup_max_age_days || 1) || 1,
      };
      cy.log(
        `Cashier test env: token=${profileMeta.custom_have_token}, relayUrl=${profileMeta.custom_edge_relay_url ? 'set' : 'missing'}, soSeries=${profileMeta.posa_sales_order_naming_series || '(default)'}, soMaxAgeDays=${profileMeta.posa_sales_order_lookup_max_age_days}`
      );
    });

    cy.visit('/app/posapp');

    cy.contains('Role:', { timeout: 30000 }).should('be.visible');
    cy.contains('Cashier', { timeout: 30000 }).should('be.visible');
    cy.contains('.v-dialog--active .v-card__title', 'Create POS Opening Shift', { timeout: 30000 }).should('be.visible');
    cy.get('body').should('contain.text', 'Opening Amount');

    selectProfileInOpeningDialog(profileName);
    cy.contains('.v-dialog--active .v-btn', /submit/i, { timeout: 30000 }).click({ force: true });

    cy.contains('.v-dialog--active .v-card__title', 'Create POS Opening Shift', { timeout: 30000 }).should('not.exist');
    cy.wait('@getItems', { timeout: 120000 }).its('response.statusCode').should('eq', 200);

    cy.contains('.v-btn', 'Select S.O', { timeout: 30000 }).should('be.visible');
    cy.get('body').then(($body) => {
      const payBtn = [...$body.find('.v-btn')].find((el) => ((el.innerText || '').trim() || '').toUpperCase() === 'PAY');
      expect(payBtn, 'PAY button present for cashier').to.not.equal(undefined);
      expect(Cypress.$(payBtn).is(':visible'), 'PAY button visible for cashier').to.eq(true);
    });

    cy.get('.workflow-ticket-rail', { timeout: 30000 }).should('exist');
    cy.get('.workflow-ticket-rail .v-btn').first().click({ force: true });
    cy.contains('.workflow-ticket-rail-panel', 'Order Monitor', { timeout: 30000 }).should('exist');
    cy.wait('@monitorBoard', { timeout: 60000 }).its('response.statusCode').should('eq', 200);

    cy.contains('.v-btn', 'Select S.O', { timeout: 30000 }).click({ force: true });
    cy.contains('.v-dialog--active .headline', 'Select Sales Orders', { timeout: 30000 }).should('be.visible');
    cy.wait('@searchOrders', { timeout: 120000 }).then((interception) => {
      expect(interception?.response?.statusCode, 'search_orders status').to.eq(200);
      const rows = Array.isArray(interception?.response?.body?.message) ? interception.response.body.message : [];
      expect(rows.length, 'filtered Sales Orders returned').to.be.greaterThan(0);

      const daysBack = Number(profileMeta.posa_sales_order_lookup_max_age_days || 1) || 1;
      const threshold = new Date();
      threshold.setHours(0, 0, 0, 0);
      threshold.setDate(threshold.getDate() - daysBack);
      const thresholdStr = threshold.toISOString().slice(0, 10);

      rows.forEach((row) => {
        const txnDate = String((row && row.transaction_date) || '').trim();
        expect(txnDate, 'row.transaction_date').to.match(/^\d{4}-\d{2}-\d{2}$/);
        expect(txnDate >= thresholdStr, `Sales Order ${row.name} should be within ${daysBack} day(s)`).to.eq(true);
        if (profileMeta.posa_sales_order_naming_series) {
          expect(
            String((row && row.naming_series) || '').trim(),
            `Sales Order ${row.name} naming_series`
          ).to.eq(profileMeta.posa_sales_order_naming_series);
        }
      });

      if (expectedLatestSaOrder) {
        expect(String(rows[0]?.name || '').trim(), 'newest filtered SO should be the SA-created order').to.eq(expectedLatestSaOrder);
      }
    });

    pickFirstUsableRow('.v-dialog--active .v-data-table tbody tr').then((row) => {
      if (!row) {
        throw new Error('No selectable Sales Order rows found. Run the SA token flow first to create an order.');
      }
      const checkbox = row.querySelector('.v-simple-checkbox, [role="checkbox"], .v-input--selection-controls__ripple');
      if (checkbox) {
        cy.wrap(checkbox).click({ force: true });
      } else {
        cy.wrap(row).click({ force: true });
      }
    });

    cy.contains('.v-dialog--active .v-btn', /^Select$/i, { timeout: 30000 }).click({ force: true });
    cy.wait('@createInvoiceFromOrder', { timeout: 120000 }).its('response.statusCode').should('eq', 200);

    ensureCartHasItem();

    cy.contains('.v-btn', 'PAY', { timeout: 30000 }).click({ force: true });

    cy.get('body', { timeout: 30000 }).should('contain.text', 'Paid Amount');
    cy.get('body').should('contain.text', 'Total Amount');
    cy.contains('.v-btn', /^Submit$/i, { timeout: 30000 }).should('exist');

    cy.get('.pyments .v-btn:visible', { timeout: 30000 }).first().click({ force: true });
    cy.contains('.v-btn', /^Submit$/i, { timeout: 30000 }).click({ force: true });

    cy.get('body', { timeout: 60000 }).then(($body) => {
      const text = ($body.text() || '').replace(/\s+/g, ' ');
      const relayTokenEnabled = Number(profileMeta.custom_have_token || 0) === 1;
      const relayUrlMissing = !String(profileMeta.custom_edge_relay_url || '').trim();

      if (relayTokenEnabled && relayUrlMissing) {
        expect(
          text.includes('Relay workflow is enabled but Edge Relay URL is not configured for this POS Profile.'),
          'Expected relay URL configuration blocker for relay-enabled profile'
        ).to.eq(true);
        cy.log('Cashier submit blocked as expected: relay URL missing on relay-enabled profile.');
        return;
      }

      const relayDownBlocked = text.includes('RELAY DOWN: Offline continuity unavailable');
      const relaySuccess = text.includes('Sale committed locally. Local Sale Ref:');
      const cloudSuccess = /Invoice\s+[^\s]+\s+is\s+Submited/i.test(text);

      expect(
        relayDownBlocked || relaySuccess || cloudSuccess,
        'Expected cashier submit success or explicit relay-down blocker'
      ).to.eq(true);

      if (relaySuccess || cloudSuccess) {
        cy.wait('@monitorBoard', { timeout: 60000 }).its('response.statusCode').should('eq', 200);
        cy.get('.workflow-ticket-rail .v-btn').first().click({ force: true });
        cy.contains('.workflow-ticket-row', 'Paid', { timeout: 30000 }).should('exist');
      }
    });
  });
});
