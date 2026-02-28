"use strict";

const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const { spawnSync } = require("child_process");

function safeSlug(value, max = 120) {
  return String(value || "unknown")
    .trim()
    .replace(/[\\/]/g, "__")
    .replace(/[^a-zA-Z0-9._ -]/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, max) || "unknown";
}

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(
    d.getMinutes()
  )}${pad(d.getSeconds())}`;
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
  return dirPath;
}

function decodeHtmlEntities(text) {
  return String(text == null ? "" : text)
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&gt;/g, ">")
    .replace(/&lt;/g, "<")
    .replace(/&amp;/g, "&")
    .replace(/&#(\d+);/g, (_m, code) => {
      const parsed = Number(code);
      return Number.isFinite(parsed) ? String.fromCharCode(parsed) : "";
    });
}

function stripTags(text) {
  return decodeHtmlEntities(String(text == null ? "" : text).replace(/<[^>]+>/g, " "))
    .replace(/\s+/g, " ")
    .trim();
}

function extractByRegex(text, regex) {
  const match = String(text || "").match(regex);
  return match && match[1] ? stripTags(match[1]) : "";
}

function escapeRegExp(text) {
  return String(text || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractLabelValue(html, label) {
  const pattern = new RegExp(
    `<div[^>]*class=["'][^"']*row[^"']*["'][^>]*>\\s*<b>${escapeRegExp(label)}:\\s*<\\/b>\\s*([\\s\\S]*?)<\\/div>`,
    "i"
  );
  return extractByRegex(html, pattern);
}

function parseQuotedJsLiteral(raw) {
  const value = String(raw || "").trim();
  if (!value) return "";
  try {
    if (value.startsWith('"')) return JSON.parse(value);
    if (value.startsWith("'")) {
      return value
        .slice(1, -1)
        .replace(/\\\\/g, "\\")
        .replace(/\\'/g, "'")
        .replace(/\\"/g, '"');
    }
  } catch (_err) {
    return "";
  }
  return "";
}

function extractTokenSlipEvidence(html) {
  const source = String(html || "");
  const salesOrder = extractByRegex(source, /<div[^>]*class=["'][^"']*muted[^"']*["'][^>]*>\s*Full SO:\s*([\s\S]*?)<\/div>/i);
  const tokenLast4 = extractByRegex(
    source,
    /<div[^>]*class=["'][^"']*token-last4[^"']*["'][^>]*>\s*([\s\S]*?)<\/div>/i
  );
  const customerName = extractLabelValue(source, "Customer");
  const salesAssociate = extractLabelValue(source, "Sales Associate");
  const date = extractLabelValue(source, "Date");
  const time = extractLabelValue(source, "Time");
  const grandTotal = extractLabelValue(source, "Grand Total");

  const barcodeRaw = extractByRegex(source, /JsBarcode\('#barcode',\s*("([^"\\]|\\.)*"|'([^'\\]|\\.)*')/i);
  const barcodeValue = parseQuotedJsLiteral(barcodeRaw);

  const qrRaw = extractByRegex(
    source,
    /text:\s*(?:""\s*\+\s*)?("([^"\\]|\\.)*"|'([^'\\]|\\.)*')/i
  );
  const qrPayloadRaw = parseQuotedJsLiteral(qrRaw);

  let qrPayloadJson = null;
  if (qrPayloadRaw) {
    try {
      qrPayloadJson = JSON.parse(qrPayloadRaw);
    } catch (_err) {
      qrPayloadJson = null;
    }
  }

  return {
    salesOrder,
    tokenLast4,
    customerName,
    salesAssociate,
    date,
    time,
    grandTotal,
    barcodeValue,
    qrPayloadRaw,
    qrPayloadJson,
  };
}

function saveTokenSlipHtml({ html, meta, spec, testTitle }) {
  const outDir = ensureDir(path.resolve(process.cwd(), "cypress", "tmp", "token_slips"));
  const stamp = nowStamp();
  const basename = `${stamp}__${safeSlug(spec || "unknown-spec", 80)}__${safeSlug(testTitle || "token-slip", 80)}`;
  const htmlPath = path.join(outDir, `${basename}.html`);
  const metaPath = path.join(outDir, `${basename}.meta.json`);
  fs.writeFileSync(htmlPath, String(html || ""), "utf8");
  fs.writeFileSync(
    metaPath,
    JSON.stringify(
      {
        savedAt: new Date().toISOString(),
        spec: spec || "",
        testTitle: testTitle || "",
        meta: meta || {},
      },
      null,
      2
    ),
    "utf8"
  );
  return { htmlPath, metaPath, basename };
}

function resolvePdfBrowserBinary() {
  const candidates = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || "";
}

function renderHtmlToPdf({ htmlPath, pdfPath }) {
  const inputPath = path.resolve(String(htmlPath || ""));
  if (!fs.existsSync(inputPath)) {
    throw new Error(`HTML file does not exist: ${inputPath}`);
  }

  const targetPdfPath = path.resolve(
    String(pdfPath || inputPath.replace(/\.html?$/i, ".pdf"))
  );
  ensureDir(path.dirname(targetPdfPath));

  const browserBinary = resolvePdfBrowserBinary();
  if (!browserBinary) {
    throw new Error("No local Chrome/Edge binary found for --print-to-pdf");
  }

  const args = [
    "--headless=new",
    "--disable-gpu",
    "--allow-file-access-from-files",
    "--run-all-compositor-stages-before-draw",
    "--virtual-time-budget=5000",
    "--print-to-pdf-no-header",
    `--print-to-pdf=${targetPdfPath}`,
    pathToFileURL(inputPath).href,
  ];

  const result = spawnSync(browserBinary, args, {
    cwd: process.cwd(),
    encoding: "utf8",
    timeout: 120000,
    windowsHide: true,
  });

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(
      `PDF render failed with status ${result.status}: ${(result.stderr || result.stdout || "").trim()}`
    );
  }
  if (!fs.existsSync(targetPdfPath)) {
    throw new Error(`PDF render reported success but file is missing: ${targetPdfPath}`);
  }

  return {
    pdfPath: targetPdfPath,
    browserBinary,
    fileSize: fs.statSync(targetPdfPath).size,
  };
}

function assertFileExists(filePath) {
  const resolved = path.resolve(String(filePath || ""));
  if (!fs.existsSync(resolved)) {
    throw new Error(`Expected file does not exist: ${resolved}`);
  }
  return {
    exists: true,
    filePath: resolved,
    fileSize: fs.statSync(resolved).size,
  };
}

module.exports = {
  assertFileExists,
  extractTokenSlipEvidence,
  renderHtmlToPdf,
  saveTokenSlipHtml,
};
