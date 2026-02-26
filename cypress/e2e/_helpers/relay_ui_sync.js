function bodyTextNormalized($body) {
  return String(($body && $body.text && $body.text()) || "").replace(/\s+/g, " ").trim();
}

function findFulfillmentWorkspaceVmHost($body) {
  return [...$body.find("*")].find((el) => {
    const vm = el && el.__vue__;
    return (
      vm &&
      typeof vm.fetchDetail === "function" &&
      typeof vm.pickUpdate === "function" &&
      Array.isArray(vm.lineRows)
    );
  });
}

function getFulfillmentWorkspaceVm() {
  return cy.get("body", { timeout: 60000 }).then(($body) => {
    const host = findFulfillmentWorkspaceVmHost($body);
    expect(host, "FulfillmentWorkspace Vue host").to.exist;
    return host.__vue__;
  });
}

function assertRelayUiAndActual(options = {}) {
  const relayBase = String(options.relayBase || "http://127.0.0.1:8787").replace(/\/$/, "");
  const expectRelayOnline = options.expectRelayOnline !== false;
  const expectCloudOnline = options.expectCloudOnline !== false;
  const skipActualRelayHealth = !!options.skipActualRelayHealth;

  if (!skipActualRelayHealth) {
    cy.request({
      method: "GET",
      url: `${relayBase}/health`,
      timeout: 60000,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status, "relay /health HTTP status").to.eq(200);
      expect(resp.body && resp.body.ok, "relay /health ok").to.eq(true);
    });
  }

  cy.get("body", { timeout: 60000 }).should(($body) => {
    const text = bodyTextNormalized($body);
    if (expectRelayOnline) {
      expect(/Relay Online\s*\(LAN\)/i.test(text), "UI relay online chip visible").to.eq(true);
      expect(/RELAY DOWN|Relay Connection Error/i.test(text), "UI relay-down/error banner absent").to.eq(false);
    } else {
      expect(/RELAY DOWN|Relay Connection Error/i.test(text), "UI relay-down/error state visible").to.eq(true);
    }

    if (expectCloudOnline) {
      expect(/Cloud Online/i.test(text), "UI cloud online chip visible").to.eq(true);
    }
  });
}

function assertFulfillmentDetailSynced(localSaleRef, options = {}) {
  const expectedRef = String(localSaleRef || "").trim();
  const expectedLineId = Number(options.expectedLineId || 0);

  expect(expectedRef, "expected local sale ref for fulfillment detail sync").to.not.equal("");

  return cy.get("body", { timeout: 90000 }).should(($body) => {
    const host = findFulfillmentWorkspaceVmHost($body);
    expect(host, "FulfillmentWorkspace Vue host").to.exist;
    const vm = host.__vue__;
    expect(String(vm.selectedRef || "").trim(), "Fulfillment selectedRef").to.eq(expectedRef);
    const detailRef = String((((vm.detail || {}).sale || {}).local_sale_ref) || "").trim();
    expect(detailRef, "Fulfillment detail.sale.local_sale_ref").to.eq(expectedRef);
    expect(Array.isArray(vm.lineRows), "Fulfillment lineRows").to.eq(true);
    expect(vm.lineRows.length, "Fulfillment lineRows length").to.be.greaterThan(0);
    if (expectedLineId > 0) {
      const ids = vm.lineRows.map((row) => Number((row && row.id) || 0));
      expect(ids, "Fulfillment line row IDs").to.include(expectedLineId);
    }
  });
}

module.exports = {
  assertRelayUiAndActual,
  assertFulfillmentDetailSynced,
  getFulfillmentWorkspaceVm,
};
