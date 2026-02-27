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
    submitOtpCodeWithRetry(totpUri, 2);
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

function startPosSessionForRole({ roleStorageValue, roleLabel, profileName }) {
  cy.visit("/app/posapp");
  cy.get("body", { timeout: 60000 }).should("contain.text", "POS");

  cy.get("body").then(($body) => {
    if (($body.text() || "").includes("multiple operational roles")) {
      throw new Error(`Precondition failed: cline has multiple cline-* roles. Expected ${roleStorageValue}.`);
    }
  });

  cy.get("body").then(($body) => {
    const hasRoleDialog = /Role:\s*/i.test($body.text() || "");
    if (!hasRoleDialog) {
      cy.window().then((win) => {
        win.localStorage.setItem("pos_current_role", roleStorageValue);
      });
      cy.reload();
      return;
    }

    cy.contains("Role:", { timeout: 30000 }).should("be.visible");
    cy.contains(roleLabel, { timeout: 30000 }).should("be.visible");

    cy.contains(".v-dialog--active .v-input", "POS Profile", { timeout: 30000 })
      .find("input:not([type='hidden'])")
      .first()
      .should("be.visible")
      .click({ force: true })
      .clear({ force: true })
      .type(profileName, { force: true });

    cy.get("body").then(($body2) => {
      const option = [...$body2.find(".v-list-item__title")].find(
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

    cy.contains(".v-dialog--active .v-btn", /submit/i, { timeout: 30000 }).click({ force: true });
  });
}

function readShellChromeSnapshot(roleKey) {
  return cy.get("body", { timeout: 60000 }).then(($body) => {
    const visibleCount = (selector) =>
      $body
        .find(selector)
        .filter((_, el) => Cypress.$(el).is(":visible")).length;
    const bodyText = ($body.text() || "").replace(/\s+/g, " ").trim();
    const markerElements = [...$body.find("*")]
      .filter((el) => /Search or type a command/i.test((el.textContent || "").trim()))
      .slice(0, 5)
      .map((el) => ({
        tag: el.tagName,
        className: String(el.className || ""),
        id: String(el.id || ""),
        text: String((el.textContent || "").trim()).slice(0, 140),
      }));
    const selectorCounts = {
      navbar: $body.find(".navbar").length,
      deskNavbar: $body.find(".desk-navbar").length,
      pageHead: $body.find(".page-head").length,
      breadcrumb: $body.find(".breadcrumb").length,
      searchBarClass: $body.find(".search-bar").length,
      navbarExpand: $body.find(".navbar-expand").length,
      posAppBar: $body.find(".v-app-bar").length,
      vuetifyToolbar: $body.find(".v-toolbar").length,
    };

    const state = {
      role: roleKey,
      url: Cypress.config("baseUrl"),
      awesomeBarVisible:
        /search or type a command/i.test(bodyText) ||
        visibleCount("input[placeholder*='Search or type a command']") > 0 ||
        visibleCount(".search-bar") > 0,
      deskNavbarVisible:
        visibleCount(".navbar") > 0 ||
        visibleCount("header.navbar") > 0 ||
        visibleCount(".desk-navbar") > 0 ||
        visibleCount(".navbar-expand") > 0,
      pageHeadVisible: visibleCount(".page-head") > 0,
      desktopBreadcrumbVisible: visibleCount(".breadcrumb") > 0 || visibleCount(".no-breadcrumbs") > 0,
      posTopBarVisible: visibleCount(".v-app-bar") > 0,
      posBrandVisible: /POS AWESOME/i.test(($body.text() || "").trim()),
      selectorCounts,
      markerElements,
    };

    return cy.writeFile(`cypress/tmp/ui_shell_chrome_${roleKey}.json`, state).then(() => state);
  });
}

describe("UI shell consistency: ERPNext chrome hidden for all cline roles", () => {
  it("checks SA/Cashier/Picker/Dispatch/Supervisor shell consistency", () => {
    const profileName = "PJ7 CASHIER";
    const loginUser = String(Cypress.env("username") || "").trim();
    const explicitUserDocname = String(Cypress.env("userDocname") || "").trim();
    const otpLabelCandidate = parseLabelFromOtpUri(Cypress.env("totpUri"));

    const roleLabelByKey = {
      sa: "Sales Associate",
      cashier: "Cashier",
      picker: "Picker",
      dispatch: "Dispatch",
      supervisor: "Supervisor",
    };
    const roleNeedlesByKey = {
      sa: ["sales", "associate"],
      cashier: ["cashier"],
      picker: ["picker"],
      dispatch: ["dispatch"],
      supervisor: ["supervisor"],
    };

    let targetUserDocname = "";
    const roleNameByKey = {};

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

      Object.entries(roleNeedlesByKey).forEach(([key, needles]) => {
        const resolved = clineRoles.find((r) => {
          const t = r.toLowerCase();
          return needles.every((n) => t.includes(n));
        });
        expect(resolved, `resolve cline role for ${key}`).to.be.a("string").and.not.be.empty;
        roleNameByKey[key] = resolved;
      });
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
      targetUserDocname = String(targetUser.name || "").trim();
      expect(targetUserDocname).to.not.equal("");
    });

    const roleOrder = ["sa", "cashier", "picker", "dispatch", "supervisor"];
    const snapshots = [];
    roleOrder.forEach((roleKey) => {
      cy.then(() =>
        frappeCall("frappe.client.get", {
          doctype: "User",
          name: targetUserDocname,
        })
      )
        .then((getResp) => {
          const doc = getResp && getResp.message ? getResp.message : null;
          expect(doc, "User doc loaded").to.be.an("object");
          const existingRoles = Array.isArray(doc.roles) ? doc.roles : [];
          const preservedNonClineRoles = existingRoles.filter(
            (r) => !String((r && r.role) || "").startsWith("cline-")
          );
          const targetRole = roleNameByKey[roleKey];
          const existingTarget = existingRoles.find((r) => String((r && r.role) || "") === targetRole);
          const rebuiltRoles = [...preservedNonClineRoles];

          if (existingTarget) {
            rebuiltRoles.push(existingTarget);
          } else {
            rebuiltRoles.push({
              doctype: "Has Role",
              parent: doc.name,
              parenttype: "User",
              parentfield: "roles",
              role: targetRole,
            });
          }

          return frappeCall("frappe.client.save", {
            doc: {
              ...doc,
              roles: rebuiltRoles,
              __unsaved: 1,
            },
          });
        })
        .then((saveResp) => {
          const saved = saveResp && saveResp.message ? saveResp.message : null;
          expect(saved, "Saved User doc response").to.be.an("object");
          const roles = Array.isArray(saved.roles) ? saved.roles : [];
          const clineRoles = roles.map((r) => String((r && r.role) || "")).filter((r) => r.startsWith("cline-"));
          expect(clineRoles, `remaining cline role for ${roleKey}`).to.deep.equal([roleNameByKey[roleKey]]);
        })
        .then(() =>
          startPosSessionForRole({
            roleStorageValue: roleNameByKey[roleKey],
            roleLabel: roleLabelByKey[roleKey],
            profileName,
          })
        )
        .then(() => readShellChromeSnapshot(roleKey))
        .then((state) => {
          snapshots.push(state);
          expect(state.posBrandVisible, `${roleKey}: POS brand text visible`).to.eq(true);
        });
    });

    cy.then(() => {
      expect(snapshots.length, "snapshots collected").to.eq(roleOrder.length);
      return cy.writeFile("cypress/tmp/ui_shell_chrome_role_summary.json", snapshots);
    }).then(() => {
      const chromeFlags = snapshots.map((s) => ({
        role: s.role,
        chromeVisible: Boolean(
          s.awesomeBarVisible || s.deskNavbarVisible || s.pageHeadVisible || s.desktopBreadcrumbVisible
        ),
      }));
      const uniqueChromeStates = [...new Set(chromeFlags.map((f) => String(f.chromeVisible)))];
      expect(uniqueChromeStates, "desk chrome visibility consistent across roles").to.have.length(1);

      const offenders = chromeFlags.filter((f) => f.chromeVisible).map((f) => f.role);
      expect(offenders, "ERPNext desk chrome hidden for every cline role").to.deep.equal([]);
    });
  });
});
