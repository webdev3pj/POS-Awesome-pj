const {
  assertRelayUiAndActual,
  assertFulfillmentDetailSynced,
} = require("./_helpers/relay_ui_sync");

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
  expect(username).to.be.a("string").and.not.be.empty;
  expect(password).to.be.a("string").and.not.be.empty;
  expect(totpUri).to.be.a("string").and.not.be.empty;

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
  cy.get("body").then(($body) => {
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
  cy.get("body").should("contain.text", "Dispatch Queue");
}

describe("Dispatch workflow (watch mode)", () => {
  it("releases a picked-ready local sale and verifies relay dispatch status", () => {
    const relayBase = "http://127.0.0.1:8787";
    const profileName = "PJ7 CASHIER";
    let targetLocalSaleRef = "";

    loginWithOtp();
    startPosSessionForRole({
      roleStorageValue: "cline-Dispatch",
      roleLabel: "Dispatch",
      profileName,
    });

    assertRelayUiAndActual({ relayBase, expectRelayOnline: true, expectCloudOnline: true });

    cy.readFile("cypress/tmp/picker_dispatch_target.json", { timeout: 10000 }).then((data) => {
      const fromFile = String((data && data.local_sale_ref) || "").trim();
      if (fromFile) {
        targetLocalSaleRef = fromFile;
      }
    });

    cy.then(() => {
      if (!targetLocalSaleRef) return null;
      return cy.request({
        url: `${relayBase}/api/transactions/${encodeURIComponent(targetLocalSaleRef)}`,
        failOnStatusCode: false,
      });
    })
      .then((resp) => {
        if (!resp) return null;
        if (resp.status === 200 && resp.body && resp.body.sale) {
          return resp;
        }
        return null;
      })
      .then((maybeResp) => {
        if (maybeResp && maybeResp.body && maybeResp.body.sale) {
          const sale = maybeResp.body.sale;
          if (String(sale.dispatch_status || "") !== "RELEASED" && String(sale.pick_status || "") === "PICKED_READY_FOR_RELEASE") {
            return;
          }
        }
        return cy
          .request(`${relayBase}/relay/pick-queue?pos_profile_id=${encodeURIComponent(profileName)}&limit=100`)
          .then((qResp) => {
            expect(qResp.status).to.eq(200);
            const rows = Array.isArray(qResp.body && qResp.body.rows) ? qResp.body.rows : [];
            const ready = [...rows]
              .reverse()
              .find(
                (r) =>
                  String((r && r.dispatch_status) || "").toUpperCase() !== "RELEASED" &&
                  String((r && r.pick_status) || "").toUpperCase() === "PICKED_READY_FOR_RELEASE"
              );
            expect(ready, "dispatch-ready row").to.be.an("object");
            targetLocalSaleRef = String(ready.local_sale_ref || "").trim();
            cy.log(`Dispatch target LSR: ${targetLocalSaleRef}`);
          });
      });

    cy.then(() => {
      expect(targetLocalSaleRef, "dispatch targetLocalSaleRef resolved").to.be.a("string").and.not.be.empty;
      cy.get("body").should("contain.text", "Avg Wait (Ready)");
      cy.get("body").should("contain.text", "Oldest Open");
      cy.get("body").should("contain.text", "Over SLA");
      cy.contains(".v-list-item", targetLocalSaleRef, { timeout: 60000 }).click({ force: true });
      assertRelayUiAndActual({ relayBase, expectRelayOnline: true, expectCloudOnline: true });
      assertFulfillmentDetailSynced(targetLocalSaleRef);
      cy.get("body", { timeout: 60000 }).should("contain.text", targetLocalSaleRef);
      cy.get("body").should("contain.text", "Dispatch + Sync");
      cy.get("body").should("contain.text", "Phase Timeline (Dispatch Monitor)");
      cy.get("body").should("contain.text", "Current Phase");
      cy.get("body").should("contain.text", "Current Phase Age");
      cy.get("body").should("contain.text", "SLA");
      cy.get("body").should(($body) => {
        const text = ($body.text() || "").replace(/\s+/g, " ");
        expect(/Paid -> Released \(Total\)|Open Age/i.test(text), "dispatch timing summary visible").to.eq(true);
        expect(/SLA:\s*(OK|Watch|High)/i.test(text), "dispatch SLA label visible").to.eq(true);
      });
      cy.get("body").then(($body) => {
        const detailedBtn = $body.find("[data-cy='fulfillment-view-detailed']").get(0);
        if (detailedBtn) {
          cy.wrap(detailedBtn).click({ force: true });
        }
      });
      cy.get("[data-cy='dispatch-release-button']", { timeout: 30000 }).should("be.visible").and("be.disabled");
      cy.get("[data-cy='dispatch-proof-ack']", { timeout: 30000 })
        .find("input,textarea")
        .first()
        .clear({ force: true })
        .type("Dispatch QA", { force: true });
      cy.get("[data-cy='dispatch-proof-mode']", { timeout: 30000 }).click({ force: true });
      cy.contains(".v-menu__content .v-list-item", /Delivery handover/i, { timeout: 30000 }).click({
        force: true,
      });
      cy.get("[data-cy='dispatch-proof-ref']")
        .find("input,textarea")
        .first()
        .clear({ force: true })
        .type(`DLV-${Date.now()}`, { force: true });
      cy.get("[data-cy='dispatch-proof-notes']")
        .find("textarea,input")
        .first()
        .clear({ force: true })
        .type("Handover captured at dispatch desk.", { force: true });
      cy.get("[data-cy='dispatch-release-button']").should("not.be.disabled").click({ force: true });
    })
      .then(() => cy.request(`${relayBase}/api/transactions/${encodeURIComponent(targetLocalSaleRef)}`))
      .then((releasedResp) => {
        expect(releasedResp.status).to.eq(200);
        expect(releasedResp.body.ok).to.eq(true);
        const sale = releasedResp.body.sale || {};
        expect(String(sale.dispatch_status || ""), "dispatch_status after release").to.eq("RELEASED");
        expect(String(sale.pick_status || ""), "pick_status remains ready").to.eq("PICKED_READY_FOR_RELEASE");
        const proof = sale.dispatch_proof || sale.dispatch_proof_payload || {};
        expect(proof, "dispatch proof saved on relay sale").to.be.an("object");
        expect(String(proof.ack_name || "").trim(), "dispatch proof ack_name").to.not.equal("");
        expect(String(proof.proof_mode || "").trim(), "dispatch proof mode").to.eq("delivery");
        const latestDispatch = [...(releasedResp.body.dispatch_events || [])].pop();
        expect(latestDispatch, "dispatch event created").to.be.an("object");
        expect(String(latestDispatch.event_type || ""), "dispatch event type").to.eq(
          "DISPATCH_RELEASED_WITH_PROOF"
        );
        expect(latestDispatch.payload, "dispatch event payload").to.be.an("object");
        expect(Array.isArray(latestDispatch.payload.line_snapshot), "dispatch event line snapshot").to.eq(true);
        expect(latestDispatch.payload.line_snapshot.length, "dispatch line snapshot length").to.be.greaterThan(0);
        cy.writeFile("cypress/tmp/latest_dispatch_release.json", {
          local_sale_ref: targetLocalSaleRef,
          dispatch_status: String(sale.dispatch_status || ""),
          pick_status: String(sale.pick_status || ""),
          cloud_sync_status: String(sale.cloud_sync_status || ""),
          released_by: String(sale.released_by || ""),
          released_at: String(sale.released_at || ""),
          dispatch_proof: proof,
          dispatch_event_type: String(latestDispatch.event_type || ""),
        });
        cy.get("body").should("contain.text", "RELEASED");
        cy.log(`Dispatch released ${targetLocalSaleRef}`);
      });
  });
});
