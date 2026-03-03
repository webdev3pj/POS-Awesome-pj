function findFirstSelector($root, selectors) {
  return selectors.find((selector) => $root.find(selector).length > 0);
}

function typeIntoFirstAvailable(selectors, value, options = {}) {
  cy.get("body", { timeout: 30000 }).then(($body) => {
    const selector = findFirstSelector($body, selectors);
    expect(selector, `selector from list: ${selectors.join(", ")}`).to.be.a("string");
    cy.get(selector, { timeout: 30000 })
      .first()
      .should("be.visible")
      .clear({ force: true })
      .type(value, options);
  });
}

function clickFirstAvailable(selectors) {
  cy.get("body", { timeout: 30000 }).then(($body) => {
    const selector = findFirstSelector($body, selectors);
    expect(selector, `selector from list: ${selectors.join(", ")}`).to.be.a("string");
    cy.get(selector, { timeout: 30000 }).first().should("be.visible").click({ force: true });
  });
}

function clickLoginSubmitNearPassword() {
  return cy.get("body", { timeout: 30000 }).then(($body) => {
    const pwdSelector = findFirstSelector($body, [
      "#login_password",
      "input[name='pwd']",
      "input[type='password']",
    ]);
    expect(pwdSelector, "password field selector").to.be.a("string");

    cy.get(pwdSelector, { timeout: 30000 })
      .first()
      .should("be.visible")
      .then(($pwd) => {
        const $form = $pwd.closest("form");
        if ($form.length) {
          const loginBtn = $form
            .find("button, .btn")
            .filter((_, el) => /^login$/i.test((el.innerText || "").trim()));
          if (loginBtn.length) {
            cy.wrap(loginBtn[0]).click({ force: true });
            return;
          }
        }
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
  const verifySelectors = [
    "#verify_token",
    "button[type='submit']",
    ".page-card-actions .btn-primary",
    "button.btn-primary",
  ];

  const attempt = (retryIndex = 0) => {
    return cy.get("body", { timeout: 30000 }).then(($body) => {
      const otpSelector = findFirstSelector($body, otpSelectors);
      if (!otpSelector) return;
      return waitForSafeTotpWindow().then(() =>
        cy.task("generateTotp", { otpauthUri: totpUri }).then((otpCode) => {
          const code = String(otpCode || "").trim();
          expect(code, "generated OTP code").to.match(/^\d{6}$/);
          cy.get(otpSelector, { timeout: 30000 }).first().clear({ force: true }).type(code, {
            log: false,
          });
          clickFirstAvailable(verifySelectors);
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

function runLoginSequence(username, password, totpUri) {
  typeIntoFirstAvailable(
    ["#login_email", "input[name='usr']", "input[name='login_email']", "input[type='email']"],
    username
  );
  typeIntoFirstAvailable(["#login_password", "input[name='pwd']", "input[type='password']"], password, {
    log: false,
  });
  clickLoginSubmitNearPassword();
  cy.wait(1200);
  cy.get("body").then(($body) => {
    const otpField = findFirstSelector($body, [
      "#login_token",
      "input[name='otp']",
      "input[name='token']",
      "input[name='login_token']",
      "input[autocomplete='one-time-code']",
    ]);
    if (otpField) submitOtpCodeWithRetry(totpUri, 2);
  });
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
  runLoginSequence(username, password, totpUri);

  cy.location("pathname", { timeout: 15000 }).then((pathname) => {
    if (/^\/app(\/|$)/.test(pathname)) {
      return;
    }

    cy.log(`Login did not reach /app (path=${pathname}); retrying once.`);
    cy.visit("/login");
    runLoginSequence(username, password, totpUri);
  });

  cy.location("pathname", { timeout: 90000 }).should("match", /^\/app(\/|$)/);
}

function frappeCall(method, args, options = {}) {
  const timeout = Number(options.timeout || 60000);
  return cy.window({ timeout: 30000 }).then({ timeout }, (win) => {
    const toMessage = (payload) => {
      if (!payload) return "frappe.call failed";
      if (typeof payload === "string") return payload;
      const direct =
        payload.message ||
        payload.exc ||
        payload.exception ||
        payload._error_message ||
        payload.server_messages ||
        payload._server_messages;
      if (typeof direct === "string" && direct.trim()) return direct;
      try {
        return JSON.stringify(payload);
      } catch (_e) {
        return String(payload);
      }
    };

    return new Cypress.Promise((resolve, reject) => {
      win.frappe.call({
        method,
        args: args || {},
        callback: (r) => {
          if (r && (r.exc || r._server_messages || r._error_message)) {
            const err = new Error(
              `frappe.call ${method} failed: ${toMessage(
                r._error_message || r._server_messages || r.exc || r.message || r
              )}`
            );
            err.name = "FrappeCallError";
            err.frappePayload = r;
            reject(err);
            return;
          }
          resolve(r);
        },
        error: (errPayload) => {
          const err = new Error(`frappe.call ${method} failed: ${toMessage(errPayload)}`);
          err.name = "FrappeCallError";
          err.frappePayload = errPayload;
          reject(err);
        },
      });
    });
  });
}

module.exports = {
  loginWithOtp,
  frappeCall,
};
