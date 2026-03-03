let __browserRuntimeEvents = [];

function truncate(value, max = 600) {
  const text = String(value == null ? "" : value);
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function serializeConsoleArg(arg, seen = new WeakSet()) {
  if (arg instanceof Error) {
    return {
      name: arg.name,
      message: arg.message,
      stack: truncate(arg.stack || "", 2000),
    };
  }

  if (arg == null) return arg;
  const t = typeof arg;
  if (t === "string" || t === "number" || t === "boolean") return arg;
  if (t === "function") return `[Function ${arg.name || "anonymous"}]`;

  if (t === "object") {
    const extractKnownErrorishShape = (obj) => {
      if (!obj || typeof obj !== "object") return null;
      const out = {};
      const keys = [
        "name",
        "message",
        "stack",
        "code",
        "type",
        "filename",
        "lineno",
        "colno",
        "fileName",
        "lineNumber",
        "columnNumber",
      ];
      for (const key of keys) {
        try {
          const value = obj[key];
          if (value != null && value !== "") {
            out[key] = key === "stack" ? truncate(value, 2000) : value;
          }
        } catch (_e) {
          // ignore
        }
      }
      for (const nestedKey of ["error", "reason", "originalError", "exception"]) {
        try {
          const nested = obj[nestedKey];
          if (nested && typeof nested === "object") {
            const nestedShape = extractKnownErrorishShape(nested);
            if (nestedShape && Object.keys(nestedShape).length) {
              out[nestedKey] = nestedShape;
            } else if (nested && nested.message) {
              out[nestedKey] = { message: nested.message };
            }
          } else if (typeof nested === "string") {
            out[nestedKey] = nested;
          }
        } catch (_e) {
          // ignore
        }
      }
      return Object.keys(out).length ? out : null;
    };

    if (seen.has(arg)) return "[Circular]";
    seen.add(arg);

    // Common browser event objects
    if (typeof arg.type === "string" && (arg.target || arg.currentTarget)) {
      const nestedError = (() => {
        try {
          return arg.error ? serializeConsoleArg(arg.error, seen) : null;
        } catch (_e) {
          return null;
        }
      })();
      return {
        type: arg.type,
        message: arg.message || "",
        filename: arg.filename || "",
        lineno: typeof arg.lineno === "number" ? arg.lineno : null,
        colno: typeof arg.colno === "number" ? arg.colno : null,
        target:
          (arg.target && (arg.target.tagName || arg.target.nodeName || arg.target.src || arg.target.href)) || "",
        error: nestedError,
      };
    }

    try {
      return JSON.parse(
        JSON.stringify(arg, (key, value) => {
          if (value instanceof Error) {
            return {
              name: value.name,
              message: value.message,
              stack: truncate(value.stack || "", 2000),
            };
          }
          if (typeof value === "function") return `[Function ${value.name || "anonymous"}]`;
          if (value && typeof value === "object") {
            if (seen.has(value)) return "[Circular]";
            seen.add(value);
          }
          return value;
        })
      );
    } catch (e) {
      const errorish = extractKnownErrorishShape(arg);
      if (errorish) return errorish;
      try {
        return {
          _type: Object.prototype.toString.call(arg),
          keys: Object.keys(arg).slice(0, 20),
        };
      } catch (_e) {
        // ignore
      }
      try {
        return String(arg);
      } catch (_e) {
        return "[Unserializable object]";
      }
    }
  }

  try {
    return String(arg);
  } catch (e) {
    return "[Unserializable]";
  }
}

function formatConsoleArgs(args) {
  return truncate(
    args
      .map((a) => {
        const serialized = serializeConsoleArg(a);
        if (typeof serialized === "string") return serialized;
        try {
          return JSON.stringify(serialized);
        } catch (e) {
          return String(serialized);
        }
      })
      .join(" "),
    2000
  );
}

function pushBrowserRuntimeEvent(event) {
  try {
    __browserRuntimeEvents.push({
      ts: new Date().toISOString(),
      ...event,
    });
    if (__browserRuntimeEvents.length > 200) {
      __browserRuntimeEvents = __browserRuntimeEvents.slice(-200);
    }
  } catch (e) {
    // best-effort capture only
  }
}

Cypress.on("window:before:load", (win) => {
  try {
    const originalError = win.console && win.console.error ? win.console.error.bind(win.console) : null;
    const originalWarn = win.console && win.console.warn ? win.console.warn.bind(win.console) : null;

    if (win.console) {
      win.console.error = (...args) => {
        pushBrowserRuntimeEvent({
          kind: "console.error",
          message: formatConsoleArgs(args),
        });
        if (originalError) return originalError(...args);
        return undefined;
      };

      win.console.warn = (...args) => {
        pushBrowserRuntimeEvent({
          kind: "console.warn",
          message: formatConsoleArgs(args),
        });
        if (originalWarn) return originalWarn(...args);
        return undefined;
      };
    }

    win.addEventListener(
      "error",
      (event) => {
        const target = event && event.target;
        // Resource/script load errors (including failed module scripts).
        if (target && target !== win) {
          pushBrowserRuntimeEvent({
            kind: "resource.error",
            tag: target.tagName || "",
            src: truncate(target.src || target.href || ""),
            message: truncate(event && event.message ? event.message : ""),
          });
          return;
        }

        pushBrowserRuntimeEvent({
          kind: "window.error",
          message: truncate(event && event.message ? event.message : "window error"),
          source: truncate(event && event.filename ? event.filename : ""),
          lineno: event && typeof event.lineno === "number" ? event.lineno : null,
          colno: event && typeof event.colno === "number" ? event.colno : null,
        });
      },
      true
    );

    win.addEventListener("unhandledrejection", (event) => {
      const reason = event && event.reason;
      const message =
        typeof reason === "string"
          ? reason
          : reason && reason.message
          ? reason.message
          : (() => {
              try {
                return JSON.stringify(reason);
              } catch (e) {
                return String(reason);
              }
            })();
      pushBrowserRuntimeEvent({
        kind: "unhandledrejection",
        message: truncate(message || "unhandled rejection"),
      });
    });
  } catch (e) {
    // best-effort capture only
  }
});

beforeEach(() => {
  __browserRuntimeEvents = [];
});

afterEach(function () {
  const testTitle = this.currentTest && this.currentTest.fullTitle ? this.currentTest.fullTitle() : "unknown";
  const events = Array.isArray(__browserRuntimeEvents) ? [...__browserRuntimeEvents] : [];
  const baseUrl = String(Cypress.config("baseUrl") || "");
  const isLocalStaging = /pj\.local(?::\d+)?/i.test(baseUrl);
  const alwaysScreenshot = /^(1|true|yes)$/i.test(String(Cypress.env("alwaysScreenshot") || ""));

  // Persist artifacts even on passing tests so we can inspect local runtime issues.
  cy.task(
    "saveBrowserRuntimeEvents",
    {
      spec: Cypress.spec && (Cypress.spec.relative || Cypress.spec.name),
      testTitle,
      events,
    },
    { log: false }
  ).then(() => {
    if (!isLocalStaging) {
      return;
    }

    const severePatterns = [
      /module\s+posawesome\s+not\s+found/i,
      /cannot use import statement outside a module/i,
      /failed to fetch dynamically imported module/i,
      /loading chunk .* failed/i,
      /syntaxerror/i,
    ];

    const severe = events.filter((evt) => {
      const msg = String(evt && evt.message ? evt.message : "");
      return severePatterns.some((pattern) => pattern.test(msg));
    });

    if (severe.length) {
      throw new Error(
        `Local staging browser runtime errors detected (${severe.length}): ${severe
          .slice(0, 3)
          .map((e) => `${e.kind}: ${e.message}`)
          .join(" | ")}`
      );
    }
  });

  if (alwaysScreenshot && this.currentTest && this.currentTest.state === "passed") {
    const safeTitle = String(testTitle)
      .replace(/[\\/]/g, "__")
      .replace(/[^a-zA-Z0-9._ -]/g, "_")
      .replace(/\s+/g, "_")
      .slice(0, 160);
    cy.screenshot(`passed__${safeTitle}`, { capture: "runner" });
  }
});

Cypress.on("uncaught:exception", (err) => {
  const message = String(err && err.message ? err.message : "");

  pushBrowserRuntimeEvent({
    kind: "uncaught:exception",
    message: truncate(message || "uncaught exception"),
    stack: truncate((err && err.stack) || "", 2000),
  });

  // Some Frappe Cloud pages can emit third-party/app script parse errors that
  // do not block the login form interaction. Ignore these so the test can
  // continue and validate the real login outcome.
  if (message.includes("Cannot use import statement outside a module")) {
    return false;
  }

  return undefined;
});
