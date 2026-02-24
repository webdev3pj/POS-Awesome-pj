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
  typeIntoFirstAvailable(['#login_password', "input[name='pwd']", "input[type='password']"], password, {
    log: false,
  });
  clickLoginSubmitNearPassword();

  const maybeCompleteOtp = () => {
    cy.wait(1500);
    return cy.get('body', { timeout: 30000 }).then(($body) => {
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
  };

  maybeCompleteOtp();

  cy.location('pathname', { timeout: 5000 }).then((pathname) => {
    if (/^\/app(\/|$)/.test(String(pathname || ''))) return;

    cy.get('body').then(($body) => {
      const stillOnLoginForm =
        !!findFirstSelector($body, ['#login_email', "input[name='usr']", "input[name='login_email']", "input[type='email']"]) &&
        !!findFirstSelector($body, ['#login_password', "input[name='pwd']", "input[type='password']"]);

      if (!stillOnLoginForm) return;

      cy.log('Login submit did not advance on first attempt; retrying once.');
      typeIntoFirstAvailable(
        ['#login_email', "input[name='usr']", "input[name='login_email']", "input[type='email']"],
        username
      );
      typeIntoFirstAvailable(['#login_password', "input[name='pwd']", "input[type='password']"], password, {
        log: false,
      });
      clickLoginSubmitNearPassword();
      maybeCompleteOtp();
    });
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

function verifyRelayCommitRecordedOnLocalRelay(localSaleRef) {
  const encodedRef = encodeURIComponent(String(localSaleRef || '').trim());
  expect(encodedRef, 'encoded local_sale_ref').to.not.equal('');

  cy.request({
    method: 'GET',
    url: `http://127.0.0.1:8787/api/transactions/${encodedRef}`,
    timeout: 60000,
  }).then((resp) => {
    expect(resp.status, 'relay /api/transactions/<local_sale_ref> status').to.eq(200);
    const body = resp.body || {};
    expect(body.ok, 'relay transaction detail ok').to.eq(true);
    expect(String(body?.sale?.local_sale_ref || '').trim(), 'relay sale.local_sale_ref').to.eq(String(localSaleRef).trim());
    expect(String(body?.sale?.sale_status || '').trim(), 'relay sale_status').to.eq('SALE_COMMITTED_LOCAL');
    expect(['SALE_SYNC_PENDING', 'SALE_SYNCED_SI_SUBMITTED']).to.include(
      String(body?.sale?.cloud_sync_status || '').trim(),
      'relay cloud_sync_status'
    );

    const outboxEvents = Array.isArray(body.outbox_events) ? body.outbox_events : [];
    const saleCommittedOutbox = outboxEvents.find(
      (row) =>
        String(row?.event_type || '').trim() === 'SALE_COMMITTED' &&
        String(row?.local_ref || '').trim() === String(localSaleRef).trim()
    );
    expect(!!saleCommittedOutbox, 'SALE_COMMITTED outbox event exists for local_sale_ref').to.eq(true);
  });

  cy.request({
    method: 'GET',
    url: 'http://127.0.0.1:8787/api/outbox',
    timeout: 60000,
  }).then((resp) => {
    expect(resp.status, 'relay /api/outbox status').to.eq(200);
    const rows = Array.isArray(resp.body?.rows) ? resp.body.rows : [];
    const matched = rows.find((row) => String(row?.local_ref || '').trim() === String(localSaleRef).trim());
    expect(!!matched, 'relay outbox row exists for local_sale_ref').to.eq(true);
    expect(['queued', 'processing', 'done']).to.include(String(matched?.status || '').trim(), 'relay outbox status');
  });

  cy.request({
    method: 'GET',
    url: 'http://127.0.0.1:8787/api/queue',
    timeout: 60000,
  }).then((resp) => {
    expect(resp.status, 'relay /api/queue status').to.eq(200);
    expect(resp.body, 'relay /api/queue payload').to.have.property('counts');
  });

  cy.request({
    method: 'GET',
    url: `http://127.0.0.1:8787/?tx_pos_profile=${encodeURIComponent('PJ7 CASHIER')}&tx_search=${encodedRef}&tx_limit=20`,
    timeout: 60000,
  }).then((resp) => {
    expect(resp.status, 'relay dashboard UI status').to.eq(200);
    const html = String(resp.body || '');
    expect(html, 'relay dashboard title').to.include('POS Relay Dashboard');
    expect(html, 'relay dashboard transaction timeline section').to.include('Transaction Timeline (Local Sales)');
    expect(html, 'relay dashboard local_sale_ref visible').to.include(String(localSaleRef).trim());
    expect(html, 'relay dashboard POS profile visible').to.include('PJ7 CASHIER');
    expect(
      html.includes('SALE_SYNC_PENDING') || html.includes('SALE_SYNCED_SI_SUBMITTED'),
      'relay dashboard cloud sync status visible'
    ).to.eq(true);
    expect(html, 'relay dashboard pick status visible').to.include('PAID_PENDING_PICK');
  });
}

function clickVisiblePaymentSubmitButton() {
  cy.get('body', { timeout: 30000 }).then(($body) => {
    const submitBtn = [...$body.find('.v-btn')].find((el) => {
      const text = ((el.innerText || '').trim() || '').toUpperCase();
      if (text !== 'SUBMIT') return false;
      if (!Cypress.$(el).is(':visible')) return false;
      const cardText = String((el.closest('.v-card') && el.closest('.v-card').innerText) || '');
      return /SUBMIT\s*&\s*PRINT/i.test(cardText) && /CANCEL PAYMENT/i.test(cardText);
    });
    expect(submitBtn, 'visible payment Submit button').to.not.equal(undefined);
    cy.wrap(submitBtn).click({ force: true });
  });
}

function closeOrderMonitorPanelIfOpen() {
  cy.get('body').then(($body) => {
    const panel = $body.find('.workflow-ticket-rail-panel:visible').get(0);
    if (!panel) return;
    const closeBtn =
      panel.querySelector('.workflow-ticket-rail-header .v-btn') ||
      panel.querySelector('.mdi-close')?.closest('button');
    if (closeBtn) {
      cy.wrap(closeBtn).click({ force: true });
      cy.get('.workflow-ticket-rail-panel:visible', { timeout: 10000 }).should('not.exist');
    }
  });
}

function waitForNewRelaySaleAfterBaseline({
  beforeCount,
  posProfile = 'PJ7 CASHIER',
  minTotal = 0,
  maxRetries = 12,
  delayMs = 1500,
}) {
  const attempt = (retryIndex = 0) => {
    return cy
      .request({
        method: 'GET',
        url: `http://127.0.0.1:8787/api/transactions?pos_profile_id=${encodeURIComponent(posProfile)}&limit=20`,
        timeout: 60000,
      })
      .then((resp) => {
        expect(resp.status, 'relay /api/transactions status').to.eq(200);
        const body = resp.body || {};
        const rows = Array.isArray(body.rows) ? body.rows : [];
        const count = Number(body.count || rows.length || 0);

        const candidate = rows.find((row) => {
          const total = Number(row?.total || 0);
          return total >= Number(minTotal || 0) && String(row?.pos_profile_id || '').trim() === posProfile;
        });

        if (count > Number(beforeCount || 0) && candidate) {
          return {
            count,
            row: candidate,
          };
        }

        if (retryIndex >= maxRetries) {
          throw new Error(
            `No new relay local sale appeared after cashier submit (beforeCount=${beforeCount}, currentCount=${count}).`
          );
        }

        cy.log(
          `Waiting for new relay local sale row (retry ${retryIndex + 1}/${maxRetries}); count=${count}, before=${beforeCount}`
        );
        cy.wait(delayMs);
        return attempt(retryIndex + 1);
      });
  };

  return attempt(0);
}

function waitForCartHasItem(maxRetries = 6, delayMs = 1000) {
  const attempt = (retryIndex = 0) => {
    return cy.get('body', { timeout: 30000 }).then(($body) => {
      const totalQty = getDisplayedTotalQty($body);
      if (totalQty !== null && totalQty > 0) {
        cy.log(`Cart populated from selected Sales Order (total qty ${totalQty}).`);
        return;
      }

      if (retryIndex >= maxRetries) {
        throw new Error(
          'Cart stayed empty after create_sales_invoice_from_order. Expected Sales Order items to load into invoice.'
        );
      }

      cy.log(`Waiting for invoice lines from selected Sales Order (retry ${retryIndex + 1}/${maxRetries}).`);
      cy.wait(delayMs);
      return attempt(retryIndex + 1);
    });
  };

  return attempt(0);
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
      paymentModeNames: [],
      defaultPaymentModeName: '',
    };
    let expectedLatestSaOrder = '';
    let relayCommitLocalSaleRef = '';
    let relayTxCountBeforeSubmit = 0;

    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.get_items').as('getItems');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.search_orders').as('searchOrders');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.create_sales_invoice_from_order').as('createInvoiceFromOrder');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.get_relay_workflow_monitor_board').as('monitorBoard');

    loginWithOtp();
    cy.visit('/app');

    cy.readFile('cypress/tmp/latest_sa_order.json', { timeout: 5000, log: true, failOnNonExistent: false }).then((data) => {
      if (!data) {
        cy.log('No latest_sa_order.json found; cashier test will use first filtered SO row.');
        return;
      }
      expectedLatestSaOrder = String((data && data.salesOrder) || '').trim();
      if (expectedLatestSaOrder) {
        cy.log(`Expecting newest SA order in Select S.O: ${expectedLatestSaOrder}`);
      }
    });

    frappeCall('frappe.client.get', { doctype: 'POS Profile', name: profileName }).then((resp) => {
      const profile = resp && resp.message ? resp.message : null;
      expect(profile, `POS Profile ${profileName}`).to.be.an('object');
      profileMeta = {
        custom_have_token: Number(profile.custom_have_token || 0),
        custom_edge_relay_url: String(profile.custom_edge_relay_url || '').trim(),
        posa_sales_order_naming_series: String(profile.posa_sales_order_naming_series || '').trim(),
        posa_sales_order_lookup_max_age_days: Number(profile.posa_sales_order_lookup_max_age_days || 1) || 1,
        paymentModeNames: Array.isArray(profile.payments)
          ? profile.payments.map((row) => String(row?.mode_of_payment || '').trim()).filter(Boolean)
          : [],
        defaultPaymentModeName:
          (
            (Array.isArray(profile.payments) ? profile.payments : []).find((row) => Number(row?.default || 0) === 1) || {}
          ).mode_of_payment || '',
      };
      cy.log(
        `Cashier test env: token=${profileMeta.custom_have_token}, relayUrl=${profileMeta.custom_edge_relay_url ? 'set' : 'missing'}, soSeries=${profileMeta.posa_sales_order_naming_series || '(default)'}, soMaxAgeDays=${profileMeta.posa_sales_order_lookup_max_age_days}, paymentModes=${profileMeta.paymentModeNames.length}`
      );
    });

    cy.visit('/app/posapp');

    cy.get('body', { timeout: 60000 }).should('contain.text', 'POS');

    cy.get('body').then(($body) => {
      const hasRoleDialog = /Role:\s*/i.test($body.text() || '');
      if (!hasRoleDialog) {
        cy.log('Cashier opening dialog not shown; proceeding with existing POS session.');
        cy.get('body').should('contain.text', profileName);
        return;
      }

      cy.contains('Role:', { timeout: 30000 }).should('be.visible');
      cy.contains('Cashier', { timeout: 30000 }).should('be.visible');
      cy.contains('.v-dialog--active .v-card__title', 'Create POS Opening Shift', { timeout: 30000 }).should('be.visible');
      cy.get('body').should('contain.text', 'Opening Amount');

      selectProfileInOpeningDialog(profileName);
      cy.contains('.v-dialog--active .v-btn', /submit/i, { timeout: 30000 }).click({ force: true });

      cy.contains('.v-dialog--active .v-card__title', 'Create POS Opening Shift', { timeout: 30000 }).should('not.exist');
    });

    cy.wait('@getItems', { timeout: 120000 }).then((interception) => {
      const status = interception?.response?.statusCode;
      if (typeof status === 'number') {
        expect(status, 'get_items status').to.eq(200);
      } else {
        cy.log('get_items intercept had no response object (cached/aborted path); validating POS UI load instead.');
      }
    });

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
      const reqBody = interception?.request?.body;
      let sentPosProfile = '';
      if (reqBody && typeof reqBody === 'object') {
        sentPosProfile = String(reqBody.pos_profile || reqBody?.args?.pos_profile || '').trim();
      } else if (typeof reqBody === 'string') {
        try {
          const params = new URLSearchParams(reqBody);
          sentPosProfile = String(params.get('pos_profile') || '').trim();
        } catch (e) {
          sentPosProfile = '';
        }
      }
      expect(
        sentPosProfile,
        'search_orders request must include pos_profile (frontend asset must be updated)'
      ).to.eq(profileName);

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
      const rowEl = row && row.jquery ? row.get(0) : row;
      const checkbox =
        rowEl && typeof rowEl.querySelector === 'function'
          ? rowEl.querySelector('.v-simple-checkbox, [role="checkbox"], .v-input--selection-controls__ripple')
          : Cypress.$(row).find('.v-simple-checkbox, [role="checkbox"], .v-input--selection-controls__ripple').get(0);
      if (checkbox) {
        cy.wrap(checkbox).click({ force: true });
      } else {
        cy.wrap(rowEl || row).click({ force: true });
      }
    });

    cy.contains('.v-dialog--active .v-btn', /^Select$/i, { timeout: 30000 }).click({ force: true });
    cy.wait('@createInvoiceFromOrder', { timeout: 120000 }).its('response.statusCode').should('eq', 200);
    cy.contains('.v-dialog--active .headline', 'Select Sales Orders', { timeout: 30000 }).should('not.exist');

    waitForCartHasItem();
    ensureCartHasItem();

    cy.contains('.v-btn', 'PAY', { timeout: 30000 }).click({ force: true });

    cy.get('body', { timeout: 30000 }).should('contain.text', 'Paid Amount');
    cy.get('body').should('contain.text', 'Total Amount');
    cy.contains('.v-btn', /^Submit$/i, { timeout: 30000 }).should('exist');

    cy.get('body').then(($body) => {
      const totalToBePaidInput = [...$body.find('input')].find((el) => {
        const wrap = el.closest('.v-input');
        return wrap && /to be paid/i.test((wrap.innerText || '').trim());
      });
      const paidAmountInput = [...$body.find('input')].find((el) => {
        const wrap = el.closest('.v-input');
        return wrap && /paid amount/i.test((wrap.innerText || '').trim());
      });

      if (totalToBePaidInput && paidAmountInput) {
        const totalValue = String(totalToBePaidInput.value || '').trim();
        cy.wrap(paidAmountInput).clear({ force: true }).type(totalValue || '0', { force: true });
      } else {
        cy.log('Could not resolve Paid Amount/To Be Paid inputs; proceeding with current payment values.');
      }
    });

    cy.get('body').then(($body) => {
      const visiblePaymentButtons = $body
        .find('.pyments .v-btn:visible, .v-btn.pyments:visible, .pyments.v-btn:visible')
        .toArray();
      const visiblePaymentLabels = visiblePaymentButtons
        .map((el) => String(el.innerText || '').trim())
        .filter(Boolean);

      expect(visiblePaymentButtons.length, 'visible payment mode buttons on payment screen').to.be.greaterThan(0);

      if (Array.isArray(profileMeta.paymentModeNames) && profileMeta.paymentModeNames.length) {
        profileMeta.paymentModeNames.forEach((modeName) => {
          expect(
            visiblePaymentLabels.includes(modeName),
            `payment mode button visible: ${modeName}`
          ).to.eq(true);
        });
      }

      const preferredModeName = String(profileMeta.defaultPaymentModeName || '').trim();
      const preferredBtn =
        (preferredModeName && visiblePaymentButtons.find((el) => String(el.innerText || '').trim() === preferredModeName)) ||
        visiblePaymentButtons[0];
      expect(preferredBtn, 'clickable payment mode button').to.not.equal(undefined);
      cy.wrap(preferredBtn).click({ force: true });
    });

    cy.request({
      method: 'GET',
      url: `http://127.0.0.1:8787/api/transactions?pos_profile_id=${encodeURIComponent(profileName)}&limit=200`,
      timeout: 60000,
    }).then((resp) => {
      expect(resp.status, 'relay baseline /api/transactions status').to.eq(200);
      relayTxCountBeforeSubmit = Number(resp.body?.count || (Array.isArray(resp.body?.rows) ? resp.body.rows.length : 0) || 0);
      cy.log(`Relay baseline transaction count for ${profileName}: ${relayTxCountBeforeSubmit}`);
    });

    closeOrderMonitorPanelIfOpen();
    clickVisiblePaymentSubmitButton();

    cy.get('body', { timeout: 60000 }).then(($body) => {
      const text = ($body.text() || '').replace(/\s+/g, ' ');
      const relayTokenEnabled = Number(profileMeta.custom_have_token || 0) === 1;
      const relayUrlMissing = !String(profileMeta.custom_edge_relay_url || '').trim();
      const amountNotComplete = text.includes('The amount paid is not complete');

      if (relayTokenEnabled && relayUrlMissing) {
        const relayUrlMissingBlocked =
          text.includes('Relay workflow is enabled but Edge Relay URL is not configured for this POS Profile.') ||
          text.includes('Edge Relay URL is not configured on this POS Profile.');
        if (amountNotComplete) {
          cy.log('Cashier flow reached payment submit validation; amount completion blocked submit before relay URL validation.');
          return;
        }
        expect(
          relayUrlMissingBlocked,
          'Expected relay URL configuration blocker for relay-enabled profile'
        ).to.eq(true);
        cy.log('Cashier submit blocked as expected: relay URL missing on relay-enabled profile.');
        return;
      }

      const relayDownBlocked = text.includes('RELAY DOWN: Offline continuity unavailable');
      const relaySuccess = text.includes('Sale committed locally. Local Sale Ref:');
      const cloudSuccess = /Invoice\s+[^\s]+\s+is\s+Submited/i.test(text);

      expect(
        amountNotComplete || relayDownBlocked || relaySuccess || cloudSuccess,
        'Expected cashier submit success or explicit relay-down blocker'
      ).to.eq(true);

      if (relaySuccess || cloudSuccess) {
        cy.wait('@monitorBoard', { timeout: 60000 }).its('response.statusCode').should('eq', 200);
        cy.get('.workflow-ticket-rail .v-btn').first().click({ force: true });
        cy.contains('.workflow-ticket-row', 'Paid', { timeout: 30000 }).should('exist');
      }
    });

    cy.then(() => {
      return waitForNewRelaySaleAfterBaseline({
        beforeCount: relayTxCountBeforeSubmit,
        posProfile: profileName,
        minTotal: 1,
      }).then(({ row }) => {
        relayCommitLocalSaleRef = String(row?.local_sale_ref || '').trim();
        expect(relayCommitLocalSaleRef, 'local_sale_ref from relay /api/transactions').to.not.equal('');
        expect(String(row?.sale_status || '').trim(), 'relay local sale status').to.eq('SALE_COMMITTED_LOCAL');
        expect(['SALE_SYNC_PENDING', 'SALE_SYNCED_SI_SUBMITTED']).to.include(
          String(row?.cloud_sync_status || '').trim(),
          'relay local sale cloud_sync_status'
        );
        cy.writeFile('cypress/tmp/latest_cashier_relay_commit.json', {
          localSaleRef: relayCommitLocalSaleRef,
          relaySaleRow: row,
          createdAt: new Date().toISOString(),
        });
      });
    });

    cy.then(() => {
      expect(relayCommitLocalSaleRef, 'local_sale_ref captured from local relay transaction API').to.not.equal('');
      verifyRelayCommitRecordedOnLocalRelay(relayCommitLocalSaleRef);
    });
  });
});
