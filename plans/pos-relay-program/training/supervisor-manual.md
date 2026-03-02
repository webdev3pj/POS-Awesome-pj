# Supervisor Manual

## Your Mission
Handle exceptions, approve overrides when justified, and keep an audit trail clean.

## Before You Start
1. Log in with supervisor user.
2. Confirm fulfillment panel and exception controls are available.
3. Confirm relay status chip and queue health.

## What You Own
1. Exception triage:
   - picking exceptions
   - dispatch mismatch cases
2. Override decisions:
   - allow partial/exception release only when justified
3. Audit quality:
   - reasons and notes must be complete

## Supervisor Workflow
1. Open exception row.
2. Review:
   - line quantities
   - notes from picker/dispatch
   - phase timeline
3. Decide path:
   - return to picker for correction, or
   - approve exception release (if policy allows).
4. Record clear reason and supporting notes.
5. Confirm final status update.

## Decision Rules
1. No financial mismatch:
   - can proceed with operational override (if policy allows).
2. Financial mismatch:
   - route back for cashier adjustment flow before final release.

## What You Must Not Do
1. Do not bypass missing audit notes.
2. Do not approve overrides without clear operational reason.
3. Do not use supervisor role for routine cashier/picker work.

## If Something Goes Wrong
1. Override action does not finalize:
   - capture order ID/local sale ref and error text
   - escalate to IT/Codex
2. UI and actual status mismatch:
   - refresh and verify using relay transaction view/API.
3. Repeated stuck exceptions:
   - pause release approvals and initiate root-cause review.

## End of Shift
1. Review open exceptions list.
2. Ensure each unresolved case has a clear handoff note.
3. Confirm no approved exception is missing reason history.
