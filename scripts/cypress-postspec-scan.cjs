const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");
const { spawnSync } = require("child_process");

function parseArgs(argv) {
  const out = {
    scope: process.env.CYPRESS_POSTSPEC_SCOPE || "auto",
    sinceMinutes: Number(process.env.CYPRESS_POSTSPEC_SINCE_MINUTES || 20),
    relayBase: process.env.CYPRESS_POSTSPEC_RELAY_BASE || "http://127.0.0.1:8787",
    dockerProject: process.env.CYPRESS_POSTSPEC_DOCKER_PROJECT || "pj-production",
    spec: "",
    cypressExitCode: null,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--scope") out.scope = String(argv[++i] || out.scope);
    else if (arg === "--since-minutes") out.sinceMinutes = Number(argv[++i] || out.sinceMinutes);
    else if (arg === "--relay-base") out.relayBase = String(argv[++i] || out.relayBase);
    else if (arg === "--docker-project") out.dockerProject = String(argv[++i] || out.dockerProject);
    else if (arg === "--spec") out.spec = String(argv[++i] || "");
    else if (arg === "--cypress-exit-code") out.cypressExitCode = Number(argv[++i]);
  }
  if (!Number.isFinite(out.sinceMinutes) || out.sinceMinutes < 1) out.sinceMinutes = 20;
  return out;
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch (_err) {
    return null;
  }
}

function run(cmd, args, options = {}) {
  const result = spawnSync(cmd, args, {
    cwd: options.cwd || process.cwd(),
    encoding: "utf8",
    timeout: options.timeoutMs || 30000,
    windowsHide: true,
    shell: false,
  });
  return {
    ok: result.status === 0,
    status: result.status,
    signal: result.signal,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
    error: result.error ? result.error.message : "",
  };
}

function httpGetJson(urlString, timeoutMs = 10000) {
  return new Promise((resolve) => {
    let parsed;
    try {
      parsed = new URL(urlString);
    } catch (err) {
      resolve({ ok: false, error: `Invalid URL: ${err.message}` });
      return;
    }
    const lib = parsed.protocol === "https:" ? https : http;
    const req = lib.request(
      {
        method: "GET",
        hostname: parsed.hostname,
        port: parsed.port || (parsed.protocol === "https:" ? 443 : 80),
        path: `${parsed.pathname || "/"}${parsed.search || ""}`,
        timeout: timeoutMs,
        rejectUnauthorized: false, // local Caddy cert can be untrusted in some runtimes
      },
      (res) => {
        let body = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          body += chunk;
        });
        res.on("end", () => {
          resolve({
            ok: true,
            status: res.statusCode || 0,
            bodyText: body,
            bodyJson: safeJsonParse(body),
          });
        });
      },
    );
    req.on("timeout", () => {
      req.destroy(new Error("Request timeout"));
    });
    req.on("error", (err) => {
      resolve({ ok: false, error: err.message });
    });
    req.end();
  });
}

function detectScope(options) {
  if (options.scope && options.scope !== "auto") return options.scope;
  const spec = String(options.spec || "");
  if (/local_staging|pj\.local/i.test(spec)) return "local";
  return "cloud";
}

function findDockerContainerNames(project) {
  const ps = run("docker", ["ps", "--format", "{{.Names}}"], { timeoutMs: 30000 });
  if (!ps.ok) return [];
  const prefix = `${project}-`;
  return ps.stdout
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean)
    .filter((name) => name.startsWith(prefix));
}

function containerLogScan(containerName, sinceMinutes) {
  const res = run("docker", ["logs", "--since", `${sinceMinutes}m`, containerName], { timeoutMs: 45000 });
  const text = `${res.stdout}\n${res.stderr}`;
  const lines = text.split(/\r?\n/).filter(Boolean);
  const pattern = /(Traceback|QueryDeadlockError|OperationalError\(1020|ValidationError|HTTPException|AssertionError|PermissionError|Deadlock|deadlock)/i;
  const matches = [];
  for (const line of lines) {
    if (pattern.test(line)) matches.push(line);
    if (matches.length >= 12) break;
  }
  return {
    containerName,
    ok: res.ok || res.status === 1, // docker logs may return 1 for no logs in some cases
    status: res.status,
    matches,
  };
}

function localBenchErrorScan(project, sinceMinutes) {
  const backend = `${project}-backend-1`;
  const cmd =
    "sh -lc " +
    [
      "'",
      "find /home/frappe/frappe-bench/sites/pj.local/error-snapshots -type f -mmin -" +
        Number(sinceMinutes) +
        " -name '*.json' 2>/dev/null | head -20 | while read f; do echo \\\"### $f\\\"; grep -HinEi 'QueryDeadlockError|OperationalError\\(1020|Traceback|ValidationError|PermissionError' \\\"$f\\\" || true; done;",
      "grep -HinEi 'QueryDeadlockError|OperationalError\\(1020|Traceback|ValidationError|PermissionError' /home/frappe/frappe-bench/logs/*.log 2>/dev/null | tail -40 || true",
      "'",
    ].join(" ");
  const res = run("docker", ["exec", backend, ...cmd.split(" ")], { timeoutMs: 45000 });
  return {
    backend,
    ok: res.ok || res.status === 1,
    status: res.status,
    output: `${res.stdout}\n${res.stderr}`.trim(),
  };
}

function extractSpecName(argsSpec) {
  if (!argsSpec) return "";
  return String(argsSpec).split(",").map((s) => s.trim()).filter(Boolean).join(",");
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const scope = detectScope(options);
  const summary = {
    at: new Date().toISOString(),
    scope,
    spec: extractSpecName(options.spec),
    cypressExitCode: options.cypressExitCode,
    relay: {},
    outbox: {},
    transactions: {},
    containers: [],
    errors: [],
    warnings: [],
  };

  const relayBase = String(options.relayBase).replace(/\/$/, "");
  const [relayHealth, relayOutbox, relayTx] = await Promise.all([
    httpGetJson(`${relayBase}/health`, 15000),
    httpGetJson(`${relayBase}/api/outbox`, 15000),
    httpGetJson(`${relayBase}/api/transactions?limit=5`, 15000),
  ]);

  summary.relay.health = relayHealth;
  summary.outbox.snapshot =
    relayOutbox.ok && relayOutbox.status === 200 && relayOutbox.bodyJson ? relayOutbox.bodyJson : null;
  summary.transactions.snapshot =
    relayTx.ok && relayTx.status === 200 && relayTx.bodyJson ? relayTx.bodyJson : null;

  if (!relayHealth.ok || relayHealth.status !== 200 || !(relayHealth.bodyJson && relayHealth.bodyJson.ok)) {
    summary.errors.push("Relay health check failed after Cypress spec");
  }

  const containers = findDockerContainerNames(options.dockerProject);
  const scanTargets = containers.filter((name) =>
    /-(backend|queue-short|queue-long|scheduler)-1$/.test(name),
  );
  for (const name of scanTargets) {
    const scan = containerLogScan(name, options.sinceMinutes);
    summary.containers.push(scan);
    if (scan.matches.length > 0) {
      summary.warnings.push(`${name} logs contain ${scan.matches.length} matched error lines (review needed)`);
    }
  }

  if (scope === "local") {
    // Snapshot local Frappe error-snapshots/logs for quick deadlock/500 visibility.
    const backendErrorScan = run("docker", [
      "exec",
      `${options.dockerProject}-backend-1`,
      "sh",
      "-lc",
      `find /home/frappe/frappe-bench/sites/pj.local/error-snapshots -type f -mmin -${options.sinceMinutes} -name '*.json' 2>/dev/null | head -10 | while read f; do echo "### $f"; grep -HinEi 'QueryDeadlockError|OperationalError\\(1020|Traceback|ValidationError|PermissionError' "$f" || true; done; grep -HinEi 'QueryDeadlockError|OperationalError\\(1020|Traceback|ValidationError|PermissionError' /home/frappe/frappe-bench/logs/*.log 2>/dev/null | tail -40 || true`,
    ], { timeoutMs: 60000 });

    const text = `${backendErrorScan.stdout}\n${backendErrorScan.stderr}`.trim();
    if (text) {
      summary.localBenchLogFindings = text;
      summary.warnings.push("Local Frappe bench logs/error-snapshots contain matched error entries");
    } else {
      summary.localBenchLogFindings = "";
    }
  }

  const outDir = path.resolve(process.cwd(), "cypress", "tmp");
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, "postspec_scan_latest.json"), JSON.stringify(summary, null, 2));

  console.log("[postspec-scan] Summary");
  console.log(`  scope: ${summary.scope}`);
  console.log(`  spec: ${summary.spec || "(unknown)"}`);
  console.log(`  relay /health: ${relayHealth.ok ? relayHealth.status : relayHealth.error}`);
  if (summary.outbox.snapshot && typeof summary.outbox.snapshot === "object") {
    const body = summary.outbox.snapshot;
    const counters = body.counters || body.outbox || body;
    if (counters && typeof counters === "object") {
      console.log(
        `  outbox: done=${counters.done ?? "?"} queued=${counters.queued ?? "?"} failed=${counters.failed ?? "?"} total=${counters.total ?? "?"}`,
      );
    }
  }
  if (summary.warnings.length) {
    console.log("  warnings:");
    for (const w of summary.warnings) console.log(`    - ${w}`);
  } else {
    console.log("  warnings: none");
  }
  if (summary.errors.length) {
    console.log("  errors:");
    for (const e of summary.errors) console.log(`    - ${e}`);
  } else {
    console.log("  errors: none");
  }
  console.log(`  saved: ${path.relative(process.cwd(), path.join(outDir, "postspec_scan_latest.json"))}`);

  // Non-zero only for hard infrastructure issues (e.g., relay health failure).
  process.exit(summary.errors.length ? 2 : 0);
}

main().catch((err) => {
  console.error("[postspec-scan] Failed:", err && err.stack ? err.stack : String(err));
  process.exit(1);
});
