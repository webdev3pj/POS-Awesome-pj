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
    });
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

describe("Admin preflight: set cline to SA-only operational role", () => {
  it("keeps non-cline roles but leaves only cline-Sales Associate among cline-* roles", () => {
    let targetOperationalRole = "cline-Sales Associate";
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

      const exact = clineRoles.find((r) => r === "cline-Sales Associate");
      const caseInsensitive = clineRoles.find(
        (r) => r.toLowerCase() === "cline-sales associate".toLowerCase()
      );
      const fuzzy = clineRoles.find((r) => {
        const t = r.toLowerCase();
        return t.includes("sales") && t.includes("associate");
      });

      const resolved = exact || caseInsensitive || fuzzy || "";
      if (!resolved) {
        throw new Error(
          [
            "Precondition failed: No Sales Associate cline role exists on this site.",
            `Available cline-* roles: ${clineRoles.length ? clineRoles.join(", ") : "(none)"}`,
            "Fix by ensuring role fixtures are installed/migrated, then rerun this spec.",
          ].join(" ")
        );
      }

      targetOperationalRole = resolved;
      cy.log(`Resolved SA operational role: ${targetOperationalRole}`);
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
    });
  });
});
