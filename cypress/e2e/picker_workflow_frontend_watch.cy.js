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

function startPosSessionForRole({ roleStorageValue, roleLabel, profileName }) {
  cy.visit("/app/posapp");
  cy.get("body", { timeout: 60000 }).should("contain.text", "POS");

  cy.get("body", { timeout: 60000 }).then(($body) => {
    if (($body.text() || "").includes("multiple operational roles")) {
      throw new Error(`Precondition failed: cline has multiple cline-* roles. Expected ${roleStorageValue}.`);
    }
  });

  cy.get("body").then(($body) => {
    const hasRoleDialog = /Role:\s*/i.test($body.text() || "");
    if (!hasRoleDialog) {
      cy.log("No start-session dialog; reapplying role in localStorage and reloading.");
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

  cy.get("body", { timeout: 90000 }).should("contain.text", "Fulfillment Detail");
  cy.get("body").should("contain.text", roleLabel.includes("Supervisor") ? "Supervisor Fulfillment" : "Picker Queue");
}

describe("Picker workflow (watch mode)", () => {
  it("updates pick status with line-wise picked qty and verifies relay persistence", () => {
    const profileName = "PJ7 CASHIER";
    const relayBase = "http://127.0.0.1:8787";
    let targetRow;
    let targetLocalSaleRef = "";
    let firstLineId = 0;
    let editedPickedQty = 0;

    cy.viewport(1600, 900);
    loginWithOtp();
    startPosSessionForRole({
      roleStorageValue: "cline-Picker",
      roleLabel: "Picker",
      profileName,
    });

    cy.request(`${relayBase}/relay/pick-queue?pos_profile_id=${encodeURIComponent(profileName)}&limit=100`)
      .then((resp) => {
        expect(resp.status).to.eq(200);
        const rows = Array.isArray(resp.body && resp.body.rows) ? resp.body.rows : [];
        targetRow = [...rows]
          .reverse()
          .find(
            (r) =>
              String((r && r.dispatch_status) || "").toUpperCase() === "PENDING" &&
              ["PAID_PENDING_PICK", "PICK_IN_PROGRESS"].includes(
                String((r && r.pick_status) || "").toUpperCase()
              )
          );
        expect(targetRow, "pending unreleased queue row").to.be.an("object");
        targetLocalSaleRef = String(targetRow.local_sale_ref || "").trim();
        expect(targetLocalSaleRef).to.not.equal("");
        cy.log(`Picker target LSR: ${targetLocalSaleRef}`);
      })
      .then(() => cy.request(`${relayBase}/api/transactions/${encodeURIComponent(targetLocalSaleRef)}`))
      .then((detailResp) => {
        expect(detailResp.status).to.eq(200);
        expect(detailResp.body.ok).to.eq(true);
        const lines = Array.isArray(detailResp.body.lines) ? detailResp.body.lines : [];
        expect(lines.length, "relay sale lines").to.be.greaterThan(0);
        const firstLine = lines[0];
        firstLineId = Number(firstLine.id || 0);
        expect(firstLineId, "first relay line id").to.be.greaterThan(0);
        const orderedQty = Number(firstLine.qty || 0);
        expect(orderedQty, "ordered qty").to.be.greaterThan(0);
        editedPickedQty = orderedQty >= 1 ? Number((orderedQty / 2).toFixed(3)) : Number((orderedQty + 0.5).toFixed(3));
        if (editedPickedQty <= 0 || editedPickedQty === orderedQty) {
          editedPickedQty = Number((orderedQty + 0.25).toFixed(3));
        }
        cy.log(`Picker will edit line ${firstLineId} picked_qty to ${editedPickedQty}`);
      })
      .then(() => {
        expect(targetLocalSaleRef, "targetLocalSaleRef resolved").to.be.a("string").and.not.be.empty;
        cy.contains(".v-list-item", targetLocalSaleRef, { timeout: 60000 }).click({ force: true });
        cy.get("body", { timeout: 60000 }).should("contain.text", targetLocalSaleRef);
        cy.get("body").should("contain.text", "Line Items");
        cy.get("body").should("contain.text", "Ord Qty");
        cy.get("body").should("contain.text", "UOM");
        cy.get("body").should("contain.text", "Conv");
        cy.get("body").should("contain.text", "Picked Qty");

        cy.get(".lines-wrap", { timeout: 60000 }).then(($wrap) => {
          const el = $wrap && $wrap[0];
          expect(el, ".lines-wrap element").to.exist;
          el.scrollLeft = el.scrollWidth || 9999;
          el.dispatchEvent(new Event("scroll", { bubbles: true }));
        });

        cy.get("body").then(($body) => {
          const vmHost = [...$body.find("*")].find((el) => {
            const vm = el && el.__vue__;
            return (
              vm &&
              typeof vm.onQtyChange === "function" &&
              typeof vm.buildLineUpdates === "function" &&
              Array.isArray(vm.lineRows)
            );
          });
          expect(vmHost, "FulfillmentWorkspace Vue host").to.exist;
          const vm = vmHost.__vue__;
          const line = Array.isArray(vm.lineRows) && vm.lineRows.length ? vm.lineRows[0] : null;
          expect(line, "first picker line row (Vue)").to.be.an("object");
          line.picked_qty_input = String(editedPickedQty);
          vm.onQtyChange(line);
        });

        cy.contains(".v-btn", "Start/Save Picking", { timeout: 30000 }).click({ force: true });
      })
      .then(() => cy.request(`${relayBase}/api/transactions/${encodeURIComponent(targetLocalSaleRef)}`))
      .then((afterPickResp) => {
        expect(afterPickResp.status).to.eq(200);
        const body = afterPickResp.body;
        expect(body.ok).to.eq(true);
        expect(String(body.sale.pick_status || "")).to.eq("PICK_IN_PROGRESS");
        const line = (body.lines || []).find((r) => Number(r.id || 0) === firstLineId);
        expect(line, `relay line ${firstLineId}`).to.be.an("object");
        expect(line.payload, "relay line payload").to.be.an("object");
        expect(line.payload.picker, "relay line payload.picker").to.be.an("object");
        expect(Number(line.payload.picker.picked_qty), "persisted picked_qty").to.eq(editedPickedQty);
        expect(Number(line.payload.picker.conversion_factor || 0), "persisted conversion_factor").to.be.greaterThan(0);
        const latestPick = [...(body.pick_events || [])].pop();
        expect(latestPick, "latest pick event").to.be.an("object");
        expect(String(latestPick.event_type || "")).to.eq("PICK_IN_PROGRESS");
        expect(Array.isArray(latestPick.payload && latestPick.payload.line_updates)).to.eq(true);
      })
      .then(() => {
        cy.writeFile("cypress/tmp/picker_dispatch_target.json", {
          local_sale_ref: targetLocalSaleRef,
          profile_name: profileName,
        });
      })
      .then(() => {
        cy.contains(".v-btn", "Mark All Picked", { timeout: 30000 }).click({ force: true });
        cy.contains(".v-btn", "Mark Picked Ready", { timeout: 30000 }).click({ force: true });
      })
      .then(() => cy.request(`${relayBase}/api/transactions/${encodeURIComponent(targetLocalSaleRef)}`))
      .then((readyResp) => {
        expect(readyResp.status).to.eq(200);
        const sale = readyResp.body && readyResp.body.sale ? readyResp.body.sale : {};
        expect(String(sale.pick_status || ""), "relay sale pick_status after ready").to.eq("PICKED_READY_FOR_RELEASE");
        cy.log(`Picker marked ready: ${targetLocalSaleRef}`);
      });
  });
});
