const { assertRelayUiAndActual } = require("./_helpers/relay_ui_sync");

function findFirstSelector($root, selectors) {
  return selectors.find((selector) => $root.find(selector).length > 0);
}

function findNavbarVmHost($body) {
  return [...$body.find("*")].find((el) => {
    const vm = el && el.__vue__;
    return (
      vm &&
      typeof vm.fetch_relay_status === "function" &&
      typeof vm.check_cloud_connectivity === "function" &&
      Object.prototype.hasOwnProperty.call(vm, "relay_status")
    );
  });
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

describe("Local staging parity smoke (watch mode)", () => {
  it("captures local staging POS bootstrap/version snapshots and verifies relay UI matches actual relay health", () => {
    const relayBase = "http://127.0.0.1:8787";

    cy.viewport(1600, 900);
    cy.intercept({ method: /GET|POST/, url: "**/api/method/**" }).as("anyApiMethod");
    cy.intercept("POST", "**/api/method/frappe.desk.desk_page.getpage").as("deskGetPage");
    cy.intercept("POST", "**/api/method/frappe.desk.desktop.get_desktop_page").as("deskGetDesktopPage");
    cy.intercept("POST", "**/api/method/frappe.desk.desktop.get_workspace_sidebar_items").as(
      "deskWorkspaceSidebar"
    );
    cy.intercept("POST", "**/api/method/posawesome.posawesome.api.posapp.get_relay_connectivity_status").as(
      "getRelayConnectivityStatus"
    );
    loginWithOtp();

    cy.request({
      method: "GET",
      url: "/api/method/posawesome.posawesome.api.posapp.get_opening_dialog_data",
      failOnStatusCode: false,
      timeout: 60000,
    }).then((resp) => {
      expect([200, 417], "opening dialog API status").to.include(resp.status);

      if (resp.status === 200) {
        const msg = (resp.body && resp.body.message) || {};
        expect(msg, "opening dialog payload").to.be.an("object");
        expect(msg).to.have.property("relay_client_auth_key");
        expect(msg).to.have.property("relay_client_auth_required");
        expect(msg).to.have.property("user_role");
        expect(Array.isArray(msg.pos_profiles_data), "pos_profiles_data array").to.eq(true);
        cy.writeFile("cypress/tmp/local_staging_opening_dialog_data.json", {
          status: resp.status,
          message: msg,
        });
        return;
      }

      // Local staging can return 417 depending on current shift/role state.
      // Capture the response for parity debugging but continue to verify the
      // actual POS app shell, bundle, and relay UI behavior.
      cy.writeFile("cypress/tmp/local_staging_opening_dialog_data.json", {
        status: resp.status,
        body: resp.body,
      });
    });

    cy.visit("/app");
    cy.location("host", { timeout: 60000 }).should("match", /pj\.local(?::8080)?$/i);

    cy.window({ timeout: 60000 }).then((win) => {
      const versions =
        (win.frappe &&
          win.frappe.boot &&
          (win.frappe.boot.versions || win.frappe.boot.change_log_versions)) ||
        null;
      expect(versions, "frappe boot versions snapshot").to.exist;
      cy.writeFile("cypress/tmp/local_staging_versions.json", versions);
    });

    cy.visit("/app/posapp");
    cy.location("pathname", { timeout: 90000 }).should("match", /^\/app\/posapp(?:\/)?$/);
    cy.wait(3000);
    cy.window({ timeout: 60000 }).then((win) => {
      const route =
        win.frappe && typeof win.frappe.get_route === "function" ? win.frappe.get_route() : null;
      const routeStr = Array.isArray(route) ? route.join("/") : String(route || "");
      const modal = win.document.querySelector(".modal-dialog,.msgprint-dialog");
      const modalText = modal ? (modal.textContent || "").replace(/\s+/g, " ").trim() : "";
      const appPage = win.document.querySelector(".page-container, .layout-main-section");
      const posVmInfo = (() => {
        try {
          const candidates = [...win.document.querySelectorAll("*")];
          const host = candidates.find((el) => el && el.__vue__ && el.__vue__.$options);
          return host && host.__vue__
            ? {
                hasVue: true,
                componentName:
                  host.__vue__.$options.name ||
                  host.__vue__.$options._componentTag ||
                  host.__vue__.$options.__file ||
                  "",
              }
            : { hasVue: false };
        } catch (e) {
          return { hasVue: false, error: String(e) };
        }
      })();
      const curPage = (win.frappe && win.frappe.container && win.frappe.container.page) || null;
      const pageObj = curPage || (win.cur_page && win.cur_page.page) || null;
      let posCtorProbe = null;
      try {
        const pageModule = win.frappe && win.frappe.pages && win.frappe.pages.posapp;
        let manualInvoke = null;
        if (pageModule && typeof pageModule.on_page_load === "function") {
          try {
            const wrapper = win.document.createElement("div");
            wrapper.setAttribute("data-cy-manual-pos-wrapper", "1");
            win.document.body.appendChild(wrapper);
            pageModule.on_page_load.call({}, wrapper);
            const manualPage =
              (win.cur_page && (win.cur_page.page || win.cur_page)) ||
              (win.frappe && win.frappe.container && win.frappe.container.page) ||
              null;
            const manualInstance =
              (manualPage && manualPage.$PosApp) ||
              (wrapper && wrapper.$PosApp) ||
              null;
            manualInvoke = {
              ok: true,
              wrapperChildren: wrapper.children ? wrapper.children.length : 0,
              manualPageHasPosApp: !!(manualPage && manualPage.$PosApp),
              manualInstanceHasVue: !!(manualInstance && manualInstance.vue),
              hasVueGlobal: !!win.Vue,
              hasVuetifyGlobal: !!win.Vuetify,
              hasJQuery: !!win.$,
            };
          } catch (e) {
            manualInvoke = {
              ok: false,
              name: e && e.name ? e.name : "",
              message: e && e.message ? e.message : String(e),
              stack: e && e.stack ? String(e.stack).slice(0, 4000) : "",
              hasVueGlobal: !!win.Vue,
              hasVuetifyGlobal: !!win.Vuetify,
              hasJQuery: !!win.$,
            };
          }
        }
        posCtorProbe = {
          hasCurrentPage: !!curPage,
          currentPageTitle:
            (curPage && (curPage.title || (curPage.page && curPage.page.title))) ||
            (pageObj && pageObj.title) ||
            "",
          hasPageMain: !!(pageObj && pageObj.main),
          hasExistingPosAppInstance: !!(pageObj && pageObj.$PosApp),
          existingPosAppHasVue: !!(pageObj && pageObj.$PosApp && pageObj.$PosApp.vue),
          pageOnLoadType: typeof (pageModule && pageModule.on_page_load),
          hasVueGlobal: !!win.Vue,
          hasVuetifyGlobal: !!win.Vuetify,
          hasJQuery: !!win.$,
          manualInvoke,
        };
      } catch (e) {
        posCtorProbe = { error: String(e) };
      }

      cy.writeFile("cypress/tmp/local_staging_posapp_window_debug.json", {
        capturedAt: new Date().toISOString(),
        href: String(win.location && win.location.href),
        route: route,
        routeStr,
        bodyClass: String(win.document.body && win.document.body.className),
        hasFrappePosAppGlobal: !!(win.frappe && win.frappe.PosApp),
        hasPosAppConstructor: !!(win.frappe && win.frappe.PosApp && win.frappe.PosApp.posapp),
        hasPageScript: !!(win.frappe && win.frappe.pages && win.frappe.pages.posapp),
        hasAppPageContainer: !!appPage,
        sessionUser:
          (win.frappe && win.frappe.session && (win.frappe.session.user || win.frappe.session.user_email)) || "",
        allowedModules:
          (win.frappe && win.frappe.boot && Array.isArray(win.frappe.boot.allowed_modules))
            ? win.frappe.boot.allowed_modules
            : null,
        modalText,
        posVmInfo,
        posCtorProbe,
      });
    });
    cy.get("@deskGetPage.all").then((calls) => {
      cy.writeFile(
        "cypress/tmp/local_staging_desk_getpage_calls.json",
        (calls || []).map((c) => ({
          requestBody: c.request && c.request.body,
          statusCode: c.response && c.response.statusCode,
          responseBody: c.response && c.response.body,
        }))
      );
    });
    cy.get("@deskGetDesktopPage.all").then((calls) => {
      cy.writeFile(
        "cypress/tmp/local_staging_desk_get_desktop_page_calls.json",
        (calls || []).map((c) => ({
          requestBody: c.request && c.request.body,
          statusCode: c.response && c.response.statusCode,
          responseBody: c.response && c.response.body,
        }))
      );
    });
    cy.get("@deskWorkspaceSidebar.all").then((calls) => {
      cy.writeFile(
        "cypress/tmp/local_staging_workspace_sidebar_calls.json",
        (calls || []).map((c) => ({
          requestBody: c.request && c.request.body,
          statusCode: c.response && c.response.statusCode,
          responseBody: c.response && c.response.body,
        }))
      );
    });
    cy.get("@anyApiMethod.all").then((calls) => {
      cy.writeFile(
        "cypress/tmp/local_staging_any_api_calls.json",
        (calls || []).map((c) => ({
          method: c.request && c.request.method,
          url: c.request && c.request.url,
          statusCode: c.response && c.response.statusCode,
          requestBody: c.request && c.request.body,
          responseBody:
            c.response && c.response.statusCode && c.response.statusCode >= 400 ? c.response.body : undefined,
        }))
      );
    });
    cy.get("body", { timeout: 90000 }).should(($body) => {
      const text = ($body.text() || "").trim();
      const knownPosRoleUi =
        /Search Items/i.test(text) ||
        /SELECT S\.O/i.test(text) ||
        /Picker Queue/i.test(text) ||
        /Dispatch Queue/i.test(text) ||
        /Fulfillment Detail/i.test(text);
      expect(/POS AWESOME/i.test(text), "POS app shell visible").to.eq(true);
      expect(knownPosRoleUi, "real POS UI rendered (cashier/picker/dispatch)").to.eq(true);
      expect(/multiple operational roles/i.test(text), "no role ambiguity blocker").to.eq(false);
      expect(/POS Awesome Actions/i.test(text), "not stuck on Desk app launcher").to.eq(false);
      expect(/Module POSAwesome not found/i.test(text), "no Desk module-not-found modal").to.eq(false);
    });

    cy.wait("@getRelayConnectivityStatus", { timeout: 60000 });
    cy.wait(2000);
    cy.window({ timeout: 60000 }).then((win) => {
      const resourceNames = (win.performance && win.performance.getEntriesByType
        ? win.performance.getEntriesByType("resource").map((r) => r && r.name).filter(Boolean)
        : []
      )
        .filter((name) => /posawesome\.bundle\./i.test(String(name)))
        .slice(-20);
      cy.get("body").then(($body) => {
        const navbarHost = findNavbarVmHost($body);
        const navbarVm = navbarHost && navbarHost.__vue__ ? navbarHost.__vue__ : null;
        const navbarSnapshot = navbarVm
          ? {
              pos_profile_name:
                (navbarVm.pos_profile && navbarVm.pos_profile.name) || navbarVm.pos_profile || "",
              relay_status: { ...(navbarVm.relay_status || {}) },
              cloud_status: { ...(navbarVm.cloud_status || {}) },
              has_relay_poll_timer: !!navbarVm.relay_poll_timer,
              has_cloud_poll_timer: !!navbarVm.cloud_poll_timer,
              current_role: navbarVm.current_role || "",
            }
          : null;

        cy.writeFile("cypress/tmp/local_staging_navbar_debug.json", {
          capturedAt: new Date().toISOString(),
          resourceNames,
          bodySample: (($body.text() || "").replace(/\s+/g, " ").trim() || "").slice(0, 1200),
          navbarSnapshot,
        });
      });
    });

    assertRelayUiAndActual({ relayBase, expectRelayOnline: true, expectCloudOnline: true });

    cy.request({
      method: "GET",
      url: `${relayBase}/health`,
      failOnStatusCode: false,
      timeout: 60000,
    }).then((health) => {
      expect(health.status).to.eq(200);
      expect(health.body && health.body.ok).to.eq(true);

      cy.request({
        method: "GET",
        url: `${relayBase}/api/outbox?limit=10`,
        failOnStatusCode: false,
        timeout: 60000,
      }).then((outbox) => {
        expect(outbox.status).to.eq(200);

        cy.request({
          method: "GET",
          url: `${relayBase}/api/transactions?limit=10`,
          failOnStatusCode: false,
          timeout: 60000,
        }).then((tx) => {
          expect(tx.status).to.eq(200);
          cy.writeFile("cypress/tmp/local_staging_parity_smoke.json", {
            capturedAt: new Date().toISOString(),
            baseUrl: Cypress.config("baseUrl"),
            relayBase,
            relayHealth: health.body,
            outboxCounts: (outbox.body && outbox.body.counts) || null,
            transactionsCount:
              (tx.body && tx.body.counts && tx.body.counts.total) ||
              (Array.isArray(tx.body && tx.body.rows) ? tx.body.rows.length : null),
          });
        });
      });
    });
  });
});
