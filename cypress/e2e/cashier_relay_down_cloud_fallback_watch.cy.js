const { assertRelayUiAndActual } = require("./_helpers/relay_ui_sync");

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

function pickFirstUsableRow(selector, maxRetries = 4) {
  const attempt = (retryIndex = 0) => {
    return cy.get("body", { timeout: 60000 }).then(($body) => {
      const rows = [...$body.find(selector || ".selection .v-data-table tbody tr")];
      const usableRow = rows.find((el) => {
        const text = (el.innerText || "").trim();
        if (!text) return false;
        if (/no data available/i.test(text)) return false;
        return el.querySelectorAll("td").length > 1 && Cypress.$(el).is(":visible");
      });
      if (usableRow) return usableRow;

      const usableCard = [...$body.find(".selection .v-card")].find((el) => {
        const text = (el.innerText || "").trim();
        if (!text) return false;
        if (/no data available/i.test(text)) return false;
        return Cypress.$(el).is(":visible");
      });
      if (usableCard) return usableCard;

      if (retryIndex >= maxRetries) return null;
      cy.wait(1500);
      return attempt(retryIndex + 1);
    });
  };

  return attempt(0);
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

function ensureCartHasItem() {
  cy.get("body", { timeout: 30000 }).then(($body) => {
    const totalQty = getDisplayedTotalQty($body);
    expect(totalQty, "cart total qty").to.be.greaterThan(0);
  });
}

function selectFirstSalesOrderIntoCart() {
  cy.contains(".v-btn", "Select S.O", { timeout: 30000 }).click({ force: true });
  cy.contains(".v-dialog--active .headline", "Select Sales Orders", { timeout: 30000 }).should("be.visible");

  return pickFirstUsableRow(".v-dialog--active .v-data-table tbody tr").then((row) => {
    if (!row) {
      throw new Error("No selectable Sales Order rows found for relay fallback cashier test.");
    }
    const rowEl = row && row.jquery ? row.get(0) : row;
    const checkbox =
      rowEl && typeof rowEl.querySelector === "function"
        ? rowEl.querySelector(".v-simple-checkbox, [role='checkbox'], .v-input--selection-controls__ripple")
        : Cypress.$(row).find(".v-simple-checkbox, [role='checkbox'], .v-input--selection-controls__ripple").get(0);
    if (checkbox) {
      cy.wrap(checkbox).click({ force: true });
    } else {
      cy.wrap(rowEl || row).click({ force: true });
    }
    cy.contains(".v-dialog--active .v-btn", /^Select$/i, { timeout: 30000 }).click({ force: true });
    cy.wait("@createInvoiceFromOrder", { timeout: 120000 }).its("response.statusCode").should("eq", 200);
    cy.contains(".v-dialog--active .headline", "Select Sales Orders", { timeout: 30000 }).should("not.exist");
  });
}

describe("Cashier relay-down cloud fallback (watch mode)", () => {
  const profileName = "PJ7 CASHIER";
  const downRelayUrl = "https://192.168.50.250";
  let originalProfile = {
    custom_have_token: 1,
    custom_edge_relay_url: "",
    posa_edge_relay_connectivity_mode: "cloud_checked",
    posa_allow_cloud_fallback_when_relay_down: 0,
  };

  after(() => {
    cy.location("pathname", { timeout: 10000 }).then((pathname) => {
      const onApp = /^\/app(\/|$)/.test(String(pathname || ""));
      if (!onApp) {
        loginWithOtp();
        cy.visit("/app");
      } else {
        cy.visit("/app");
      }

      setField("POS Profile", profileName, "custom_have_token", originalProfile.custom_have_token);
      setField("POS Profile", profileName, "custom_edge_relay_url", originalProfile.custom_edge_relay_url || "");
      setField(
        "POS Profile",
        profileName,
        "posa_edge_relay_connectivity_mode",
        originalProfile.posa_edge_relay_connectivity_mode || "cloud_checked"
      );
      setField(
        "POS Profile",
        profileName,
        "posa_allow_cloud_fallback_when_relay_down",
        originalProfile.posa_allow_cloud_fallback_when_relay_down || 0
      );
    });
  });

  it("prompts and submits to cloud when relay is down but cloud is reachable", () => {
    let confirmSeen = false;

    cy.intercept("POST", "**/api/method/posawesome.posawesome.api.posapp.get_items").as("getItems");
    cy.intercept("POST", "**/api/method/posawesome.posawesome.api.posapp.create_sales_invoice_from_order").as(
      "createInvoiceFromOrder"
    );
    cy.intercept("POST", "**/api/method/posawesome.posawesome.api.posapp.submit_invoice").as("submitInvoiceCloud");

    cy.on("window:confirm", (text) => {
      confirmSeen = true;
      expect(String(text || "")).to.include("cloud");
      expect(String(text || "")).to.match(/relay/i);
      return true;
    });

    loginWithOtp();
    cy.visit("/app");

    frappeCall("frappe.client.get", { doctype: "POS Profile", name: profileName }).then((resp) => {
      const doc = resp?.message || {};
      expect(doc, `POS Profile ${profileName}`).to.be.an("object");

      [
        "custom_have_token",
        "custom_edge_relay_url",
        "posa_edge_relay_connectivity_mode",
        "posa_allow_cloud_fallback_when_relay_down",
      ].forEach((fieldname) => {
        expect(doc, `POS Profile field ${fieldname}`).to.have.property(fieldname);
      });

      originalProfile = {
        custom_have_token: Number(doc.custom_have_token || 0),
        custom_edge_relay_url: String(doc.custom_edge_relay_url || "").trim(),
        posa_edge_relay_connectivity_mode: String(doc.posa_edge_relay_connectivity_mode || "").trim() || "cloud_checked",
        posa_allow_cloud_fallback_when_relay_down: Number(doc.posa_allow_cloud_fallback_when_relay_down || 0),
      };

      const updates = [
        ["custom_have_token", 1],
        ["custom_edge_relay_url", downRelayUrl],
        ["posa_edge_relay_connectivity_mode", "lan_only_browser_checked"],
        ["posa_allow_cloud_fallback_when_relay_down", 1],
      ];
      return updates.reduce((chain, [fieldname, value]) => {
        return chain.then(() => setField("POS Profile", profileName, fieldname, value));
      }, Cypress.Promise.resolve());
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
      cy.contains(".v-dialog--active .v-card__title", "Create POS Opening Shift", { timeout: 30000 }).should("be.visible");
      selectProfileInOpeningDialog(profileName);
      cy.contains(".v-dialog--active .v-btn", /submit/i, { timeout: 30000 }).click({ force: true });
      cy.contains(".v-dialog--active .v-card__title", "Create POS Opening Shift", { timeout: 30000 }).should("not.exist");
    });

    cy.wait(3000);
    cy.get("@getItems.all").then((calls) => {
      const list = Array.isArray(calls) ? calls : [];
      if (!list.length) {
        cy.log("get_items was not re-fired; continuing with rendered item grid checks.");
        return;
      }
      const last = list[list.length - 1];
      const status = last?.response?.statusCode;
      if (typeof status === "number") {
        expect(status, "latest get_items status").to.eq(200);
      } else {
        cy.log("get_items intercept had no response object (cached/aborted path); continuing with UI checks.");
      }
    });

    cy.request("http://127.0.0.1:8787/health").its("body.ok").should("eq", true);
    cy.get("body", { timeout: 60000 }).should(($body) => {
      const text = ($body.text() || "").replace(/\s+/g, " ");
      expect(text).to.match(/relay/i);
    });
    assertRelayUiAndActual({
      relayBase: "http://127.0.0.1:8787",
      expectRelayOnline: false,
      expectCloudOnline: true,
      skipActualRelayHealth: true,
    });

    pickFirstUsableRow(".selection .v-data-table tbody tr").then((row) => {
      if (!row) {
        cy.log("No sellable item row/card visible; falling back to Select S.O path.");
        return selectFirstSalesOrderIntoCart();
      }
      cy.wrap(row).click({ force: true });
    });

    cy.wait(500);
    ensureCartHasItem();

    cy.contains(".v-btn", "PAY", { timeout: 30000 }).click({ force: true });
    cy.get("body", { timeout: 30000 }).should("contain.text", "Paid Amount");

    cy.get("body").then(($body) => {
      const totalToBePaidInput = [...$body.find("input")].find((el) => {
        const wrap = el.closest(".v-input");
        return wrap && /to be paid/i.test((wrap.innerText || "").trim());
      });
      const paidAmountInput = [...$body.find("input")].find((el) => {
        const wrap = el.closest(".v-input");
        return wrap && /paid amount/i.test((wrap.innerText || "").trim());
      });
      if (totalToBePaidInput && paidAmountInput) {
        const totalValue = String(totalToBePaidInput.value || "").trim();
        cy.wrap(paidAmountInput).clear({ force: true }).type(totalValue || "0", { force: true });
      }
    });

    cy.get("body").then(($body) => {
      const paymentButtons = $body
        .find(".v-btn.pyments:visible, .pyments.v-btn:visible, .pyments .v-btn:visible")
        .toArray();
      if (paymentButtons.length) {
        cy.wrap(paymentButtons[0]).click({ force: true });
      }
    });

    cy.contains(".v-btn", /^Submit$/i, { timeout: 30000 }).click({ force: true });

    assertRelayUiAndActual({
      relayBase: "http://127.0.0.1:8787",
      expectRelayOnline: false,
      expectCloudOnline: true,
      skipActualRelayHealth: true,
    });

    cy.wait("@submitInvoiceCloud", { timeout: 120000 }).then((interception) => {
      expect(confirmSeen, "relay-down cloud-fallback confirmation prompt seen").to.eq(true);
      expect(interception?.response?.statusCode, "cloud submit status").to.eq(200);
      const reqBody = interception?.request?.body;
      if (reqBody && typeof reqBody === "object") {
        const data = reqBody.data || reqBody.args?.data;
        expect(data, "submit_invoice request data payload").to.exist;
      }
    });

    cy.get("body", { timeout: 60000 }).then(($body) => {
      const text = ($body.text() || "").replace(/\s+/g, " ");
      expect(
        text.includes("Submitting to cloud (relay fallback confirmed by cashier).") ||
          /Invoice\s+[^\s]+\s+is\s+Submited/i.test(text) ||
          text.includes("The amount paid is not complete"),
        "fallback path should prompt and attempt cloud submit"
      ).to.eq(true);
    });
  });
});
