const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const projectRoot = path.resolve(__dirname, "..");
const runnerScript = path.resolve(__dirname, "run-cypress.cjs");

function parseArgs(argv) {
  const out = {
    once: false,
    watch: [],
    cypressArgs: [],
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--once") {
      out.once = true;
      continue;
    }
    if (arg === "--watch") {
      const next = argv[i + 1];
      if (!next) {
        throw new Error("--watch requires a file or directory path");
      }
      out.watch.push(next);
      i += 1;
      continue;
    }
    if (arg === "--help" || arg === "-h") {
      out.help = true;
      continue;
    }
    out.cypressArgs.push(arg);
  }

  return out;
}

function printHelp() {
  console.log(
    [
      "Usage: node scripts/cypress-gui-watch.cjs [options] [cypress run args...]",
      "",
      "Runs Cypress in headed + runner-ui mode, then stays alive and reruns on file changes.",
      "This is a terminal-driven alternative to `cypress open` when GUI clicking is not possible.",
      "",
      "Options:",
      "  --once            Run once and exit (no watching)",
      "  --watch <path>    Additional file/dir to watch (can repeat)",
      "  -h, --help        Show this help",
      "",
      "Examples:",
      "  npm run e2e:watch:gui -- --spec cypress/e2e/sa_workflow_frontend_watch.cy.js",
      "  npm run e2e:watch:gui:chrome -- --spec cypress/e2e/cashier_workflow_frontend_watch.cy.js",
      "  npm run e2e:watch:gui -- --once --spec cypress/e2e/frappe_login_otp.cy.js",
    ].join("\n"),
  );
}

function uniquePaths(paths) {
  const seen = new Set();
  const out = [];
  for (const p of paths) {
    const full = path.resolve(projectRoot, p);
    if (!fs.existsSync(full)) {
      continue;
    }
    if (seen.has(full)) {
      continue;
    }
    seen.add(full);
    out.push(full);
  }
  return out;
}

function createRecursiveWatcher(targetPath, onChange) {
  try {
    return fs.watch(targetPath, { recursive: true }, onChange);
  } catch (_err) {
    if (fs.statSync(targetPath).isDirectory()) {
      const children = [];
      for (const entry of fs.readdirSync(targetPath, { withFileTypes: true })) {
        const childPath = path.join(targetPath, entry.name);
        if (entry.isDirectory()) {
          children.push(createRecursiveWatcher(childPath, onChange));
        } else {
          try {
            children.push(fs.watch(childPath, onChange));
          } catch (_ignored) {}
        }
      }
      let dirWatcher;
      try {
        dirWatcher = fs.watch(targetPath, onChange);
      } catch (_ignored) {}
      return {
        close() {
          if (dirWatcher) dirWatcher.close();
          for (const w of children) {
            if (w && typeof w.close === "function") {
              w.close();
            }
          }
        },
      };
    }

    return fs.watch(targetPath, onChange);
  }
}

async function main() {
  const parsed = parseArgs(process.argv.slice(2));
  if (parsed.help) {
    printHelp();
    return;
  }

  const baseArgs = [
    "run",
    "--e2e",
    "--headed",
    "--runner-ui",
    ...parsed.cypressArgs,
  ];

  // Default watch set covers test sources plus Cypress config.
  const watchPaths = uniquePaths([
    "cypress/e2e",
    "cypress/support",
    "cypress/fixtures",
    "cypress.config.cjs",
    ...parsed.watch,
  ]);

  let child = null;
  let running = false;
  let rerunQueued = false;
  let stopping = false;
  let debounceTimer = null;

  function launchRun() {
    if (stopping || running) return;
    running = true;
    rerunQueued = false;

    console.log(`\n[cypress-watch] Starting run: node scripts/run-cypress.cjs ${baseArgs.join(" ")}`);
    child = spawn(process.execPath, [runnerScript, ...baseArgs], {
      cwd: projectRoot,
      stdio: "inherit",
    });

    child.on("exit", (code, signal) => {
      running = false;
      child = null;
      if (signal) {
        console.log(`[cypress-watch] Cypress exited via signal ${signal}`);
      } else {
        console.log(`[cypress-watch] Cypress exited with code ${code}`);
      }

      if (stopping || parsed.once) {
        process.exit(code ?? 1);
        return;
      }

      if (rerunQueued) {
        launchRun();
      } else {
        console.log("[cypress-watch] Waiting for file changes...");
      }
    });

    child.on("error", (err) => {
      running = false;
      child = null;
      console.error("[cypress-watch] Failed to launch Cypress:", err.message);
      if (parsed.once) {
        process.exit(1);
        return;
      }
      console.log("[cypress-watch] Waiting for file changes...");
    });
  }

  function queueRerun(changePath) {
    if (parsed.once || stopping) return;
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      rerunQueued = true;
      if (running) {
        console.log(`[cypress-watch] Change detected (${changePath || "unknown"}), rerun queued after current run.`);
        return;
      }
      launchRun();
    }, 300);
  }

  const watchers = parsed.once
    ? []
    : watchPaths.map((p) =>
        createRecursiveWatcher(p, (_eventType, filename) => {
          const pretty = filename ? path.join(path.basename(p), String(filename)) : p;
          queueRerun(pretty);
        }),
      );

  if (!parsed.once) {
    if (watchPaths.length === 0) {
      console.warn("[cypress-watch] No watch paths found; running once.");
      parsed.once = true;
    } else {
      console.log("[cypress-watch] Watching:");
      for (const p of watchPaths) {
        console.log(`  - ${path.relative(projectRoot, p) || "."}`);
      }
    }
  }

  const shutdown = (signal) => {
    if (stopping) return;
    stopping = true;
    if (debounceTimer) clearTimeout(debounceTimer);
    for (const w of watchers) {
      if (w && typeof w.close === "function") {
        try {
          w.close();
        } catch (_ignored) {}
      }
    }
    if (child) {
      console.log(`[cypress-watch] Stopping Cypress (${signal})...`);
      try {
        child.kill(signal === "SIGINT" ? "SIGINT" : "SIGTERM");
      } catch (_ignored) {}
      return;
    }
    process.exit(0);
  };

  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));

  launchRun();
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
