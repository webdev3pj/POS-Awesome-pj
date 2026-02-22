const path = require("path");
const dotenv = require("dotenv");
const { defineConfig } = require("cypress");
const OTPAuth = require("otpauth");

dotenv.config({ path: path.resolve(__dirname, ".env"), quiet: true });

function firstNonEmpty(values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

module.exports = defineConfig({
  e2e: {
    baseUrl: firstNonEmpty([
      process.env.CYPRESS_baseUrl,
      process.env.CYPRESS_BASE_URL,
      process.env.BASE_URL,
    ]),
    specPattern: "cypress/e2e/**/*.cy.{js,jsx,ts,tsx}",
    supportFile: "cypress/support/e2e.js",
    defaultCommandTimeout: 15000,
    pageLoadTimeout: 60000,
    setupNodeEvents(on, config) {
      on("task", {
        generateTotp({ otpauthUri }) {
          const uri = firstNonEmpty([
            otpauthUri,
            process.env.CYPRESS_totpUri,
            process.env.CYPRESS_TOTP_URI,
          ]);
          if (!uri) {
            throw new Error("Missing otpauth URI. Set CYPRESS_totpUri in .env");
          }

          const totp = OTPAuth.URI.parse(uri);
          return totp.generate();
        },
      });

      config.baseUrl =
        config.baseUrl ||
        firstNonEmpty([process.env.CYPRESS_baseUrl, process.env.CYPRESS_BASE_URL]);

      config.env = {
        ...config.env,
        username: firstNonEmpty([
          config.env.username,
          process.env.CYPRESS_username,
          process.env.CYPRESS_USERNAME,
        ]),
        password: firstNonEmpty([
          config.env.password,
          process.env.CYPRESS_password,
          process.env.CYPRESS_PASSWORD,
        ]),
        totpUri: firstNonEmpty([
          config.env.totpUri,
          process.env.CYPRESS_totpUri,
          process.env.CYPRESS_TOTP_URI,
        ]),
      };

      return config;
    },
  },
});
