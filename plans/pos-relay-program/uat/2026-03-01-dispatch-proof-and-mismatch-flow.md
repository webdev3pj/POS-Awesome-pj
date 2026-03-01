# 2026-03-01 - Dispatch proof + mismatch return-to-picker validation

## Scope
- Branch: `codex-5-final`
- Local commit under test: `df9ac9b` (working tree includes uncommitted implementation patch)
- Target behavior:
  - Detailed fulfillment view default for `cline-Picker`, `cline-Dispatch`, `cline-Supervisor`
  - Dispatch release requires proof (`proof_ack_name`, `proof_mode`, `line_snapshot`)
  - Dispatch mismatch action returns row to picker exception path
  - Relay persists proof/mismatch state and emits new dispatch event types

## Environment
- Cloud dev site: `https://devpjjamaica.v.frappe.cloud/`
- Relay: `http://127.0.0.1:8787` (`/health` observed `200` during post-spec scans)
- Cypress mode: headed Chrome watch wrapper (`scripts/cypress-gui-watch.cjs --once`)

## Specs executed
1. `cypress/e2e/dispatch_workflow_frontend_watch.cy.js`
   - Result: `FAIL`
   - Failure: selector `[data-cy='dispatch-release-button']` not found
   - Evidence:
     - `cypress/screenshots/dispatch_workflow_frontend_watch.cy.js/Dispatch workflow (watch mode) -- releases a picked-ready local sale and verifies relay dispatch status (failed).png`

2. `cypress/e2e/dispatch_mismatch_returns_to_picker_watch.cy.js`
   - Result: `FAIL`
   - Failure: selector `[data-cy='dispatch-mismatch-code']` not found
   - Evidence:
     - `cypress/screenshots/dispatch_mismatch_returns_to_picker_watch.cy.js/Dispatch mismatch returns row to picker flow (watch mode) -- flags a mismatch and verifies relay sets PICK_EXCEPTION + cashier adjustment requirement (failed).png`

## Interpretation
- Relay health is up, but cloud UI under test did not expose newly added dispatch controls.
- This indicates the cloud site assets/deploy did not yet include the dispatch-proof/mismatch UI patch at run time.
- Failures are deployment-state failures, not test harness failures.

## Implementation state in repo
- Implemented (code patch complete):
  - `relay/relay/storage.py`
  - `relay/relay/app.py`
  - `relay/relay/sync_worker.py`
  - `posawesome/public/js/posapp/components/pos/FulfillmentWorkspace.vue`
  - `posawesome/posawesome/api/posapp.py`
  - `cypress/e2e/dispatch_workflow_frontend_watch.cy.js`
  - `cypress/e2e/dispatch_mismatch_returns_to_picker_watch.cy.js`
  - `cypress/e2e/ui_shell_chrome_role_consistency.cy.js`
- Documentation updated:
  - `plans/pos-relay-program/CHANGELOG_PROGRESS.md`
  - `plans/pos-relay-program/01-role-based-workflow-spec.md`
  - `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md`
  - `plans/pos-relay-program/runbooks/cypress_order_of_testing.md`

## Open items before signoff
1. Deploy this branch patch to cloud dev.
2. Re-run:
   - `dispatch_workflow_frontend_watch.cy.js`
   - `dispatch_mismatch_returns_to_picker_watch.cy.js`
   - `ui_shell_chrome_role_consistency.cy.js`
3. Confirm relay evidence for a fresh row:
   - sale fields:
     - `dispatch_proof_payload`
     - `dispatch_exception_state`
     - `cashier_adjustment_required`
   - events:
     - `DISPATCH_RELEASED_WITH_PROOF`
     - `DISPATCH_MISMATCH_FLAGGED`
4. Capture pass artifacts in `cypress/tmp/` and replace this pre-deploy UAT note with final pass status.
