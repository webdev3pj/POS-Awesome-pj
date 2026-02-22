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

describe("Frappe Cloud login (OTP automated)", () => {
  it("logs in and reaches the desk/home screen", () => {
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
      [
        "#login_email",
        "input[name='usr']",
        "input[name='login_email']",
        "input[type='email']",
      ],
      username
    );

    typeIntoFirstAvailable(
      ["#login_password", "input[name='pwd']", "input[type='password']"],
      password,
      { log: false }
    );

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

      if (!otpSelector) {
        return;
      }

      cy.task("generateTotp", { otpauthUri: totpUri }).then((otpCode) => {
        const code = String(otpCode || "").trim();
        expect(code, "generated OTP code").to.match(/^\d{6}$/);

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

    cy.location("pathname", { timeout: 90000 }).should((pathname) => {
      expect(pathname, "post-login path").to.match(/^\/app(\/|$)/);
    });

    cy.get("body", { timeout: 60000 }).should(($body) => {
      const hasDeskMarkers =
        $body.find(".navbar").length > 0 &&
        ($body.find(".desk-sidebar").length > 0 ||
          $body.find(".layout-main-section").length > 0 ||
          $body.find(".page-head").length > 0);

      expect(hasDeskMarkers, "Frappe desk/home UI markers").to.eq(true);
    });
  });
});
