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
  const maybeCompleteOtp = () => {
    cy.wait(1500);
    return cy.get("body", { timeout: 30000 }).then(($body) => {
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
  };

  const runLoginRound = () => {
    typeIntoFirstAvailable(
      ["#login_email", "input[name='usr']", "input[name='login_email']", "input[type='email']"],
      username
    );
    typeIntoFirstAvailable(["#login_password", "input[name='pwd']", "input[type='password']"], password, {
      log: false,
    });
    clickLoginSubmitNearPassword();
    return maybeCompleteOtp();
  };

  cy.visit("/login");
  runLoginRound();

  cy.location("pathname", { timeout: 5000 }).then((pathname) => {
    if (/^\/app(\/|$)/.test(String(pathname || ""))) return;

    cy.get("body").then(($body) => {
      const stillOnLoginForm =
        !!findFirstSelector($body, ["#login_email", "input[name='usr']", "input[name='login_email']", "input[type='email']"]) &&
        !!findFirstSelector($body, ["#login_password", "input[name='pwd']", "input[type='password']"]);
      if (!stillOnLoginForm) return;

      cy.log("Login submit did not advance on first attempt; retrying once.");
      typeIntoFirstAvailable(
        ["#login_email", "input[name='usr']", "input[name='login_email']", "input[type='email']"],
        username
      );
      typeIntoFirstAvailable(["#login_password", "input[name='pwd']", "input[type='password']"], password, {
        log: false,
      });
      clickLoginSubmitNearPassword();
      maybeCompleteOtp();
    });
  });

  cy.location("pathname", { timeout: 10000 }).then((pathname) => {
    if (/^\/app(\/|$)/.test(String(pathname || ""))) return;
    cy.log("Still on login after in-page retry; doing one full login round from fresh /login.");
    cy.visit("/login");
    runLoginRound();
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

function parseLabelFromOtpUri(uri) {
  try {
    const text = String(uri || "");
    const marker = "otpauth://totp/";
    const idx = text.indexOf(marker);
    if (idx === -1) return "";
    const after = text.slice(idx + marker.length);
    const pathPart = after.split("?")[0] || "";
    const decoded = decodeURIComponent(pathPart);
    const label = decoded.includes(":") ? decoded.split(":").slice(1).join(":") : decoded;
    return (label || "").trim();
  } catch (e) {
    return "";
  }
}

function setField(doctype, name, fieldname, value) {
  return frappeCall("frappe.client.set_value", {
    doctype,
    name,
    fieldname,
    value,
  });
}

describe("Admin preflight: set cline to Cashier-only operational role", () => {
  it("keeps non-cline roles but leaves only cline-Cashier among cline-* roles", () => {
    let targetOperationalRole = "cline-Cashier";
    const profileName = "PJ7 CASHIER";
    const loginUser = String(Cypress.env("username") || "").trim();
    const explicitUserDocname = String(Cypress.env("userDocname") || "").trim();
    const otpLabelCandidate = parseLabelFromOtpUri(Cypress.env("totpUri"));

    loginWithOtp();
    cy.visit("/app");

    frappeCall("frappe.client.get_list", {
      doctype: "Role",
      fields: ["name"],
      limit_page_length: 1000,
    }).then((roleResp) => {
      const roleRows = Array.isArray(roleResp && roleResp.message) ? roleResp.message : [];
      const roleNames = roleRows.map((r) => String((r && r.name) || "").trim()).filter(Boolean);
      const clineRoles = roleNames.filter((name) => name.startsWith("cline-"));

      const exact = clineRoles.find((r) => r === "cline-Cashier");
      const caseInsensitive = clineRoles.find(
        (r) => r.toLowerCase() === "cline-cashier".toLowerCase()
      );
      const fuzzy = clineRoles.find((r) => {
        const t = r.toLowerCase();
        return t.includes("cashier");
      });

      const resolved = exact || caseInsensitive || fuzzy || "";
      if (!resolved) {
        throw new Error(
            [
            "Precondition failed: No Cashier cline role exists on this site.",
            `Available cline-* roles: ${clineRoles.length ? clineRoles.join(", ") : "(none)"}`,
            "Fix by ensuring role fixtures are installed/migrated, then rerun this spec.",
          ].join(" ")
        );
      }

      targetOperationalRole = resolved;
      cy.log(`Resolved Cashier operational role: ${targetOperationalRole}`);
    });

    frappeCall("frappe.client.get_list", {
      doctype: "User",
      fields: ["name", "email", "username", "enabled"],
      limit_page_length: 200,
      filters: { enabled: 1 },
    }).then((resp) => {
      const users = Array.isArray(resp && resp.message) ? resp.message : [];
      const candidates = [
        explicitUserDocname,
        loginUser,
        otpLabelCandidate,
        loginUser.includes("@") ? loginUser.split("@")[0] : "",
      ]
        .map((v) => String(v || "").trim())
        .filter(Boolean);

      const targetUser =
        users.find((u) =>
          candidates.some(
            (c) =>
              String(u.name || "").trim() === c ||
              String(u.email || "").trim() === c ||
              String(u.username || "").trim() === c
          )
        ) || null;

      expect(targetUser, `resolve User record for candidates: ${candidates.join(", ")}`).to.not.equal(null);

      const targetDocname = String(targetUser.name || "").trim();
      cy.wrap(targetDocname, { log: true }).as("targetUserDocname");
      cy.log(`Resolved User doc: ${targetDocname}`);

      cy.visit(`/app/user/${encodeURIComponent(targetDocname)}`);
      cy.location("pathname", { timeout: 30000 }).should("include", "/app/user/");
      cy.get("body", { timeout: 60000 }).should("contain.text", "User");

      return frappeCall("frappe.client.get", {
        doctype: "User",
        name: targetDocname,
      });
    }).then((getResp) => {
      const doc = getResp && getResp.message ? getResp.message : null;
      expect(doc, "User doc loaded").to.be.an("object");
      expect(String(doc.doctype || "")).to.eq("User");

      const existingRoles = Array.isArray(doc.roles) ? doc.roles : [];
      const preservedNonClineRoles = existingRoles.filter(
        (r) => !String((r && r.role) || "").startsWith("cline-")
      );
      const existingTarget = existingRoles.find((r) => String((r && r.role) || "") === targetOperationalRole);

      const rebuiltRoles = [...preservedNonClineRoles];

      if (existingTarget) {
        rebuiltRoles.push(existingTarget);
      } else {
        rebuiltRoles.push({
          doctype: "Has Role",
          parent: doc.name,
          parenttype: "User",
          parentfield: "roles",
          role: targetOperationalRole,
        });
      }

      const newDoc = {
        ...doc,
        roles: rebuiltRoles,
        __unsaved: 1,
      };

      return frappeCall("frappe.client.save", {
        doc: newDoc,
      });
    }).then((saveResp) => {
      const saved = saveResp && saveResp.message ? saveResp.message : null;
      expect(saved, "Saved User doc response").to.be.an("object");
      const roles = Array.isArray(saved.roles) ? saved.roles : [];
      const clineRoles = roles.map((r) => String((r && r.role) || "")).filter((r) => r.startsWith("cline-"));

      expect(clineRoles, "remaining cline-* roles").to.deep.equal([targetOperationalRole]);
      cy.log(`Operational roles now: ${clineRoles.join(", ")}`);

      // Reload the User form so the change is visible in the UI for watch mode.
      cy.reload();
      cy.get("body", { timeout: 60000 }).should("contain.text", targetOperationalRole);

      // Preflight POS Profile config for SA token tests (minimize manual setup/deploy loops).
      return frappeCall("frappe.client.get", {
        doctype: "POS Profile",
        name: profileName,
      });
    }).then((profileResp) => {
      const profile = profileResp && profileResp.message ? profileResp.message : null;
      expect(profile, `POS Profile ${profileName} exists`).to.be.an("object");

      const requiredFlags = [
        ["custom_have_token", 1],
        ["posa_allow_sales_order", 1],
        ["custom_allow_select_sales_order", 1],
      ];

      requiredFlags.forEach(([fieldname]) => {
        expect(fieldname in profile, `POS Profile field exists: ${fieldname}`).to.eq(true);
      });

      expect(String(profile.company || "").trim(), "POS Profile company").to.not.equal("");
      expect(String(profile.warehouse || "").trim(), "POS Profile warehouse").to.not.equal("");
      expect(String(profile.selling_price_list || "").trim(), "POS Profile selling_price_list").to.not.equal("");

      const paymentsCount =
        (Array.isArray(profile.payments) && profile.payments.length) ||
        (Array.isArray(profile.payment_methods) && profile.payment_methods.length) ||
        0;
      expect(paymentsCount, "POS Profile payment rows").to.be.greaterThan(0);

      const updates = requiredFlags.filter(([fieldname, desired]) => Number(profile[fieldname] || 0) !== desired);
      if (!updates.length) {
        cy.log("PJ7 CASHIER profile token/SO flags already enabled.");
        return null;
      }

      cy.log(`Updating PJ7 CASHIER flags: ${updates.map(([k, v]) => `${k}=${v}`).join(", ")}`);
      return updates.reduce((chain, [fieldname, desired]) => {
        return chain.then(() => setField("POS Profile", profileName, fieldname, desired));
      }, Cypress.Promise.resolve());
    }).then(() => {
      return frappeCall("frappe.client.get", {
        doctype: "POS Profile",
        name: profileName,
      });
    }).then((verifyProfileResp) => {
      const profile = verifyProfileResp && verifyProfileResp.message ? verifyProfileResp.message : null;
      expect(profile, "reloaded POS Profile").to.be.an("object");
      expect(Number(profile.custom_have_token || 0), "custom_have_token").to.eq(1);
      expect(Number(profile.posa_allow_sales_order || 0), "posa_allow_sales_order").to.eq(1);
      expect(Number(profile.custom_allow_select_sales_order || 0), "custom_allow_select_sales_order").to.eq(1);
      cy.log(
        `Relay URL configured: ${String(profile.custom_edge_relay_url || "").trim() ? "yes" : "no"}`
      );

      // Preflight data sanity: ensure this POS Profile can actually load at least one item.
      return frappeCall("posawesome.posawesome.api.posapp.get_items", {
        pos_profile: JSON.stringify(profile),
        item_group: "",
        search_value: "",
      }, { timeout: 120000 }).then((itemsResp) => {
        const items = Array.isArray(itemsResp && itemsResp.message) ? itemsResp.message : [];
        expect(
          items.length,
          [
            `PJ7 CASHIER POS items loaded (${items.length}).`,
            "If zero, check Item Price entries for the profile selling price list/currency, warehouse stock filters, and POS profile item visibility settings.",
          ].join(" "),
        ).to.be.greaterThan(0);
        cy.log(`PJ7 CASHIER get_items returned ${items.length} item(s).`);
      });
    });
  });
});
