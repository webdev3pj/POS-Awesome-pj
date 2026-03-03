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

function parseLabelFromOtpUri(uri) {
  try {
    const text = String(uri || '');
    const marker = 'otpauth://totp/';
    const idx = text.indexOf(marker);
    if (idx === -1) return '';
    const after = text.slice(idx + marker.length);
    const pathPart = after.split('?')[0] || '';
    const decoded = decodeURIComponent(pathPart);
    const label = decoded.includes(':') ? decoded.split(':').slice(1).join(':') : decoded;
    return (label || '').trim();
  } catch (_e) {
    return '';
  }
}

function setField(doctype, name, fieldname, value) {
  return frappeCall('frappe.client.set_value', {
    doctype,
    name,
    fieldname,
    value,
  });
}

function getCandidateOperationalRole(clineRoles, target) {
  const normalized = String(target || '').toLowerCase();
  if (normalized === 'sales-associate') {
    return (
      clineRoles.find((r) => r === 'cline-Sales Associate') ||
      clineRoles.find((r) => r.toLowerCase() === 'cline-sales associate') ||
      clineRoles.find((r) => {
        const text = r.toLowerCase();
        return text.includes('sales') && text.includes('associate');
      }) ||
      ''
    );
  }
  if (normalized === 'cashier') {
    return (
      clineRoles.find((r) => r === 'cline-Cashier') ||
      clineRoles.find((r) => r.toLowerCase() === 'cline-cashier') ||
      clineRoles.find((r) => r.toLowerCase().includes('cashier')) ||
      ''
    );
  }
  return '';
}

function resolveTargetUserDocname() {
  const loginUser = String(Cypress.env('username') || '').trim();
  const explicitUserDocname = String(Cypress.env('userDocname') || '').trim();
  const otpLabelCandidate = parseLabelFromOtpUri(Cypress.env('totpUri'));

  return frappeCall('frappe.client.get_list', {
    doctype: 'User',
    fields: ['name', 'email', 'username', 'enabled'],
    limit_page_length: 200,
    filters: { enabled: 1 },
  }).then((resp) => {
    const users = Array.isArray(resp && resp.message) ? resp.message : [];
    const candidates = [
      explicitUserDocname,
      loginUser,
      otpLabelCandidate,
      loginUser.includes('@') ? loginUser.split('@')[0] : '',
    ]
      .map((v) => String(v || '').trim())
      .filter(Boolean);

    const targetUser =
      users.find((u) =>
        candidates.some(
          (c) =>
            String(u.name || '').trim() === c ||
            String(u.email || '').trim() === c ||
            String(u.username || '').trim() === c
        )
      ) || null;

    expect(targetUser, `resolve User record for candidates: ${candidates.join(', ')}`).to.not.equal(null);
    return String(targetUser.name || '').trim();
  });
}

function resolveOperationalRole(target) {
  return frappeCall('frappe.client.get_list', {
    doctype: 'Role',
    fields: ['name'],
    limit_page_length: 1000,
  }).then((resp) => {
    const roleRows = Array.isArray(resp && resp.message) ? resp.message : [];
    const clineRoles = roleRows
      .map((r) => String((r && r.name) || '').trim())
      .filter((name) => name.startsWith('cline-'));
    const resolved = getCandidateOperationalRole(clineRoles, target);
    expect(resolved, `resolve cline role for ${target} from ${clineRoles.join(', ')}`).to.not.equal('');
    return resolved;
  });
}

function setOnlyOperationalRole(targetUserDocname, targetOperationalRole) {
  return frappeCall('frappe.client.get', {
    doctype: 'User',
    name: targetUserDocname,
  }).then((getResp) => {
    const doc = getResp && getResp.message ? getResp.message : null;
    expect(doc, 'User doc loaded').to.be.an('object');

    const existingRoles = Array.isArray(doc.roles) ? doc.roles : [];
    const preservedNonClineRoles = existingRoles.filter(
      (r) => !String((r && r.role) || '').startsWith('cline-')
    );
    const existingTarget = existingRoles.find(
      (r) => String((r && r.role) || '') === targetOperationalRole
    );

    const rebuiltRoles = [...preservedNonClineRoles];
    if (existingTarget) {
      rebuiltRoles.push(existingTarget);
    } else {
      rebuiltRoles.push({
        doctype: 'Has Role',
        parent: doc.name,
        parenttype: 'User',
        parentfield: 'roles',
        role: targetOperationalRole,
      });
    }

    return frappeCall('frappe.client.save', {
      doc: {
        ...doc,
        roles: rebuiltRoles,
        __unsaved: 1,
      },
    });
  }).then((saveResp) => {
    const saved = saveResp && saveResp.message ? saveResp.message : null;
    expect(saved, 'Saved User doc response').to.be.an('object');
    const clineRoles = (Array.isArray(saved.roles) ? saved.roles : [])
      .map((r) => String((r && r.role) || ''))
      .filter((r) => r.startsWith('cline-'));
    expect(clineRoles, 'remaining cline-* roles').to.deep.equal([targetOperationalRole]);
    cy.log(`Operational role now: ${targetOperationalRole}`);
  });
}

function ensureProfileConfigured(profileName) {
  return frappeCall('frappe.client.get', {
    doctype: 'POS Profile',
    name: profileName,
  }).then((profileResp) => {
    const profile = profileResp && profileResp.message ? profileResp.message : null;
    expect(profile, `POS Profile ${profileName} exists`).to.be.an('object');

    const requiredFlags = [
      ['custom_have_token', 1],
      ['posa_allow_sales_order', 1],
      ['custom_allow_select_sales_order', 1],
    ];
    const updates = requiredFlags.filter(([fieldname, desired]) => Number(profile[fieldname] || 0) !== desired);
    if (!updates.length) {
      return profile;
    }

    return updates
      .reduce((chain, [fieldname, desired]) => chain.then(() => setField('POS Profile', profileName, fieldname, desired)), Cypress.Promise.resolve())
      .then(() =>
        frappeCall('frappe.client.get', {
          doctype: 'POS Profile',
          name: profileName,
        }).then((verifyResp) => {
          const verified = verifyResp && verifyResp.message ? verifyResp.message : null;
          expect(verified, `reloaded POS Profile ${profileName}`).to.be.an('object');
          return verified;
        })
      );
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

function clearPosStorageForFreshRole() {
  cy.window({ timeout: 30000 }).then((win) => {
    const keys = [];
    for (let i = 0; i < win.localStorage.length; i += 1) {
      const key = win.localStorage.key(i);
      if (key) keys.push(key);
    }

    keys
      .filter((key) => /^pos/i.test(key) || /^posa_/i.test(key))
      .forEach((key) => win.localStorage.removeItem(key));

    try {
      win.sessionStorage.clear();
    } catch (_err) {
      // Ignore storage access issues in older browser contexts.
    }
  });
}

function startPosForCurrentRole(profileName, options = {}) {
  const roleStorageValue = String(options.roleStorageValue || '').trim();
  const reloadWithRole = () => {
    if (!roleStorageValue) return;
    cy.log(`Opening dialog not shown; reapplying ${roleStorageValue} in localStorage and reloading.`);
    cy.window().then((win) => {
      win.localStorage.setItem('pos_current_role', roleStorageValue);
    });
    cy.reload();
  };

  cy.visit('/app/posapp');
  cy.get('body', { timeout: 60000 }).should('contain.text', 'POS');

  cy.get('body').then(($body) => {
    const hasRoleDialog = /Role:\s*/i.test($body.text() || '');
    if (!hasRoleDialog) {
      reloadWithRole();
      return;
    }

    selectProfileInOpeningDialog(profileName);
    cy.contains('.v-dialog--active .v-btn', /submit/i, { timeout: 30000 }).click({ force: true });
  });
}

function getDisplayedTotalQty($body) {
  const totalQtyBlock = [...$body.find('.v-input')].find((el) =>
    /total qty/i.test((el.innerText || '').trim())
  );
  if (!totalQtyBlock) return null;
  const input = totalQtyBlock.querySelector('input');
  const raw = input && typeof input.value === 'string' ? input.value : totalQtyBlock.innerText || '';
  const num = parseFloat(String(raw).replace(/[^0-9.-]/g, ''));
  return Number.isFinite(num) ? num : 0;
}

function hasVisibleSellableItem($body) {
  const usableRow = [...$body.find('.selection .v-data-table tbody tr')].find((el) => {
    const text = (el.innerText || '').trim();
    if (!text || /no data available/i.test(text)) return false;
    return el.querySelectorAll('td').length > 1 && Cypress.$(el).is(':visible');
  });
  if (usableRow) return true;

  const usableCard = [...$body.find('.selection .v-card')].find((el) => {
    const text = (el.innerText || '').trim();
    if (!text || /no data available/i.test(text)) return false;
    return Cypress.$(el).is(':visible');
  });
  return !!usableCard;
}

function waitForSellableItemGrid(maxCycles = 4) {
  const attempt = (cycle = 0) => {
    return cy.get('body', { timeout: 60000 }).then(($body) => {
      if (hasVisibleSellableItem($body)) return;

      if (cycle >= maxCycles) {
        throw new Error(
          'POS item grid never showed a sellable row/card after get_items cycles. Check current POS profile item setup.'
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
        })
        .then(() => cy.wait(500))
        .then(() => attempt(cycle + 1));
    });
  };

  return attempt(0);
}

function clickFirstSellableItem() {
  return cy.get('body', { timeout: 60000 }).then(($body) => {
    const usableRow = [...$body.find('.selection .v-data-table tbody tr')].find((el) => {
      const text = (el.innerText || '').trim();
      if (!text || /no data available/i.test(text)) return false;
      return el.querySelectorAll('td').length > 1;
    });
    if (usableRow) {
      cy.wrap(usableRow).click({ force: true });
      return;
    }

    const usableCard = [...$body.find('.selection .v-card')].find((el) => {
      const text = (el.innerText || '').trim();
      if (!text || /no data available/i.test(text)) return false;
      return Cypress.$(el).is(':visible');
    });
    if (usableCard) {
      cy.wrap(usableCard).click({ force: true });
      return;
    }

    throw new Error('No visible sellable item row/card found for token print test.');
  });
}

function ensureCartHasItem() {
  cy.get('body', { timeout: 30000 }).then(($body) => {
    const totalQty = getDisplayedTotalQty($body);
    if (totalQty !== null && totalQty > 0) return;
    throw new Error('Cart is still empty after selecting an item.');
  });
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

    throw new Error('Sales Order Token dialog was not found.');
  });
}

function installPrintCapture(win, state) {
  cy.stub(win, 'open').callsFake(() => {
    const iframe = win.document.createElement('iframe');
    iframe.setAttribute('data-cy-token-print-capture', '1');
    iframe.style.position = 'fixed';
    iframe.style.width = '1px';
    iframe.style.height = '1px';
    iframe.style.opacity = '0';
    iframe.style.pointerEvents = 'none';
    iframe.style.left = '-9999px';
    iframe.style.top = '-9999px';
    win.document.body.appendChild(iframe);

    const popupWin = iframe.contentWindow;
    expect(popupWin, 'print capture iframe contentWindow').to.not.equal(null);

    const originalWrite = popupWin.document.write.bind(popupWin.document);
    state.popupWindow = popupWin;
    state.rawHtml = '';
    state.renderedHtml = '';
    state.printed = false;
    state.focusCalled = false;
    state.openCount += 1;

    popupWin.focus = () => {
      state.focusCalled = true;
    };
    popupWin.print = () => {
      state.printed = true;
      try {
        state.renderedHtml = `<!doctype html>\n${popupWin.document.documentElement.outerHTML}`;
      } catch (_err) {
        state.renderedHtml = state.rawHtml;
      }
    };
    popupWin.document.write = (chunk) => {
      state.rawHtml += String(chunk || '');
      return originalWrite(chunk);
    };

    return popupWin;
  }).as('tokenPrintWindowOpen');
}

function setInputValue(selector, value) {
  cy.get(selector, { timeout: 30000 })
    .first()
    .should('exist')
    .then(($input) => {
      const el = $input[0];
      const nextValue = String(value == null ? '' : value);
      el.value = '';
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.value = nextValue;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
}

function getSearchOrderNameFromRequestBody(body) {
  if (!body) return '';
  if (typeof body === 'object') {
    return String(body.order_name || body?.args?.order_name || '').trim();
  }
  if (typeof body === 'string') {
    const text = String(body || '');
    try {
      const params = new URLSearchParams(text);
      return String(params.get('order_name') || '').trim();
    } catch (_err) {
      // Ignore URLSearchParams parsing errors.
    }
    try {
      const parsed = JSON.parse(text);
      return String(parsed.order_name || parsed?.args?.order_name || '').trim();
    } catch (_err) {
      // Ignore JSON parsing errors.
    }
  }
  return '';
}

function waitForSearchOrdersForQuery(query, maxRetries = 6) {
  const expected = String(query == null ? '' : query).trim();
  const attempt = (retryIndex = 0) =>
    cy.wait('@searchOrders', { timeout: 120000 }).then((interception) => {
      const sent = getSearchOrderNameFromRequestBody(interception?.request?.body);
      if (sent === expected) return interception;
      if (retryIndex >= maxRetries) return interception;
      cy.log(
        `search_orders alias mismatch (expected "${expected}" got "${sent}"), waiting next matching response (${retryIndex + 1}/${maxRetries}).`
      );
      return attempt(retryIndex + 1);
    });
  return attempt(0);
}

function searchSalesOrders(query) {
  const inputSelector = '.v-dialog--active input';
  const normalizedQuery = String(query == null ? '' : query);
  setInputValue(inputSelector, normalizedQuery);
  cy.contains('.v-dialog--active .v-btn', /^Search$/i, { timeout: 30000 }).click({ force: true });
  return waitForSearchOrdersForQuery(normalizedQuery).then((interception) => {
    expect(interception?.response?.statusCode, 'search_orders status').to.eq(200);
    const rows = Array.isArray(interception?.response?.body?.message) ? interception.response.body.message : [];
    return rows;
  });
}

function pickPreferredUsableRow(selector, preferredOrderName, options = {}) {
  const preferred = String(preferredOrderName || '').trim();
  const maxRetries = Number(options.maxRetries || 10);
  const delayMs = Number(options.delayMs || 1000);

  const attempt = (retryIndex = 0) =>
    cy.get('body', { timeout: 30000 }).then(($body) => {
      const rows = [...$body.find(selector)].filter((el) => {
        const text = (el.innerText || '').trim();
        if (!text || /no data available/i.test(text)) return false;
        return el.querySelectorAll('td').length > 1;
      });

      if (rows.length) {
        if (!preferred) return rows[0];
        return rows.find((el) => (el.innerText || '').includes(preferred)) || rows[0];
      }

      if (retryIndex >= maxRetries) return null;

      cy.log(`Waiting for selectable Sales Order row (${retryIndex + 1}/${maxRetries}).`);
      cy.wait(delayMs);
      return attempt(retryIndex + 1);
    });

  return attempt(0);
}

function waitForCartHasItem(maxRetries = 6, delayMs = 1000) {
  const attempt = (retryIndex = 0) => {
    return cy.get('body', { timeout: 30000 }).then(($body) => {
      const totalQty = getDisplayedTotalQty($body);
      if (totalQty !== null && totalQty > 0) return;

      if (retryIndex >= maxRetries) {
        throw new Error('Cart stayed empty after create_sales_invoice_from_order. Expected Sales Order items to load into invoice.');
      }

      cy.log(`Waiting for invoice lines from selected Sales Order (retry ${retryIndex + 1}/${maxRetries}).`);
      cy.wait(delayMs);
      return attempt(retryIndex + 1);
    });
  };

  return attempt(0);
}

describe('Cloud token print PDF + cashier retrieval (watch mode)', () => {
  it('captures token slip to PDF and proves current cashier retrieval path', () => {
    const profileName = 'PJ7 CASHIER';
    const printCapture = {
      openCount: 0,
      rawHtml: '',
      renderedHtml: '',
      printed: false,
      focusCalled: false,
      popupWindow: null,
    };
    const runSummary = {
      capturedAt: new Date().toISOString(),
      profileName,
      salesOrder: '',
      tokenId: '',
      tokenLast4: '',
      htmlPath: '',
      pdfPath: '',
      evidenceJsonPath: '',
      qrLookupSupported: false,
      barcodeLookupWorked: false,
      fallbackSoLookupWorked: false,
      loadedIntoInvoice: false,
      relayEvidencePath: '',
    };
    let relayClientKey = '';
    let currentUserDocname = '';
    let saRoleName = '';
    let cashierRoleName = '';
    let currentEvidence = null;

    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.get_items').as('getItems');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.create_sales_order_token').as(
      'createSalesOrderToken'
    );
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.search_orders').as('searchOrders');
    cy.intercept('POST', '**/api/method/posawesome.posawesome.api.posapp.create_sales_invoice_from_order').as(
      'createInvoiceFromOrder'
    );

    loginWithOtp();
    cy.visit('/app');

    resolveTargetUserDocname().then((docname) => {
      currentUserDocname = docname;
    });
    resolveOperationalRole('sales-associate').then((roleName) => {
      saRoleName = roleName;
    });
    resolveOperationalRole('cashier').then((roleName) => {
      cashierRoleName = roleName;
    });
    ensureProfileConfigured(profileName);

    cy.then(() => setOnlyOperationalRole(currentUserDocname, saRoleName));

    clearPosStorageForFreshRole();
    startPosForCurrentRole(profileName, { roleStorageValue: saRoleName });
    cy.request('http://127.0.0.1:8787/health').its('body.ok').should('eq', true);
    cy.get('body', { timeout: 60000 }).should('contain.text', 'Search Items');
    waitForSellableItemGrid();
    assertRelayUiAndActual({ relayBase: 'http://127.0.0.1:8787', expectRelayOnline: true, expectCloudOnline: true });

    cy.window().then((win) => {
      relayClientKey = String(win.localStorage.getItem('posa_relay_client_key') || '').trim();
      installPrintCapture(win, printCapture);
    });

    clickFirstSellableItem();
    cy.wait(500);
    ensureCartHasItem();

    cy.contains('.v-btn', 'Save/New', { timeout: 30000 }).click({ force: true });

    cy.wait('@createSalesOrderToken', { timeout: 120000 }).then((interception) => {
      expect(interception?.response?.statusCode, 'create_sales_order_token status').to.eq(200);
      const message = interception?.response?.body?.message || {};
      runSummary.salesOrder = String(message.sales_order_name || '').trim();
      runSummary.tokenId = String(message.token_id || '').trim();
      runSummary.tokenLast4 = String(message.token_last4 || '').trim();
      expect(runSummary.salesOrder, 'sales_order_name').to.not.equal('');
      expect(runSummary.tokenId, 'token_id').to.not.equal('');
    });

    cy.contains('body', 'Sales Order Token', { timeout: 60000 }).should('be.visible');
    getSalesOrderTokenDialog().as('tokenDialog');
    cy.get('@tokenDialog').should('contain.text', 'Customer');
    cy.get('@tokenDialog').should('contain.text', 'Sales Associate');
    cy.get('@tokenDialog').should('contain.text', 'Grand Total');
    cy.get('@tokenDialog').should('contain.text', 'SO:');

    cy.get('@tokenDialog').within(() => {
      cy.contains('button, .v-btn', /^Print Token Slip$/i, { timeout: 30000 }).click({ force: true });
    });

    cy.get('@tokenPrintWindowOpen').should('have.been.called');
    cy.wrap(null, { timeout: 15000 }).should(() => {
      expect(printCapture.openCount, 'print popup count').to.eq(1);
      expect(printCapture.focusCalled, 'print popup focus call').to.eq(true);
      expect(printCapture.printed, 'print popup print invocation').to.eq(true);
      expect(String(printCapture.rawHtml || '').trim(), 'captured raw token slip HTML').to.not.equal('');
    });

    cy.then(() => {
      const finalHtml = String(printCapture.renderedHtml || printCapture.rawHtml || '').trim();
      expect(finalHtml, 'final token slip HTML').to.not.equal('');
      return cy
        .task('saveTokenSlipHtml', {
          html: finalHtml,
          meta: {
            salesOrder: runSummary.salesOrder,
            tokenId: runSummary.tokenId,
            tokenLast4: runSummary.tokenLast4,
          },
          spec: Cypress.spec.relative,
          testTitle: 'token_print_pdf_and_cashier_retrieve',
        })
        .then(({ htmlPath }) => {
          runSummary.htmlPath = htmlPath;
          return cy.task('extractTokenSlipEvidence', { html: finalHtml });
        })
        .then((evidence) => {
          currentEvidence = evidence || {};
          expect(currentEvidence.salesOrder, 'printed sales_order').to.equal(runSummary.salesOrder);
          expect(currentEvidence.tokenLast4, 'printed token_last4').to.equal(runSummary.tokenLast4);
          expect(currentEvidence.customerName, 'printed customer_name').to.not.equal('');
          expect(currentEvidence.salesAssociate, 'printed sales_associate').to.not.equal('');
          expect(currentEvidence.date, 'printed date').to.not.equal('');
          expect(currentEvidence.time, 'printed time').to.not.equal('');
          expect(currentEvidence.grandTotal, 'printed grand_total').to.not.equal('');
          expect(currentEvidence.barcodeValue, 'printed barcode value').to.not.equal('');
          expect(currentEvidence.qrPayloadJson, 'parsed QR payload JSON').to.be.an('object');
          expect(currentEvidence.qrPayloadJson).to.include({
            type: 'POS-SO-TOKEN',
            sales_order: runSummary.salesOrder,
            token_id: runSummary.tokenId,
            token_last4: runSummary.tokenLast4,
          });

          const evidenceJsonPath = runSummary.htmlPath.replace(/\.html$/i, '.evidence.json');
          runSummary.evidenceJsonPath = evidenceJsonPath;
          cy.writeFile(evidenceJsonPath, {
            capturedAt: new Date().toISOString(),
            ...currentEvidence,
          });
        })
        .then(() =>
          cy.task('renderHtmlToPdf', {
            htmlPath: runSummary.htmlPath,
            pdfPath: runSummary.htmlPath.replace(/\.html$/i, '.pdf'),
          })
        )
        .then(({ pdfPath }) => {
          runSummary.pdfPath = pdfPath;
          return cy.task('assertFileExists', { filePath: pdfPath });
        });
    });

    cy.then(() => {
      const relayEvidencePath = 'cypress/tmp/latest_token_print_relay_evidence.json';
      runSummary.relayEvidencePath = relayEvidencePath;
      cy.request({
        method: 'GET',
        url: `http://127.0.0.1:8787/relay/token/${encodeURIComponent(runSummary.tokenId)}`,
        timeout: 60000,
      }).then((tokenResp) => {
        expect(tokenResp.status, 'relay token detail status').to.eq(200);
        expect(String(tokenResp.body?.token?.token_id || '').trim(), 'relay token id').to.eq(runSummary.tokenId);

        return cy.request({
          method: 'GET',
          url: `http://127.0.0.1:8787/relay/tokens/search?pos_profile_id=${encodeURIComponent(profileName)}&search=${encodeURIComponent(runSummary.tokenId)}&statuses_csv=TOKEN_OPEN&limit=20`,
          headers: relayClientKey ? { 'X-Relay-Client-Key': relayClientKey } : {},
          timeout: 60000,
        }).then((searchResp) => {
          expect(searchResp.status, 'relay token search status').to.eq(200);
          const rows = Array.isArray(searchResp.body?.rows) ? searchResp.body.rows : [];
          expect(rows.some((row) => String(row?.token_id || '').trim() === runSummary.tokenId), 'relay search finds token').to.eq(true);

          cy.writeFile(relayEvidencePath, {
            capturedAt: new Date().toISOString(),
            tokenDetail: tokenResp.body,
            searchResultCount: rows.length,
            matchedRow: rows.find((row) => String(row?.token_id || '').trim() === runSummary.tokenId) || null,
          });
        });
      });
    });

    cy.then(() => setOnlyOperationalRole(currentUserDocname, cashierRoleName));
    loginWithOtp();
    cy.visit('/app');
    clearPosStorageForFreshRole();
    cy.window().then((win) => {
      win.localStorage.setItem('pos_current_role', cashierRoleName);
    });
    startPosForCurrentRole(profileName, { roleStorageValue: cashierRoleName });
    cy.contains('.v-btn', 'Select S.O', { timeout: 30000 }).should('be.visible');

    cy.contains('.v-btn', 'Select S.O', { timeout: 30000 }).click({ force: true });
    cy.contains('.v-dialog--active .headline', 'Select Sales Orders', { timeout: 30000 }).should('exist');
    cy.wait('@searchOrders', { timeout: 120000 }).its('response.statusCode').should('eq', 200);

    cy.then(() => searchSalesOrders(currentEvidence.qrPayloadRaw || '')).then((rows) => {
      const qrRowMatch = rows.some((row) => String(row?.name || '').trim() === runSummary.salesOrder);
      runSummary.qrLookupSupported = qrRowMatch;
      cy.log(`QR raw lookup supported: ${qrRowMatch ? 'yes' : 'no'}`);
    });

    cy.then(() => searchSalesOrders(currentEvidence.barcodeValue || runSummary.tokenId)).then((rows) => {
      const barcodeRowMatch = rows.some((row) => String(row?.name || '').trim() === runSummary.salesOrder);
      runSummary.barcodeLookupWorked = barcodeRowMatch;
      if (barcodeRowMatch) {
        return;
      }

      return searchSalesOrders(runSummary.salesOrder).then((fallbackRows) => {
        const fallbackMatch = fallbackRows.some((row) => String(row?.name || '').trim() === runSummary.salesOrder);
        runSummary.fallbackSoLookupWorked = fallbackMatch;
      });
    });

    cy.then(() => {
      expect(
        runSummary.barcodeLookupWorked || runSummary.fallbackSoLookupWorked,
        'cashier retrieval via barcode or SO fallback'
      ).to.eq(true);
    });

    pickPreferredUsableRow('.v-dialog--active .v-data-table tbody tr', runSummary.salesOrder, {
      maxRetries: 15,
      delayMs: 1000,
    }).then((row) => {
      if (!row) {
        throw new Error('No selectable Sales Order row found after token retrieval searches.');
      }
      const rowEl = row && row.jquery ? row.get(0) : row;
      const checkbox =
        rowEl && typeof rowEl.querySelector === 'function'
          ? rowEl.querySelector('.v-simple-checkbox, [role="checkbox"], .v-input--selection-controls__ripple')
          : null;
      if (checkbox) {
        cy.wrap(checkbox).click({ force: true });
      } else {
        cy.wrap(rowEl).click({ force: true });
      }
    });

    cy.contains('.v-dialog--active .v-btn', /^Select$/i, { timeout: 30000 }).click({ force: true });
    cy.wait('@createInvoiceFromOrder', { timeout: 120000 }).then((interception) => {
      expect(interception?.response?.statusCode, 'create_sales_invoice_from_order status').to.eq(200);
      const doc = interception?.response?.body?.message || {};
      const invoiceSalesOrder = String(
        doc?.sales_order ||
          doc?.sales_order_name ||
          doc?.items?.[0]?.sales_order ||
          doc?.items?.[0]?.sales_order_name ||
          ''
      ).trim();
      cy.writeFile('cypress/tmp/latest_token_print_invoice_from_order_response.json', {
        capturedAt: new Date().toISOString(),
        salesOrderExpected: runSummary.salesOrder,
        salesOrderResolved: invoiceSalesOrder,
        name: doc?.name || '',
        doctype: doc?.doctype || '',
        token_id: doc?.token_id || '',
        itemsCount: Array.isArray(doc?.items) ? doc.items.length : 0,
        rawTopLevelSalesOrder: doc?.sales_order || '',
        rawTopLevelSalesOrderName: doc?.sales_order_name || '',
        rawFirstItemSalesOrder: doc?.items?.[0]?.sales_order || '',
      });
      if (invoiceSalesOrder) {
        expect(invoiceSalesOrder, 'loaded invoice sales_order').to.eq(runSummary.salesOrder);
      }
    });
    cy.contains('.v-dialog--active .headline', 'Select Sales Orders', { timeout: 30000 }).should('not.exist');
    waitForCartHasItem();
    ensureCartHasItem();
    runSummary.loadedIntoInvoice = true;

    cy.writeFile('cypress/tmp/latest_token_print_retrieval_summary.json', runSummary);
  });
});
