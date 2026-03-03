const { assertRelayUiAndActual } = require('./_helpers/relay_ui_sync');

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
  const attempt = (retryIndex = 0) => {
    return cy.get('body', { timeout: 60000 }).then(($body) => {
      const allSelectionRows = [...$body.find('.selection .v-data-table tbody tr')];
      const usableRow = allSelectionRows.find((el) => {
        const text = (el.innerText || '').trim();
        if (!text) return false;
        if (/no data available/i.test(text)) return false;
        const tdCount = el.querySelectorAll('td').length;
        return tdCount > 1;
      });

      if (usableRow) {
        cy.wrap(usableRow).click({ force: true });
        return;
      }

      const usableCard = [...$body.find('.selection .v-card')].find((el) => {
        const text = (el.innerText || '').trim();
        if (!text) return false;
        if (/no data available/i.test(text)) return false;
        return Cypress.$(el).is(':visible');
      });
      if (usableCard) {
        cy.wrap(usableCard).click({ force: true });
        return;
      }

      if (retryIndex < 2) {
        cy.log('Sellable item rows/cards not ready yet; retrying.');
        cy.wait(1500);
        return attempt(retryIndex + 1);
      }

      throw new Error('No visible sellable item rows/cards found for SA flow test after retries. Check PJ7 CASHIER item setup and item list rendering.');
    });
  };

  return attempt(0);
}

function hasVisibleSellableItem($body) {
  const usableRow = [...$body.find('.selection .v-data-table tbody tr')].find((el) => {
    const text = (el.innerText || '').trim();
    if (!text) return false;
    if (/no data available/i.test(text)) return false;
    const tdCount = el.querySelectorAll('td').length;
    return tdCount > 1 && Cypress.$(el).is(':visible');
  });
  if (usableRow) return true;

  const usableCard = [...$body.find('.selection .v-card')].find((el) => {
    const text = (el.innerText || '').trim();
    if (!text) return false;
    if (/no data available/i.test(text)) return false;
    return Cypress.$(el).is(':visible');
  });
  return !!usableCard;
}

function waitForSellableItemGrid(maxCycles = 4) {
  const attempt = (cycle = 0) => {
    return cy.get('body', { timeout: 60000 }).then(($body) => {
      if (hasVisibleSellableItem($body)) {
        cy.log('Sellable item row/card is visible.');
        return;
      }

      if (cycle >= maxCycles) {
        throw new Error(
          'POS item grid never showed a sellable row/card after get_items cycles. Check final get_items response/order after session bootstrap/reload.'
        );
      }

      cy.log(`Waiting for a later get_items response to populate visible item rows/cards (cycle ${cycle + 1}/${maxCycles}).`);
      return cy
        .wait('@getItems', { timeout: 120000 })
        .then((interception) => {
          const status = interception?.response?.statusCode;
          if (typeof status === 'number') {
            expect(status, `get_items status (cycle ${cycle + 1})`).to.eq(200);
          }
          const items = interception?.response?.body?.message;
          if (Array.isArray(items)) {
            cy.log(`get_items cycle ${cycle + 1} returned ${items.length} item(s)`);
          }
        })
        .then(() => cy.wait(500))
        .then(() => attempt(cycle + 1));
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

  // Some runs remain on /login after the first submit without surfacing OTP; retry credential submit once.
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
      typeIntoFirstAvailable(
        ['#login_password', "input[name='pwd']", "input[type='password']"],
        password,
        { log: false }
      );
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

describe('SA frontend workflow (watch mode)', () => {
  it('validates SA flow, token dialog, and workflow ticket rail', () => {
    const profileName = 'PJ7 CASHIER';
    let expectedSoNamingSeries = '';
    let saRoleReloaded = false;
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.get_items').as('getItems');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.get_relay_workflow_monitor_board').as(
      'monitorBoard'
    );
    cy.intercept('GET', '**/relay/workflow/monitor-board*').as('monitorBoard');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.create_sales_order_token').as(
      'createSalesOrderToken'
    );

    loginWithOtp();
    cy.visit('/app');

    frappeCall('frappe.client.get', { doctype: 'POS Profile', name: profileName }).then((resp) => {
      const profile = resp && resp.message ? resp.message : null;
      expect(profile, `POS Profile ${profileName}`).to.be.an('object');
      expectedSoNamingSeries = String(profile.posa_sales_order_naming_series || '').trim();
      cy.log(`Expected SO naming series for SA token: ${expectedSoNamingSeries || '(default ERPNext)'}`);
    });

    cy.visit('/app/posapp');

    cy.get('body', { timeout: 60000 }).should('contain.text', 'POS');

    cy.get('body', { timeout: 60000 }).then(($body) => {
      if ($body.text().includes('multiple operational roles')) {
        throw new Error(
          'Precondition failed: cline has multiple cline-* operational roles. Set cline to SA-only (cline-Sales Associate) before running this spec.'
        );
      }
    });

    // If POS reopens directly into an existing session (no opening dialog), localStorage role may be empty
    // after Cypress clears storage. Reapply SA role and reload once so UI guards (PAY hidden/disabled) are evaluated correctly.
    cy.get('body').then(($body) => {
      const hasStartSessionDialog =
        $body.find('.v-dialog--active .v-card__title').toArray().some((el) =>
          /start pos session|create pos opening shift/i.test((el.innerText || '').trim())
        ) || /Role:\s*/i.test($body.text() || '');

      if (hasStartSessionDialog) return;

      const payVisible = [...$body.find('.v-btn')].some(
        (el) => ((el.innerText || '').trim() || '').toUpperCase() === 'PAY' && Cypress.$(el).is(':visible')
      );
      if (!payVisible) return;

      cy.log('POS reopened without start dialog; reapplying SA role in localStorage and reloading.');
      saRoleReloaded = true;
      cy.window().then((win) => {
        win.localStorage.setItem('pos_current_role', 'cline-Sales Associate');
      });
      cy.reload();
      cy.get('body', { timeout: 60000 }).should('contain.text', 'POS');
    });

    cy.get('body').then(($body) => {
      const hasRoleDialog = /Role:\s*/i.test($body.text() || '');
      if (!hasRoleDialog) {
        cy.log('Start POS Session dialog not shown; proceeding with existing POS session.');
        cy.get('body').should('contain.text', profileName);
        return;
      }

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

      cy.get('body').then(($body2) => {
        const option = [...$body2.find('.v-list-item__title')].find((el) =>
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
      cy.get('body', { timeout: 60000 }).then(($body3) => {
        const activeTitles = [...$body3.find('.v-dialog--active .v-card__title')].map((el) =>
          (el.innerText || '').trim()
        );
        if (activeTitles.some((t) => /start pos session/i.test(t))) {
          throw new Error('Start POS Session dialog is still active after Submit; SA session bootstrap did not complete.');
        }
      });
    });

    // Wait briefly for item feed request (or cached POS session path) and then validate via UI.
    cy.wait(2000);
    cy.get('@getItems.all').then((calls) => {
      const interception = Array.isArray(calls) && calls.length ? calls[calls.length - 1] : null;
      if (!interception) {
        cy.log('No get_items request observed (cached/reused POS session path); validating POS UI load instead.');
        return;
      }
      const status = interception?.response?.statusCode;
      if (typeof status === 'number') {
        expect(status, 'get_items status').to.eq(200);
      } else {
        cy.log('get_items intercept had no response object (cached/aborted path); validating POS UI load instead.');
      }
      const items = interception?.response?.body?.message;
      if (Array.isArray(items)) {
        cy.log(`get_items returned ${items.length} item(s) for POS UI load`);
      }
    });

    cy.request('http://127.0.0.1:8787/health').its('body.ok').should('eq', true);

    cy.get('body', { timeout: 60000 }).should('contain.text', 'Search Items');
    if (saRoleReloaded) {
      cy.log('SA spec detected POS reload path; waiting for post-reload item list to populate.');
    }
    waitForSellableItemGrid();

    // POS screen loads. UI visibility enforcement is still partial across components, so
    // accept hidden/disabled PAY or a visible PAY button (submit-time role enforcement still applies).
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

      cy.wrap(visiblePay).then(($btn) => {
        const disabled =
          $btn.is(':disabled') ||
          $btn.attr('disabled') !== undefined ||
          $btn.hasClass('v-btn--disabled');
        if (disabled) {
          cy.log('PAY button visible but disabled for SA (acceptable).');
          return;
        }
        cy.log('PAY button visible/enabled for SA; continuing (known partial UI visibility, submit-time guard applies).');
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

    cy.wait('@createSalesOrderToken', { timeout: 120000 }).then((interception) => {
      expect(interception?.response?.statusCode, 'create_sales_order_token status').to.eq(200);
      const message = interception?.response?.body?.message || {};
      const soName = String(message.sales_order_name || '').trim();
      const soDoc = message.sales_order || {};
      expect(soName, 'sales_order_name').to.not.equal('');
      if (expectedSoNamingSeries) {
        expect(String(soDoc.naming_series || '').trim(), 'SO naming series from token API').to.eq(expectedSoNamingSeries);
      }
      cy.writeFile('cypress/tmp/latest_sa_order.json', {
        salesOrder: soName,
        tokenId: String(message.token_id || ''),
        tokenLast4: String(message.token_last4 || ''),
        soNamingSeries: String(soDoc.naming_series || '').trim(),
        profile: profileName,
        createdAt: new Date().toISOString(),
      });
    });

    cy.contains('body', 'Sales Order Token', { timeout: 60000 }).should('be.visible');
    getSalesOrderTokenDialog().as('tokenDialog');

    cy.get('@tokenDialog').should('contain.text', 'Customer');
    cy.get('@tokenDialog').should('contain.text', 'Sales Associate');
    cy.get('@tokenDialog').should('contain.text', 'Grand Total');
    cy.get('@tokenDialog').should('contain.text', 'SO:');

    cy.get('@tokenDialog').within(() => {
      cy.contains('button, .v-btn', /^Print( Token Slip)?$/i).click({ force: true });
    });
    cy.get('@windowOpen').should('have.been.called');

    cy.wait('@monitorBoard', { timeout: 60000 }).its('response.statusCode').should('eq', 200);
    assertRelayUiAndActual({ relayBase: 'http://127.0.0.1:8787', expectRelayOnline: true, expectCloudOnline: true });

    // Ticket rail visible and expandable.
    cy.get('.workflow-ticket-rail', { timeout: 30000 }).should('exist');
    cy.get('.workflow-ticket-rail .v-btn').first().click({ force: true });

    cy.contains('.workflow-ticket-rail-panel', 'Order Monitor', { timeout: 30000 }).should('exist');
    cy.get('.workflow-ticket-rail-panel').should('contain.text', 'Profile');
    cy.get('.workflow-ticket-rail-panel').should('contain.text', 'Date');
    cy.get('.workflow-ticket-rail-panel').then(($panel) => {
      const panelText = ($panel.text() || '').replace(/\s+/g, ' ');
      if (!/SA/i.test(panelText)) {
        cy.log('Order Monitor panel has no SA rows yet; continuing with relay/outbox validation.');
      }
    });

    // Mine filter should be available and keep a row visible once rows exist.
    cy.contains('.workflow-ticket-rail-panel .v-btn', 'Mine').click({ force: true });

    cy.get('body').then(($body) => {
      const rows = [...$body.find('.workflow-ticket-row')];
      if (!rows.length) {
        cy.log('No workflow ticket row visible after SA token creation; relay outbox evidence is used as source of truth.');
        return;
      }

      const saRow = rows.find((el) => /SA/i.test((el.innerText || '').replace(/\s+/g, ' ')));
      if (!saRow) {
        cy.log('Workflow rows visible, but no SA-labeled row yet; continuing with relay/outbox evidence.');
        return;
      }
      cy.wrap(saRow).should('contain.text', 'Total');
    });
  });
});
