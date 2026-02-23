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
          expect(code).to.match(/^\d{6}$/);

          cy.get(otpSelector, { timeout: 30000 })
            .first()
            .should("be.visible")
            .clear({ force: true })
            .type(code, { log: false });

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
    return submitOtpCodeWithRetry(totpUri, 2);
  });

  cy.location("pathname", { timeout: 90000 }).should("match", /^\/app(\/|$)/);
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

function setField(doctype, name, fieldname, value) {
  return frappeCall("frappe.client.set_value", { doctype, name, fieldname, value });
}

function extractNumeric(text) {
  const num = parseFloat(String(text || "").replace(/[^0-9.-]/g, ""));
  return Number.isFinite(num) ? num : 0;
}

function getDisplayedTotalQty($body) {
  const totalQtyBlock = [...$body.find(".v-input")].find((el) => /total qty/i.test((el.innerText || "").trim()));
  if (!totalQtyBlock) return null;
  const input = totalQtyBlock.querySelector("input");
  if (input && typeof input.value === "string") return extractNumeric(input.value);
  return extractNumeric(totalQtyBlock.innerText || "");
}

function pickFirstUsableRow(selector) {
  return cy.get(selector, { timeout: 60000 }).then(($rows) => {
    const usable = [...$rows].find((el) => {
      const text = (el.innerText || "").trim();
      if (!text) return false;
      if (/no data available/i.test(text)) return false;
      return el.querySelectorAll("td").length > 1;
    });
    return usable || null;
  });
}

function ensureCartHasItem() {
  cy.get("body", { timeout: 30000 }).then(($body) => {
    const totalQty = getDisplayedTotalQty($body);
    expect(totalQty, "cart total qty").to.be.greaterThan(0);
  });
}

function selectProfileInOpeningDialog(profileName) {
  cy.contains(".v-dialog--active .v-input", "POS Profile", { timeout: 30000 })
    .find("input:not([type='hidden'])")
    .first()
    .should("be.visible")
    .click({ force: true })
    .clear({ force: true })
    .type(profileName, { force: true });

  cy.get("body").then(($body) => {
    const option = [...$body.find(".v-list-item__title")].find((el) => (el.innerText || "").trim() === profileName);
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

describe("Cashier regression: POS works when custom_have_token is disabled", () => {
  const profileName = "PJ7 CASHIER";
  let originalHaveToken = 1;

  after(() => {
    loginWithOtp();
    cy.visit("/app");
    setField("POS Profile", profileName, "custom_have_token", originalHaveToken);
    frappeCall("frappe.client.get", { doctype: "POS Profile", name: profileName }).then((resp) => {
      const doc = resp?.message || {};
      expect(Number(doc.custom_have_token || 0), "custom_have_token restored").to.eq(Number(originalHaveToken || 0));
    });
  });

  it("opens cashier POS and payment screen with token workflow disabled", () => {
    cy.intercept("POST", "**/api/method/posawesome.posawesome.api.posapp.get_items").as("getItems");

    loginWithOtp();
    cy.visit("/app");

    frappeCall("frappe.client.get", { doctype: "POS Profile", name: profileName }).then((resp) => {
      const doc = resp?.message || {};
      expect(doc, `POS Profile ${profileName}`).to.be.an("object");
      expect(doc).to.have.property("custom_have_token");
      originalHaveToken = Number(doc.custom_have_token || 0);
      return setField("POS Profile", profileName, "custom_have_token", 0);
    });

    frappeCall("frappe.client.get", { doctype: "POS Profile", name: profileName }).then((resp) => {
      const doc = resp?.message || {};
      expect(Number(doc.custom_have_token || 0), "custom_have_token disabled for test").to.eq(0);
    });

    cy.visit("/app/posapp");
    cy.get("body", { timeout: 60000 }).should("contain.text", "POS");

    cy.get("body").then(($body) => {
      const hasRoleDialog = /Role:\s*/i.test($body.text() || "");
      if (!hasRoleDialog) {
        cy.log("Existing POS session reused; proceeding.");
        return;
      }

      cy.contains("Role:", { timeout: 30000 }).should("be.visible");
      cy.contains("Cashier", { timeout: 30000 }).should("be.visible");
      cy.contains(".v-dialog--active .v-card__title", "Create POS Opening Shift", { timeout: 30000 }).should(
        "be.visible"
      );
      selectProfileInOpeningDialog(profileName);
      cy.contains(".v-dialog--active .v-btn", /submit/i, { timeout: 30000 }).click({ force: true });
      cy.contains(".v-dialog--active .v-card__title", "Create POS Opening Shift", { timeout: 30000 }).should(
        "not.exist"
      );
    });

    cy.wait("@getItems", { timeout: 120000 }).then((interception) => {
      const status = interception?.response?.statusCode;
      if (typeof status === "number") {
        expect(status).to.eq(200);
      }
    });

    cy.get("body", { timeout: 30000 }).should("not.contain.text", "Server Error");
    cy.get("body").should("contain.text", "PAY");

    pickFirstUsableRow(".selection .v-data-table tbody tr").then((row) => {
      if (!row) {
        throw new Error("No sellable item row found for token-disabled cashier smoke test.");
      }
      cy.wrap(row).click({ force: true });
    });

    cy.wait(500);
    ensureCartHasItem();

    cy.contains(".v-btn", "PAY", { timeout: 30000 }).click({ force: true });
    cy.get("body", { timeout: 30000 }).should("contain.text", "Paid Amount");

    // The relay-token configuration blocker should not appear when token workflow is disabled.
    cy.get("body").should(
      "not.contain.text",
      "Relay workflow is enabled but Edge Relay URL is not configured for this POS Profile."
    );
  });
});
