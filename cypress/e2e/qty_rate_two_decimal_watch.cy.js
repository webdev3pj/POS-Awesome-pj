const { loginWithOtp, frappeCall } = require("./_helpers/pos_auth");

function setField(doctype, name, fieldname, value) {
  return frappeCall("frappe.client.set_value", {
    doctype,
    name,
    fieldname,
    value,
  });
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

function ensureProfileFlags(profileName) {
  return frappeCall("frappe.client.get", { doctype: "POS Profile", name: profileName }, { timeout: 120000 }).then(
    (resp) => {
      const doc = resp && resp.message ? resp.message : null;
      expect(doc, "POS Profile doc loaded").to.be.an("object");
      const updates = [];

      [
        ["posa_input_qty", 1],
        ["posa_allow_user_to_edit_rate", 1],
      ].forEach(([fieldname, desired]) => {
        expect(fieldname in doc, `POS Profile field ${fieldname} exists`).to.eq(true);
        if (Number(doc[fieldname] || 0) !== desired) {
          updates.push([fieldname, desired]);
        }
      });

      return updates.reduce((chain, [fieldname, desired]) => {
        return chain.then(() => setField("POS Profile", profileName, fieldname, desired));
      }, Cypress.Promise.resolve());
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

function openPosSessionForRole({ roleStorageValue, roleLabel, profileName }) {
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
    choosePosProfile(profileName);
    cy.contains(".v-dialog--active .v-btn", /submit/i, { timeout: 30000 }).click({ force: true });
  });

  cy.contains("body", "Search Items", { timeout: 90000 }).should("be.visible");
}

function clickFirstSellableItem() {
  return cy.get("body", { timeout: 60000 }).then(($body) => {
    const usableRow = [...$body.find(".selection .v-data-table tbody tr")].find((el) => {
      const text = (el.innerText || "").trim();
      if (!text) return false;
      if (/no data available/i.test(text)) return false;
      return el.querySelectorAll("td").length > 1 && Cypress.$(el).is(":visible");
    });
    if (usableRow) {
      cy.wrap(usableRow).click({ force: true });
      return;
    }

    const usableCard = [...$body.find(".selection .v-card")].find((el) => {
      const text = (el.innerText || "").trim();
      if (!text) return false;
      if (/no data available/i.test(text)) return false;
      return Cypress.$(el).is(":visible");
    });
    if (usableCard) {
      cy.wrap(usableCard).click({ force: true });
      return;
    }

    throw new Error("No visible sellable item rows/cards found for precision spec.");
  });
}

function parseNumeric(text) {
  const value = parseFloat(String(text || "").replace(/[^0-9.-]/g, ""));
  return Number.isFinite(value) ? value : 0;
}

function getVisibleFieldNumericValue(label) {
  return cy.get("body", { timeout: 60000 }).then(($body) => {
    const block = [...$body.find(".v-input")].find((el) => {
      if (!Cypress.$(el).is(":visible")) return false;
      const labelEl = el.querySelector("label");
      const labelText = String((labelEl && labelEl.textContent) || "")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
      return labelText === String(label || "").toLowerCase();
    });
    expect(block, `visible field block for ${label}`).to.exist;
    const input = block.querySelector("input");
    const raw = input && typeof input.value === "string" ? input.value : block.innerText || "";
    return parseNumeric(raw);
  });
}

function getInvoiceVm() {
  return cy.get("body", { timeout: 60000 }).then(($body) => {
    const host = [...$body.find("*")].find((el) => {
      const vm = el && el.__vue__;
      return (
        vm &&
        typeof vm.get_invoice_doc === "function" &&
        typeof vm.add_item === "function" &&
        Array.isArray(vm.items)
      );
    });
    expect(host, "Invoice Vue host").to.exist;
    return host.__vue__;
  });
}

describe("POS qty/rate precision (watch mode)", () => {
  it("rounds scoped qty and rate inputs to two decimals", () => {
    const profileName = "PJ7 CASHIER";
    const roleName = "cline-Sales Associate";

    cy.viewport(1600, 900);
    loginWithOtp();
    cy.visit("/app");

    cy.window({ timeout: 30000 }).then((win) => {
      const userDocname = String(win?.frappe?.session?.user || "").trim();
      expect(userDocname, "resolved user docname").to.not.equal("");
      return cy.wrap(userDocname).as("targetUserDocname");
    });

    cy.get("@targetUserDocname").then((userDocname) => setSingleOperationalRole(String(userDocname), roleName));
    cy.then(() => ensureProfileFlags(profileName));
    cy.then(() =>
      openPosSessionForRole({
        roleStorageValue: roleName,
        roleLabel: "Sales Associate",
        profileName,
      })
    );

    cy.get(".selection input[type='number']", { timeout: 60000 })
      .first()
      .should("be.visible")
      .clear({ force: true })
      .type("1.239", { force: true })
      .blur()
      .should(($input) => {
        expect(parseNumeric($input.val()), "item selector qty rounded").to.eq(1.24);
      });

    clickFirstSellableItem();

    getVisibleFieldNumericValue("Total Qty").then((totalQty) => {
      expect(totalQty, "cart total qty after add").to.eq(1.24);
    });

    getInvoiceVm().then((vm) => {
      expect(Array.isArray(vm.items), "invoice items array").to.eq(true);
      expect(vm.items.length, "cart has one item").to.be.greaterThan(0);
      expect(Number(vm.items[0].qty), "Vue item qty after add").to.eq(1.24);
      vm.expanded = [vm.items[0]];
      vm.$forceUpdate();
    });

    cy.get(".v-data-table__expanded__content", { timeout: 30000 }).should("be.visible");
    cy.get(".v-data-table__expanded__content").within(() => {
      cy.contains(".v-input", /^QTY$/)
        .find("input")
        .first()
        .clear({ force: true })
        .type("2.555", { force: true })
        .blur()
        .should(($input) => {
          expect(parseNumeric($input.val()), "expanded line qty rounded").to.eq(2.56);
        });

      cy.get("input#rate")
        .should("be.visible")
        .clear({ force: true })
        .type("10.999", { force: true })
        .blur()
        .should(($input) => {
          expect(parseNumeric($input.val()), "expanded line rate rounded").to.eq(11.0);
        });
    });

    getInvoiceVm().then((vm) => {
      const item = Array.isArray(vm.items) && vm.items.length ? vm.items[0] : null;
      expect(item, "invoice first item").to.be.an("object");
      expect(Number(item.qty), "Vue item qty after edit").to.eq(2.56);
      expect(Number(item.rate), "Vue item rate after edit").to.eq(11.0);
      expect(Number(item.stock_qty), "stock qty recalculated from rounded qty").to.eq(
        Number((2.56 * Number(item.conversion_factor || 1)).toFixed(2))
      );
      expect(Number(vm.Total), "Vue total uses rounded qty/rate").to.eq(28.16);
    });

    getVisibleFieldNumericValue("Total Qty").then((totalQty) => {
      expect(totalQty, "displayed total qty after line edit").to.eq(2.56);
    });
    getVisibleFieldNumericValue("Total").then((total) => {
      expect(total, "displayed total after rate edit").to.eq(28.16);
    });
  });
});
