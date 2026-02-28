# 2026-02-28 Cloud Dev Token Print PDF + Cashier Retrieval

## Scope
- Environment under test:
  - Frappe Cloud dev site: `https://devpjjamaica.v.frappe.cloud/`
  - OptiPlex local relay service: `http://127.0.0.1:8787`
  - OptiPlex LAN relay URL: `https://192.168.50.168`
- Branch: `codex-5-final`
- Test commit under validation:
  - runtime/UI baseline included latest deployed branch state prior to this run
  - token print/retrieval harness implemented in working tree on the same branch

## Test Intent
1. Capture the real Sales Associate token print popup content.
2. Save the token slip as an HTML artifact and render it to PDF.
3. Validate printed business fields:
   - Sales Order / token id
   - token last4
   - customer name
   - sales associate
   - date
   - time
   - grand total
4. Extract barcode and QR payloads from the printed slip.
5. Prove the current cashier retrieval path on cloud dev.
6. Record whether raw QR lookup is actually supported today.

## Cypress Execution
- Mode: headed watch mode (Chrome)
- Strict timeout env:
  - `CYPRESS_MAX_RUN_MS=900000`
  - `CYPRESS_POSTSPEC_SCAN=1`
- Spec:
  - `cypress/e2e/token_print_pdf_and_cashier_retrieve_watch.cy.js`

Result:
- Passed

## Fresh Evidence IDs
- Sales Order / token: `SAL-ORD-PJ7-2026-00032`
- Token last4: `0032`
- Cashier-loaded invoice: `ACC-SINV-2026-00314`

## Artifact Paths
- HTML:
  - `cypress/tmp/token_slips/20260228-024509__cypress__e2e__token_print_pdf_and_cashier_retrieve_watch.cy.js__token_print_pdf_and_cashier_retrieve.html`
- PDF:
  - `cypress/tmp/token_slips/20260228-024509__cypress__e2e__token_print_pdf_and_cashier_retrieve_watch.cy.js__token_print_pdf_and_cashier_retrieve.pdf`
- Extracted evidence JSON:
  - `cypress/tmp/token_slips/20260228-024509__cypress__e2e__token_print_pdf_and_cashier_retrieve_watch.cy.js__token_print_pdf_and_cashier_retrieve.evidence.json`
- Retrieval summary:
  - `cypress/tmp/latest_token_print_retrieval_summary.json`
- Relay token evidence:
  - `cypress/tmp/latest_token_print_relay_evidence.json`
- Invoice-from-order response:
  - `cypress/tmp/latest_token_print_invoice_from_order_response.json`

## What Was Proven
### 1. SA print path is real, not a fake placeholder
- The spec captured the actual popup HTML emitted by the `Print Token Slip` flow.
- The popup invoked `window.print()` successfully inside the captured print context.
- A real PDF artifact was rendered from that HTML using local headless Chrome on the OptiPlex.

### 2. Printed slip contains required business fields
Verified in extracted evidence:
- Sales Order / token id present
- token last4 present
- customer name present
- sales associate present
- date present
- time present
- grand total present

### 3. Printed machine-readable payloads were extracted successfully
- Barcode payload extracted successfully
- QR payload extracted successfully
- QR payload parsed as valid JSON with expected fields:
  - `type = POS-SO-TOKEN`
  - `sales_order = SAL-ORD-PJ7-2026-00032`
  - `token_id = SAL-ORD-PJ7-2026-00032`
  - `token_last4 = 0032`

### 4. Current cashier retrieval behavior on cloud dev
Observed outcome:
- `qrLookupSupported = false`
- `barcodeLookupWorked = true`
- `fallbackSoLookupWorked = false`
- `loadedIntoInvoice = true`

Interpretation:
- Raw QR payload is not cashier-ingestable in the current product.
- Barcode/Sales Order lookup is the supported scanner-like retrieval path today.
- Cashier successfully loaded the Sales Order into an invoice using the printed barcode/SO payload path.

### 5. Relay proof for the same token
Relay evidence confirmed:
- token detail exists on relay
- relay token search finds the same token/Sales Order
- `source_origin = https://devpjjamaica.v.frappe.cloud`
- `source_env = cloud_dev`

## Findings
1. Raw QR retrieval should not be treated as a regression today.
   - Current cashier search filters by `Sales Order.name`.
   - Printed QR contains JSON payload, not a plain order id.
   - Therefore raw QR lookup is not currently supported without product work.

2. Barcode/Sales Order retrieval is the actual supported path today.
   - This path worked on cloud dev in the cashier UI.
   - The order loaded into invoice successfully and produced:
     - `ACC-SINV-2026-00314`

3. The initial implementation needed two test-hardening fixes:
   - full cashier re-login/bootstrap after server-side role mutation
   - waiting for a usable order row instead of treating the immediate `No data available` table row as final

These were test harness issues, not product regressions.

## Production Signoff Meaning
This run proves:
- browser/PDF token slip generation is working
- the slip content is correct
- barcode/Sales Order retrieval works for cashier on cloud dev

This run does not prove:
- physical printer quality on actual receipt hardware
- physical handheld scanner optics/decoding behavior
- raw QR cashier intake support

## Remaining Related Work
1. Real printer/scanner hardware UAT on the target cashier station
2. Optional scanner-first enhancement if QR payload ingestion is desired:
   - cashier parser/search path that accepts the printed JSON QR payload directly
