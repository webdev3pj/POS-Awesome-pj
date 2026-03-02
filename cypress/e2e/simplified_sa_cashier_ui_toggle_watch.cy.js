const { loginWithOtp, frappeCall } = require("./_helpers/pos_auth");

const PROFILE_NAME = "PJ7 CASHIER";
const FIELDNAME = "posa_simplified_sa_cashier_ui";

function resolveOperationalRole(target) {
  const wanted = String(target || "").trim().toLowerCase();
  return frappeCall("frappe.client.get_list", {
    doctype: "Role",
    fields: ["name"],
    limit_page_length: 1000,
  }).then((resp) => {
    const roles = Array.isArray(resp && resp.message) ? resp.message : [];
    const names = roles.map((r) => String((r && r.name) || "").trim()).filter(Boolean);
    const clineRoles = names.filter((n) => n.startsWith("cline-"));
    let role = "";
    if (wanted === "sa") {
      role =
        clineRoles.find((n) => n === "cline-Sales Associate") ||
        clineRoles.find((n) => n.toLowerCase() === "cline-sales associate");
    } else if (wanted === "cashier") {
      role = clineRoles.find((n) => n === "cline-Cashier") || clineRoles.find((n) => n.toLowerCase() === "cline-cashier");
    }
    expect(role, `resolved cline role for ${target}`).to.be.a("string").and.not.be.empty;
    return role;
  });
}

function getLoggedUserDocname() {
  return frappeCall("frappe.auth.get_logged_user", {}).then((resp) => {
    const user = String((resp && resp.message) || "").trim();
    expect(user, "logged user docname").to.be.a("string").and.not.be.empty;
    return user;
  });
}

function setOnlyOperationalRole(userDocname, targetRoleName) {
  return frappeCall("frappe.client.get", {
    doctype: "User",
    name: userDocname,
  }).then((resp) => {
    const doc = (resp && resp.message) || {};
    expect(String(doc.doctype || ""), "User doc loaded").to.eq("User");
    const currentRoles = Array.isArray(doc.roles) ? doc.roles : [];
    const preservedNonCline = currentRoles.filter((r) => !String((r && r.role) || "").startsWith("cline-"));
    const targetExisting = currentRoles.find((r) => String((r && r.role) || "") === targetRoleName);
    const rebuiltRoles = [...preservedNonCline];
    if (targetExisting) {
      rebuiltRoles.push(targetExisting);
    } else {
      rebuiltRoles.push({
        doctype: "Has Role",
        parent: doc.name,
        parenttype: "User",
        parentfield: "roles",
        role: targetRoleName,
      });
    }
    const nextDoc = {
      ...doc,
      roles: rebuiltRoles,
      __unsaved: 1,
    };
    return frappeCall("frappe.client.save", { doc: nextDoc });
  });
}

function setSimplifiedToggle(value) {
  return frappeCall("frappe.client.get", {
    doctype: "POS Profile",
    name: PROFILE_NAME,
  }).then((resp) => {
    const profile = (resp && resp.message) || {};
    expect(profile, `POS Profile ${PROFILE_NAME} exists`).to.be.an("object");
    expect(FIELDNAME in profile, `${FIELDNAME} field exists on cloud`).to.eq(true);
    return frappeCall("frappe.client.set_value", {
      doctype: "POS Profile",
      name: PROFILE_NAME,
      fieldname: FIELDNAME,
      value: Number(value || 0),
    });
  });
}

function openPosWithRole(roleName) {
  cy.visit("/app/posapp", {
    onBeforeLoad(win) {
      try {
        win.localStorage.setItem("pos_current_role", roleName);
      } catch (_e) {}
    },
  });
  cy.get("body", { timeout: 60000 }).should("contain.text", "POS AWESOME");
}

function assertButtonVisible(label, visible = true) {
  const matcher = new RegExp(`^${label}$`, "i");
  if (visible) {
    cy.contains(".v-btn", matcher, { timeout: 30000 }).should("be.visible");
    return;
  }
  cy.contains(".v-btn", matcher, { timeout: 10000 }).should("not.exist");
}

describe("Simplified SA and Cashier UI toggle (cloud)", () => {
  it("toggles SA button simplification on/off while keeping cashier actions", () => {
    let userDocname = "";
    let saRoleName = "";
    let cashierRoleName = "";

    loginWithOtp();
    cy.visit("/app");

    getLoggedUserDocname().then((name) => {
      userDocname = name;
    });
    resolveOperationalRole("sa").then((name) => {
      saRoleName = name;
    });
    resolveOperationalRole("cashier").then((name) => {
      cashierRoleName = name;
    });

    cy.then(() => setSimplifiedToggle(1));

    cy.then(() => setOnlyOperationalRole(userDocname, saRoleName));
    cy.then(() => openPosWithRole(saRoleName));
    assertButtonVisible("Save/New", true);
    assertButtonVisible("Held", false);
    assertButtonVisible("Return", false);
    assertButtonVisible("PAY", false);

    cy.then(() => setOnlyOperationalRole(userDocname, cashierRoleName));
    cy.then(() => openPosWithRole(cashierRoleName));
    assertButtonVisible("Held", true);
    assertButtonVisible("Return", true);
    assertButtonVisible("PAY", true);

    cy.then(() => setSimplifiedToggle(0));
    cy.then(() => setOnlyOperationalRole(userDocname, saRoleName));
    cy.then(() => openPosWithRole(saRoleName));
    assertButtonVisible("Save/New", true);
    assertButtonVisible("Held", true);
    assertButtonVisible("Return", true);
    cy.contains(".v-btn", /^PAY$/i, { timeout: 30000 }).should("be.visible").and("be.disabled");
  });
});

