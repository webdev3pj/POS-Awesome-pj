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
    const pwdSelector = findFirstSelector($body, ["#login_password", "input[name='pwd']", "input[type='password']"]);
    expect(pwdSelector, "password field selector").to.be.a("string");

    cy.get(pwdSelector, { timeout: 30000 })
      .first()
      .should("be.visible")
      .then(($pwd) => {
        const $form = $pwd.closest("form");
        if ($form.length) {
          const loginBtn = $form.find("button, .btn").filter((_, el) => /^login$/i.test((el.innerText || "").trim()));
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
                throw new Error("OTP verification failed after retries. Check server time and OTP secret.");
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
    return submitOtpCodeWithRetry(totpUri, 2);
  });

  cy.location("pathname", { timeout: 90000 }).should("match", /^\/app(\/|$)/);
}

function frappeCall(method, args) {
  return cy.window({ timeout: 30000 }).then((win) => {
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
  return frappeCall("frappe.client.set_value", {
    doctype,
    name,
    fieldname,
    value,
  });
}

function getSalesOrderNamingSeriesOptions() {
  return cy.window({ timeout: 30000 }).then((win) => {
    return new Cypress.Promise((resolve, reject) => {
      try {
        win.frappe.model.with_doctype("Sales Order", () => {
          try {
            const df = win.frappe.meta.get_docfield("Sales Order", "naming_series");
            const options = String((df && df.options) || "")
              .split(/\r?\n/)
              .map((v) => String(v || "").trim())
              .filter(Boolean);
            resolve(options);
          } catch (e) {
            reject(e);
          }
        });
      } catch (e) {
        reject(e);
      }
    });
  });
}

describe("Admin preflight: configure PJ7 CASHIER POS Profile for SA token testing", () => {
  it("ensures token flags, configures SO naming series, and sets Select S.O max age", () => {
    const profileName = "PJ7 CASHIER";
    const requiredSoSeries = "SAL-ORD-PJ7-.YYYY.-";
    let chosenSalesOrderSeries = "";

    loginWithOtp();
    cy.visit("/app");

    getSalesOrderNamingSeriesOptions()
      .then((soSeriesOptions) => {
        expect(soSeriesOptions, "Sales Order naming series options").to.be.an("array").and.not.be.empty;
        return frappeCall("frappe.client.get", {
          doctype: "POS Profile",
          name: profileName,
        }).then((resp) => ({ soSeriesOptions, resp }));
      })
      .then(({ soSeriesOptions, resp }) => {
        const doc = resp && resp.message ? resp.message : null;
        expect(doc, `POS Profile ${profileName} exists`).to.be.an("object");

        const requiredFlags = [
          ["custom_have_token", 1],
          ["posa_allow_sales_order", 1],
          ["custom_allow_select_sales_order", 1],
        ];

        const updates = [];
        requiredFlags.forEach(([fieldname, desired]) => {
          if (!(fieldname in doc)) {
            throw new Error(
              `POS Profile field missing: ${fieldname}. Ensure latest custom fields are installed/migrated.`
            );
          }
          const current = Number(doc[fieldname] || 0);
          if (current !== desired) {
            updates.push([fieldname, desired]);
          }
        });

        ["posa_sales_order_naming_series", "posa_sales_order_lookup_max_age_days"].forEach((fieldname) => {
          if (!(fieldname in doc)) {
            throw new Error(
              `POS Profile field missing: ${fieldname}. Deploy/migrate the naming-series feature first, then rerun this spec.`
            );
          }
        });

        const cleanedOptions = soSeriesOptions.map((v) => String(v || "").trim()).filter(Boolean);
        const standardSeries = cleanedOptions[0] || "";
        chosenSalesOrderSeries = cleanedOptions.find((v) => v === requiredSoSeries) || "";

        if (!chosenSalesOrderSeries) {
          throw new Error(
            `Required Sales Order naming series not found for test profile ${profileName}: ${requiredSoSeries}. Available: ${cleanedOptions.join(", ")}`
          );
        }

        if (String(doc.posa_sales_order_naming_series || "").trim() !== chosenSalesOrderSeries) {
          updates.push(["posa_sales_order_naming_series", chosenSalesOrderSeries]);
        }
        if (Number(doc.posa_sales_order_lookup_max_age_days || 1) !== 1) {
          updates.push(["posa_sales_order_lookup_max_age_days", 1]);
        }

        cy.log(`SO series options: ${cleanedOptions.join(", ")}`);
        cy.log(`SO standard(default candidate): ${standardSeries || "(none)"}`);
        cy.log(`SO test series selected (required): ${chosenSalesOrderSeries}`);
        cy.log(`POS Profile company: ${doc.company || "(missing)"}`);
        cy.log(`POS Profile warehouse: ${doc.warehouse || "(missing)"}`);
        cy.log(`POS Profile price list: ${doc.selling_price_list || "(missing)"}`);

        const payments =
          (Array.isArray(doc.payments) && doc.payments.length) ||
          (Array.isArray(doc.payment_methods) && doc.payment_methods.length) ||
          0;
        cy.log(`POS Profile payments rows: ${payments}`);

        if (!doc.company || !doc.warehouse || !doc.selling_price_list) {
          throw new Error(
            "POS Profile is missing one or more basic fields (company/warehouse/selling_price_list). Fix profile setup before SA/Cashier UAT."
          );
        }
        if (!payments) {
          throw new Error(
            "POS Profile has no payment method rows. Fix POS Profile payment setup before SA/Cashier UAT."
          );
        }

        if (!updates.length) {
          cy.log("PJ7 CASHIER flags + SO naming series + age filter already configured.");
          return null;
        }

        cy.log(`Updating profile fields: ${updates.map(([k, v]) => `${k}=${v}`).join(", ")}`);
        return updates.reduce((chain, [fieldname, desired]) => {
          return chain.then(() => setField("POS Profile", profileName, fieldname, desired));
        }, Cypress.Promise.resolve());
      })
      .then(() => {
        return frappeCall("frappe.client.get", {
          doctype: "POS Profile",
          name: profileName,
        });
      })
      .then((verifyResp) => {
        const doc = verifyResp && verifyResp.message ? verifyResp.message : null;
        expect(doc, "reloaded POS Profile").to.be.an("object");
        expect(Number(doc.custom_have_token || 0), "custom_have_token").to.eq(1);
        expect(Number(doc.posa_allow_sales_order || 0), "posa_allow_sales_order").to.eq(1);
        expect(Number(doc.custom_allow_select_sales_order || 0), "custom_allow_select_sales_order").to.eq(1);
        expect(Number(doc.posa_sales_order_lookup_max_age_days || 0), "posa_sales_order_lookup_max_age_days").to.eq(1);
        expect(String(doc.posa_sales_order_naming_series || "").trim(), "posa_sales_order_naming_series").to.not.equal("");
        if (chosenSalesOrderSeries) {
          expect(String(doc.posa_sales_order_naming_series || "").trim()).to.eq(chosenSalesOrderSeries);
        }

        cy.writeFile("cypress/tmp/pj7_cashier_profile_runtime.json", {
          profile: profileName,
          soNamingSeries: String(doc.posa_sales_order_naming_series || "").trim(),
          soLookupMaxAgeDays: Number(doc.posa_sales_order_lookup_max_age_days || 1),
        });

        cy.visit(`/app/pos-profile/${encodeURIComponent(profileName)}`);
        cy.location("pathname", { timeout: 30000 }).should("include", "/app/pos-profile/");
        cy.get("body", { timeout: 60000 }).should("contain.text", profileName);
        cy.get("body").should("contain.text", "Sales Order Naming Series");
        cy.get("body").should("contain.text", "Select S.O Max Age (Days)");
      });
  });
});
