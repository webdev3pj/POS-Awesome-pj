function findFirstSelector($root, selectors) {
  return selectors.find((selector) => $root.find(selector).length > 0);
}

function typeIntoFirstAvailable(selectors, value, options = {}) {
  cy.get("body", { timeout: 30000 }).then(($body) => {
    const selector = findFirstSelector($body, selectors);
    expect(selector, `selector from list: ${selectors.join(", ")}`).to.be.a("string");
    cy.get(selector, { timeout: 30000 }).first().should("be.visible").clear({ force: true }).type(value, options);
  });
}

function clickFirstAvailable(selectors) {
  cy.get("body", { timeout: 30000 }).then(($body) => {
    const selector = findFirstSelector($body, selectors);
    expect(selector, `selector from list: ${selectors.join(", ")}`).to.be.a("string");
    cy.get(selector, { timeout: 30000 }).first().should("be.visible").click({ force: true });
  });
}

function waitForSafeTotpWindow(minRemainingSeconds = 6) {
  return cy.window({ timeout: 30000 }).then((win) => {
    const nowSec = Math.floor(win.Date.now() / 1000);
    const secIntoWindow = nowSec % 30;
    const remaining = 30 - secIntoWindow;
    if (remaining <= minRemainingSeconds) {
      cy.wait((remaining + 1) * 1000);
    }
  });
}

function submitOtpCodeWithRetry(totpUri, maxRetries = 2) {
  const otpSelectors = [
    "#login_token",
    "input[name='otp']",
    "input[name='token']",
    "input[name='login_token']",
    "input[autocomplete='one-time-code']",
  ];

  const attempt = (retryIndex = 0) => {
    return cy.get("body", { timeout: 30000 }).then(($body) => {
      const otpSelector = findFirstSelector($body, otpSelectors);
      if (!otpSelector) return;

      return waitForSafeTotpWindow().then(() =>
        cy.task("generateTotp", { otpauthUri: totpUri }).then((otpCode) => {
          const code = String(otpCode || "").trim();
          expect(code).to.match(/^\d{6}$/);
          cy.get(otpSelector, { timeout: 30000 })
            .first()
            .should("be.visible")
            .clear({ force: true })
            .type(code, { log: false });
          clickFirstAvailable([
            "#verify_token",
            "button[type='submit']",
            ".page-card-actions .btn-primary",
            "button.btn-primary",
          ]);

          cy.wait(1500);
          cy.get("body").then(($after) => {
            const stillOnOtp = !!findFirstSelector($after, otpSelectors);
            const invalidLogin = /invalid login/i.test(($after.text() || "").trim());
            if (stillOnOtp && invalidLogin) {
              if (retryIndex >= maxRetries) {
                throw new Error("OTP verification failed after retries.");
              }
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
  const username = Cypress.env("username");
  const password = Cypress.env("password");
  const totpUri = Cypress.env("totpUri");

  expect(Cypress.config("baseUrl"), "CYPRESS_baseUrl").to.be.a("string").and.not.be.empty;
  expect(username, "CYPRESS_username").to.be.a("string").and.not.be.empty;
  expect(password, "CYPRESS_password").to.be.a("string").and.not.be.empty;
  expect(totpUri, "CYPRESS_totpUri").to.be.a("string").and.not.be.empty;

  cy.clearCookies();
  cy.clearLocalStorage();
  cy.visit("/login");

  typeIntoFirstAvailable(
    ["#login_email", "input[name='usr']", "input[name='login_email']", "input[type='email']"],
    username
  );
  typeIntoFirstAvailable(["#login_password", "input[name='pwd']", "input[type='password']"], password, {
    log: false,
  });
  clickFirstAvailable([
    "button.btn-login",
    ".btn-login",
    "button[type='submit']",
    ".page-card-actions .btn-primary",
  ]);

  cy.wait(1500);
  cy.get("body", { timeout: 30000 }).then(($body) => {
    const otpSelector = findFirstSelector($body, [
      "#login_token",
      "input[name='otp']",
      "input[name='token']",
      "input[name='login_token']",
      "input[autocomplete='one-time-code']",
    ]);
    if (!otpSelector) return;
    submitOtpCodeWithRetry(totpUri, 2);
  });

  cy.location("pathname", { timeout: 90000 }).should("match", /^\/app(\/|$)/);
}

function _frappeCallOnce(method, args, timeoutMs) {
  const callTimeout = Math.max(1000, Number(timeoutMs || 60000));
  const thenTimeout = callTimeout + 5000;
  return cy.window({ timeout: 30000 }).then({ timeout: thenTimeout }, (win) => {
    return new Cypress.Promise((resolve, reject) => {
      let settled = false;
      const timeoutHandle = setTimeout(() => {
        if (settled) return;
        settled = true;
        reject(new Error(`frappe.call timeout for method: ${method}`));
      }, callTimeout);

      const finish = (fn, value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timeoutHandle);
        fn(value);
      };

      try {
        win.frappe.call({
          method,
          args: args || {},
          callback: (r) => finish(resolve, r),
          error: (err) => finish(reject, err),
        });
      } catch (err) {
        finish(reject, err);
      }
    });
  });
}

function frappeCall(method, args, options = {}) {
  const timeout = Number(options.timeout || 60000);
  const retries = Number(options.retries || 1);
  const thenTimeout = Math.max(15000, timeout + 5000);

  const attempt = (retryIndex = 0) => {
    return cy.then({ timeout: thenTimeout }, () => _frappeCallOnce(method, args, timeout)).then(
      (resp) => resp,
      (err) => {
        if (retryIndex >= retries) throw err;
        cy.wait(1200);
        return attempt(retryIndex + 1);
      }
    );
  };

  return attempt(0);
}

function setSingleOperationalRole(userDocname, roleName) {
  return frappeCall("frappe.client.get", { doctype: "User", name: userDocname }, { timeout: 120000 }).then(
    (getResp) => {
      const doc = getResp && getResp.message ? getResp.message : null;
      expect(doc, "User doc loaded").to.be.an("object");

      const existingRoles = Array.isArray(doc.roles) ? doc.roles : [];
      const preservedNonClineRoles = existingRoles.filter(
        (r) => !String((r && r.role) || "").startsWith("cline-")
      );
      const existingTarget = existingRoles.find((r) => String((r && r.role) || "") === roleName);
      const rebuiltRoles = [...preservedNonClineRoles];

      if (existingTarget) {
        rebuiltRoles.push(existingTarget);
      } else {
        rebuiltRoles.push({
          doctype: "Has Role",
          parent: doc.name,
          parenttype: "User",
          parentfield: "roles",
          role: roleName,
        });
      }

      return frappeCall(
        "frappe.client.save",
        {
          doc: {
            ...doc,
            roles: rebuiltRoles,
            __unsaved: 1,
          },
        },
        { timeout: 120000 }
      );
    }
  );
}

function choosePosProfile(profileName) {
  cy.contains(".v-dialog--active .v-input", "POS Profile", { timeout: 30000 })
    .find("input:not([type='hidden'])")
    .first()
    .should("be.visible")
    .click({ force: true })
    .clear({ force: true })
    .type(profileName, { force: true });

  cy.get("body").then(($body) => {
    const option = [...$body.find(".v-list-item__title")].find(
      (el) => (el.innerText || "").trim() === profileName
    );
    if (option) {
      cy.wrap(option).click({ force: true });
    } else {
      cy.contains(".v-dialog--active .v-input", "POS Profile")
        .find("input:not([type='hidden'])")
        .first()
        .type("{enter}", { force: true });
    }
  });
}

function openPosSessionForRole({
  roleStorageValue,
  roleLabel,
  profileName,
  expectFulfillment,
  screenshotDialogName,
  expectCashOpeningDialog,
}) {
  cy.visit("/app/posapp");
  cy.get("body", { timeout: 60000 }).should("contain.text", "POS");

  cy.window().then((win) => {
    win.localStorage.setItem("pos_current_role", roleStorageValue);
  });
  cy.reload();
  cy.get("body", { timeout: 60000 }).should("contain.text", "POS");

  cy.get("body").then(($body) => {
    if (($body.text() || "").includes("multiple operational roles")) {
      throw new Error(`User has multiple operational roles. Expected only ${roleStorageValue}.`);
    }
    const hasRoleDialog = /Role:\s*/i.test($body.text() || "");
    if (!hasRoleDialog) return;

    cy.contains("Role:", { timeout: 30000 }).should("be.visible");
    cy.contains(roleLabel, { timeout: 30000 }).should("be.visible");

    if (expectCashOpeningDialog) {
      cy.contains(".v-dialog--active .v-card__title", "Create POS Opening Shift", { timeout: 30000 }).should(
        "be.visible"
      );
      cy.contains(".v-dialog--active", "Opening Amount", { timeout: 30000 }).should("be.visible");
    } else {
      cy.contains(".v-dialog--active .v-card__title", "Start POS Session", { timeout: 30000 }).should(
        "be.visible"
      );
      cy.contains(".v-dialog--active", "Opening Amount", { timeout: 5000 }).should("not.exist");
    }

    if (screenshotDialogName) {
      cy.wait(700);
      cy.screenshot(screenshotDialogName, { capture: "viewport" });
    }

    choosePosProfile(profileName);
    cy.contains(".v-dialog--active .v-btn", /submit/i, { timeout: 30000 }).click({ force: true });
  });

  if (expectFulfillment) {
    cy.get("body", { timeout: 90000 }).should("contain.text", "Fulfillment Detail");
  } else {
    cy.contains("body", "Search Items", { timeout: 90000 }).should("be.visible");
  }
}

function clickFirstSellableItemIfCartEmpty() {
  cy.get("body").then(($body) => {
    const totalQtyBlock = [...$body.find(".v-input")].find((el) => /total qty/i.test((el.innerText || "").trim()));
    const currentQty = (() => {
      if (!totalQtyBlock) return 0;
      const input = totalQtyBlock.querySelector("input");
      const raw = input ? input.value : totalQtyBlock.innerText || "";
      const n = parseFloat(String(raw).replace(/[^0-9.-]/g, ""));
      return Number.isFinite(n) ? n : 0;
    })();
    if (currentQty > 0) return;

    const row = [...$body.find(".selection .v-data-table tbody tr")].find((el) => {
      const text = (el.innerText || "").trim();
      return text && !/no data available/i.test(text) && el.querySelectorAll("td").length > 1;
    });
    if (row) {
      cy.wrap(row).click({ force: true });
      return;
    }

    const card = [...$body.find(".selection .v-card")].find((el) => {
      const text = (el.innerText || "").trim();
      return text && !/no data available/i.test(text) && Cypress.$(el).is(":visible");
    });
    if (card) {
      cy.wrap(card).click({ force: true });
    }
  });
}

function openPaymentScreenIfPossible() {
  clickFirstSellableItemIfCartEmpty();
  cy.wait(600);
  cy.get("body").then(($body) => {
    const payBtn = [...$body.find(".v-btn")].find((el) => ((el.innerText || "").trim() || "").toUpperCase() === "PAY");
    if (!payBtn || !Cypress.$(payBtn).is(":visible")) return;
    cy.wrap(payBtn).click({ force: true });
  });
}

function maybeCaptureSelectSoDialog(screenshotName) {
  cy.get("body").then(($body) => {
    const selectSoBtn = [...$body.find(".v-btn")].find((el) => {
      const txt = (el.innerText || "").trim().toUpperCase();
      return txt === "SELECT S.O" && Cypress.$(el).is(":visible");
    });
    if (!selectSoBtn) return;
    cy.wrap(selectSoBtn).click({ force: true });
    cy.contains(".v-dialog--active .headline", "Select Sales Orders", { timeout: 30000 }).should("be.visible");
    cy.wait(800);
    cy.screenshot(screenshotName, { capture: "viewport" });

    cy.get("body").then(($b2) => {
      const closeBtn = [...$b2.find(".v-dialog--active .v-btn")].find((el) => /close|cancel/i.test((el.innerText || "").trim()));
      if (closeBtn) {
        cy.wrap(closeBtn).click({ force: true });
      } else {
        cy.get("body").type("{esc}");
      }
    });
  });
}

function selectFirstQueueRowIfAny() {
  cy.get("body").then(($body) => {
    const row = [...$body.find(".queue-list .v-list-item")].find((el) => Cypress.$(el).is(":visible"));
    if (!row) return;
    cy.wrap(row).click({ force: true });
    cy.wait(900);
  });
}

describe("Manuals v2 clean screenshots (high-res, fresh)", () => {
  it("captures fresh UI screenshots for all roles and key dialogs", () => {
    const profileName = "PJ7 CASHIER";
    const roles = {
      sa: "cline-Sales Associate",
      cashier: "cline-Cashier",
      picker: "cline-Picker",
      dispatch: "cline-Dispatch",
      supervisor: "cline-Supervisor",
    };
    let userDocname = "";

    cy.viewport(1904, 985);
    loginWithOtp();
    cy.visit("/app");
    cy.window({ timeout: 30000 }).then((win) => {
      userDocname = String(win?.frappe?.session?.user || "").trim();
      expect(userDocname, "resolved user docname").to.not.equal("");
    });

    cy.then(() => setSingleOperationalRole(userDocname, roles.sa));
    cy.then(() =>
      openPosSessionForRole({
        roleStorageValue: roles.sa,
        roleLabel: "Sales Associate",
        profileName,
        expectFulfillment: false,
        screenshotDialogName: "manuals-v3-sa-opening-dialog",
        expectCashOpeningDialog: false,
      })
    );
    cy.wait(900);
    cy.screenshot("manuals-v3-sa-ui", { capture: "viewport" });

    cy.then(() => setSingleOperationalRole(userDocname, roles.cashier));
    cy.then(() =>
      openPosSessionForRole({
        roleStorageValue: roles.cashier,
        roleLabel: "Cashier",
        profileName,
        expectFulfillment: false,
        screenshotDialogName: "manuals-v3-cashier-opening-dialog",
        expectCashOpeningDialog: true,
      })
    );
    cy.wait(900);
    cy.screenshot("manuals-v3-cashier-ui", { capture: "viewport" });
    maybeCaptureSelectSoDialog("manuals-v3-select-sales-order");

    openPaymentScreenIfPossible();
    cy.get("body").then(($body) => {
      if (($body.text() || "").includes("Cancel Payment")) {
        cy.wait(700);
        cy.screenshot("manuals-v3-payment-screen", { capture: "viewport" });
        cy.contains(".v-btn", "Cancel Payment", { timeout: 30000 }).click({ force: true });
      }
    });

    cy.then(() => setSingleOperationalRole(userDocname, roles.picker));
    cy.then(() =>
      openPosSessionForRole({
        roleStorageValue: roles.picker,
        roleLabel: "Picker",
        profileName,
        expectFulfillment: true,
        screenshotDialogName: null,
        expectCashOpeningDialog: false,
      })
    );
    selectFirstQueueRowIfAny();
    cy.screenshot("manuals-v3-picker-ui", { capture: "viewport" });

    cy.then(() => setSingleOperationalRole(userDocname, roles.dispatch));
    cy.then(() =>
      openPosSessionForRole({
        roleStorageValue: roles.dispatch,
        roleLabel: "Dispatch",
        profileName,
        expectFulfillment: true,
        screenshotDialogName: null,
        expectCashOpeningDialog: false,
      })
    );
    selectFirstQueueRowIfAny();
    cy.get("body").then(($body) => {
      const proofCard = $body.find("[data-cy='dispatch-proof-ack']").get(0);
      if (proofCard) {
        cy.wrap(proofCard).scrollIntoView({ duration: 200 });
      }
    });
    cy.wait(700);
    cy.screenshot("manuals-v3-dispatch-ui", { capture: "viewport" });

    cy.then(() => setSingleOperationalRole(userDocname, roles.supervisor));
    cy.then(() =>
      openPosSessionForRole({
        roleStorageValue: roles.supervisor,
        roleLabel: "Supervisor",
        profileName,
        expectFulfillment: true,
        screenshotDialogName: null,
        expectCashOpeningDialog: false,
      })
    );
    selectFirstQueueRowIfAny();
    cy.wait(700);
    cy.screenshot("manuals-v3-supervisor-ui", { capture: "viewport" });
  });
});
