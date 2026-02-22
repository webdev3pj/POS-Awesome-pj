Cypress.on("uncaught:exception", (err) => {
  const message = String(err && err.message ? err.message : "");

  // Some Frappe Cloud pages can emit third-party/app script parse errors that
  // do not block the login form interaction. Ignore these so the test can
  // continue and validate the real login outcome.
  if (message.includes("Cannot use import statement outside a module")) {
    return false;
  }

  return undefined;
});
