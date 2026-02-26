const { spawn } = require("child_process");
const path = require("path");
const { spawnSync } = require("child_process");

const cypressCli = path.resolve(__dirname, "..", "node_modules", "cypress", "bin", "cypress");
const postSpecScanScript = path.resolve(__dirname, "cypress-postspec-scan.cjs");

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error("Usage: node scripts/run-cypress.cjs <open|run> [cypress args...]");
  process.exit(1);
}

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;
env.CYPRESS_SKIP_VERIFY = "true";

const isRunCommand = args[0] === "run";
const maxRunMs = Number(env.CYPRESS_MAX_RUN_MS || (isRunCommand ? 12 * 60 * 1000 : 0));
const enablePostSpecScan =
  isRunCommand && String(env.CYPRESS_POSTSPEC_SCAN || "1").trim() !== "0";

function getArgValue(flagName) {
  const idx = args.findIndex((arg) => arg === flagName);
  if (idx >= 0 && idx + 1 < args.length) {
    return args[idx + 1];
  }
  const prefix = `${flagName}=`;
  const combined = args.find((arg) => String(arg).startsWith(prefix));
  if (combined) {
    return combined.slice(prefix.length);
  }
  return "";
}

const child = spawn(process.execPath, [cypressCli, ...args], {
  stdio: "inherit",
  cwd: path.resolve(__dirname, ".."),
  env,
  shell: false,
});

let timedOut = false;
let timeoutHandle = null;
if (maxRunMs > 0) {
  timeoutHandle = setTimeout(() => {
    timedOut = true;
    const mins = Math.round(maxRunMs / 60000);
    console.error(`Cypress run exceeded timeout (${mins} minute(s)); force-stopping child process tree.`);
    if (process.platform === "win32") {
      try {
        spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
          stdio: "inherit",
          windowsHide: true,
          timeout: 15000,
        });
      } catch (_err) {}
    }
    try {
      child.kill("SIGTERM");
    } catch (_err) {}
  }, maxRunMs);
}

function runPostSpecScan(cypressExitCode) {
  if (!enablePostSpecScan) return { status: 0 };
  const spec = getArgValue("--spec");
  const scanArgs = [
    postSpecScanScript,
    "--cypress-exit-code",
    String(cypressExitCode ?? 1),
  ];
  if (spec) {
    scanArgs.push("--spec", spec);
  }
  const result = spawnSync(process.execPath, scanArgs, {
    cwd: path.resolve(__dirname, ".."),
    stdio: "inherit",
    env,
    windowsHide: true,
    timeout: 120000,
  });
  if (result.error) {
    console.error(`[postspec-scan] launcher error: ${result.error.message}`);
  }
  return result;
}

child.on("exit", (code, signal) => {
  if (timeoutHandle) {
    clearTimeout(timeoutHandle);
    timeoutHandle = null;
  }

  const effectiveCode = timedOut ? 124 : code ?? 1;
  const scanResult = runPostSpecScan(effectiveCode);
  if (scanResult && scanResult.status && scanResult.status !== 0) {
    console.error(`[postspec-scan] completed with non-zero status ${scanResult.status}`);
  }

  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(effectiveCode);
});

child.on("error", (err) => {
  if (timeoutHandle) {
    clearTimeout(timeoutHandle);
    timeoutHandle = null;
  }
  console.error("Failed to launch Cypress:", err.message);
  process.exit(1);
});
