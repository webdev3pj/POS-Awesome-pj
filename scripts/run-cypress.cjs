const { spawn } = require("child_process");
const path = require("path");

const cypressCli = path.resolve(__dirname, "..", "node_modules", "cypress", "bin", "cypress");

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error("Usage: node scripts/run-cypress.cjs <open|run> [cypress args...]");
  process.exit(1);
}

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;
env.CYPRESS_SKIP_VERIFY = "true";

const child = spawn(process.execPath, [cypressCli, ...args], {
  stdio: "inherit",
  cwd: path.resolve(__dirname, ".."),
  env,
  shell: false,
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 1);
});

child.on("error", (err) => {
  console.error("Failed to launch Cypress:", err.message);
  process.exit(1);
});
