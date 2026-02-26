const { assertRelayUiAndActual } = require("./_helpers/relay_ui_sync");

function findFirstSelector($root, selectors) {
  return selectors.find((selector) => $root.find(selector).length > 0);
}

function findNavbarVmHost($body) {
  return [...$body.find("*")].find((el) => {
    const vm = el && el.__vue__;
    return (
      vm &&
      typeof vm.fetch_relay_status === "function" &&
      typeof vm.check_cloud_connectivity === "function" &&
      Object.prototype.hasOwnProperty.call(vm, "relay_status")
    );
  });
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
  clickLoginSubmitNearPassword();

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

describe("Local staging parity smoke (watch mode)", () => {
  it("captures local staging POS bootstrap/version snapshots and verifies relay UI matches actual relay health", () => {
    const relayBase = "http://127.0.0.1:8787";

    cy.viewport(1600, 900);
    cy.intercept("POST", "**/api/method/posawesome.posawesome.api.posapp.get_relay_connectivity_status").as(
      "getRelayConnectivityStatus"
    );
    loginWithOtp();

    cy.request({
      method: "GET",
      url: "/api/method/posawesome.posawesome.api.posapp.get_opening_dialog_data",
      failOnStatusCode: false,
      timeout: 60000,
    }).then((resp) => {
      expect(resp.status, "opening dialog API status").to.eq(200);
      const msg = (resp.body && resp.body.message) || {};
      expect(msg, "opening dialog payload").to.be.an("object");
      expect(msg).to.have.property("relay_client_auth_key");
      expect(msg).to.have.property("relay_client_auth_required");
      expect(msg).to.have.property("user_role");
      expect(Array.isArray(msg.pos_profiles_data), "pos_profiles_data array").to.eq(true);
      cy.writeFile("cypress/tmp/local_staging_opening_dialog_data.json", msg);
    });

    cy.visit("/app");
    cy.location("host", { timeout: 60000 }).should("match", /pj\.local(?::8080)?$/i);

    cy.window({ timeout: 60000 }).then((win) => {
      const versions =
        (win.frappe &&
          win.frappe.boot &&
          (win.frappe.boot.versions || win.frappe.boot.change_log_versions)) ||
        null;
      expect(versions, "frappe boot versions snapshot").to.exist;
      cy.writeFile("cypress/tmp/local_staging_versions.json", versions);
    });

    cy.visit("/app/posapp");
    cy.location("pathname", { timeout: 90000 }).should("match", /^\/app\/posapp(?:\/)?$/);
    cy.get("body", { timeout: 90000 }).should(($body) => {
      const text = ($body.text() || "").trim();
      expect(/POS AWESOME/i.test(text), "POS app shell visible").to.eq(true);
      expect(/Search Items/i.test(text), "real POS UI rendered").to.eq(true);
      expect(/SELECT S\.O/i.test(text), "cashier POS actions rendered").to.eq(true);
      expect(/multiple operational roles/i.test(text), "no role ambiguity blocker").to.eq(false);
      expect(/POS Awesome Actions/i.test(text), "not stuck on Desk app launcher").to.eq(false);
    });

    cy.wait("@getRelayConnectivityStatus", { timeout: 60000 });
    cy.wait(2000);
    cy.window({ timeout: 60000 }).then((win) => {
      const resourceNames = (win.performance && win.performance.getEntriesByType
        ? win.performance.getEntriesByType("resource").map((r) => r && r.name).filter(Boolean)
        : []
      )
        .filter((name) => /posawesome\.bundle\./i.test(String(name)))
        .slice(-20);
      cy.get("body").then(($body) => {
        const navbarHost = findNavbarVmHost($body);
        const navbarVm = navbarHost && navbarHost.__vue__ ? navbarHost.__vue__ : null;
        const navbarSnapshot = navbarVm
          ? {
              pos_profile_name:
                (navbarVm.pos_profile && navbarVm.pos_profile.name) || navbarVm.pos_profile || "",
              relay_status: { ...(navbarVm.relay_status || {}) },
              cloud_status: { ...(navbarVm.cloud_status || {}) },
              has_relay_poll_timer: !!navbarVm.relay_poll_timer,
              has_cloud_poll_timer: !!navbarVm.cloud_poll_timer,
              current_role: navbarVm.current_role || "",
            }
          : null;

        cy.writeFile("cypress/tmp/local_staging_navbar_debug.json", {
          capturedAt: new Date().toISOString(),
          resourceNames,
          bodySample: (($body.text() || "").replace(/\s+/g, " ").trim() || "").slice(0, 1200),
          navbarSnapshot,
        });
      });
    });

    assertRelayUiAndActual({ relayBase, expectRelayOnline: true, expectCloudOnline: true });

    cy.request({
      method: "GET",
      url: `${relayBase}/health`,
      failOnStatusCode: false,
      timeout: 60000,
    }).then((health) => {
      expect(health.status).to.eq(200);
      expect(health.body && health.body.ok).to.eq(true);

      cy.request({
        method: "GET",
        url: `${relayBase}/api/outbox?limit=10`,
        failOnStatusCode: false,
        timeout: 60000,
      }).then((outbox) => {
        expect(outbox.status).to.eq(200);

        cy.request({
          method: "GET",
          url: `${relayBase}/api/transactions?limit=10`,
          failOnStatusCode: false,
          timeout: 60000,
        }).then((tx) => {
          expect(tx.status).to.eq(200);
          cy.writeFile("cypress/tmp/local_staging_parity_smoke.json", {
            capturedAt: new Date().toISOString(),
            baseUrl: Cypress.config("baseUrl"),
            relayBase,
            relayHealth: health.body,
            outboxCounts: (outbox.body && outbox.body.counts) || null,
            transactionsCount:
              (tx.body && tx.body.counts && tx.body.counts.total) ||
              (Array.isArray(tx.body && tx.body.rows) ? tx.body.rows.length : null),
          });
        });
      });
    });
  });
});
