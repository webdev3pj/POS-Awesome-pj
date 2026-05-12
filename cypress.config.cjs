const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const dotenv = require("dotenv");
const { defineConfig } = require("cypress");
const {
  assertFileExists,
  extractTokenSlipEvidence,
  renderHtmlToPdf,
  saveTokenSlipHtml,
} = require("./cypress/e2e/_helpers/token_slip_artifacts");

dotenv.config({ path: path.resolve(__dirname, ".env"), quiet: true });

function firstNonEmpty(values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function normalizeAlgorithm(input) {
  const raw = String(input || "SHA1").trim().toUpperCase();
  if (raw === "SHA256") return "sha256";
  if (raw === "SHA512") return "sha512";
  return "sha1";
}

function decodeBase32(base32) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const clean = String(base32 || "")
    .toUpperCase()
    .replace(/=+$/g, "")
    .replace(/[^A-Z2-7]/g, "");

  if (!clean) {
    throw new Error("Invalid or empty TOTP secret");
  }

  let bits = "";
  for (const ch of clean) {
    const idx = alphabet.indexOf(ch);
    if (idx < 0) {
      throw new Error(`Invalid base32 character in TOTP secret: ${ch}`);
    }
    bits += idx.toString(2).padStart(5, "0");
  }

  const bytes = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) {
    bytes.push(parseInt(bits.slice(i, i + 8), 2));
  }
  return Buffer.from(bytes);
}

function parseOtpAuthUri(uri) {
  let parsed;
  try {
    parsed = new URL(uri);
  } catch (err) {
    throw new Error(`Invalid otpauth URI: ${err.message}`);
  }

  if (parsed.protocol !== "otpauth:") {
    throw new Error("Invalid otpauth URI: protocol must be otpauth://");
  }

  const type = String(parsed.hostname || "").toLowerCase();
  if (type !== "totp") {
    throw new Error(`Unsupported otpauth type: ${type || "(missing)"} (expected totp)`);
  }

  const secret = parsed.searchParams.get("secret");
  if (!secret) {
    throw new Error("Missing secret in otpauth URI");
  }

  return {
    secret,
    algorithm: normalizeAlgorithm(parsed.searchParams.get("algorithm")),
    digits: Math.max(1, parseInt(parsed.searchParams.get("digits") || "6", 10) || 6),
    period: Math.max(1, parseInt(parsed.searchParams.get("period") || "30", 10) || 30),
  };
}

function generateTotpFromUri(otpauthUri, nowMs = Date.now()) {
  const { secret, algorithm, digits, period } = parseOtpAuthUri(otpauthUri);
  const key = decodeBase32(secret);
  const counter = Math.floor(nowMs / 1000 / period);

  const counterBuf = Buffer.alloc(8);
  const high = Math.floor(counter / 0x100000000);
  const low = counter >>> 0;
  counterBuf.writeUInt32BE(high >>> 0, 0);
  counterBuf.writeUInt32BE(low, 4);

  const hmac = crypto.createHmac(algorithm, key).update(counterBuf).digest();
  const offset = hmac[hmac.length - 1] & 0x0f;
  const codeInt =
    ((hmac[offset] & 0x7f) << 24) |
    ((hmac[offset + 1] & 0xff) << 16) |
    ((hmac[offset + 2] & 0xff) << 8) |
    (hmac[offset + 3] & 0xff);
  const modulo = 10 ** digits;
  return String(codeInt % modulo).padStart(digits, "0");
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
      on("before:browser:launch", (browser = {}, launchOptions) => {
        if (browser.family === "chromium") {
          // OptiPlex LAN relay uses a local Caddy CA; Cypress-launched Chrome can reject it intermittently.
          launchOptions.args.push("--ignore-certificate-errors");
          launchOptions.args.push("--allow-insecure-localhost");
          launchOptions.args.push("--window-size=1920,1080");
        }
        return launchOptions;
      });

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
          return generateTotpFromUri(uri);
        },
        saveBrowserRuntimeEvents({ spec, testTitle, events }) {
          const safeSpec = String(spec || "unknown")
            .replace(/[\\/]/g, "__")
            .replace(/[^a-zA-Z0-9._-]/g, "_");
          const safeTitle = String(testTitle || "unknown")
            .slice(0, 160)
            .replace(/[^a-zA-Z0-9._ -]/g, "_")
            .replace(/\s+/g, "_");
          const outDir = path.resolve(__dirname, "cypress", "tmp", "browser_runtime_events");
          fs.mkdirSync(outDir, { recursive: true });
          const outPath = path.join(outDir, `${safeSpec}__${safeTitle}.json`);
          fs.writeFileSync(
            outPath,
            JSON.stringify(
              {
                spec: spec || "",
                testTitle: testTitle || "",
                capturedAt: new Date().toISOString(),
                events: Array.isArray(events) ? events : [],
              },
              null,
              2
            )
          );
          return outPath;
        },
        saveTokenSlipHtml({ html, meta, spec, testTitle }) {
          return saveTokenSlipHtml({ html, meta, spec, testTitle });
        },
        renderHtmlToPdf({ htmlPath, pdfPath }) {
          return renderHtmlToPdf({ htmlPath, pdfPath });
        },
        extractTokenSlipEvidence({ html }) {
          return extractTokenSlipEvidence(html);
        },
        assertFileExists({ filePath }) {
          return assertFileExists(filePath);
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
