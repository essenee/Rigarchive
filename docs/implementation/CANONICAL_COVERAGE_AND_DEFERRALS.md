# Canonical Coverage and Deferrals Register

Created: 2026-11-10  
Status: Active operational register (not an ADR or authorization to import)

This register records **known** gaps in intended canonical coverage and deliberate deferrals across model years. It is not a list of every unresearched vehicle, and a deferred observation is not an authorized canonical configuration. Entries remain visible until resolved, superseded with an auditable reason, or explicitly withdrawn with evidence. Maintain references to retained source observations, relevant classification decisions and subsequent resolution artifacts; do not silently delete entries. Distinguish missing evidence, unresolved consumer-market scope, identity uncertainty, and approved exclusion. An Edmunds catalog entry is evidence of catalog coverage, not proof of retail eligibility.

## Status vocabulary

- **Deferred — consumer-market applicability unresolved**: known observed offering; sufficient evidence for ordinary US consumer-market scope is not established.
- **Deferred — identity unresolved**: potential configuration requires supported canonical identity/classification.
- **Resolved — included**: supported, approved and traceable to an actual canonical import/receipt.
- **Resolved — excluded**: supported explicit scope decision with rationale and approval.

A resolution must record decision maker/authority, date, exact scope, evidence and canonical identifiers/receipts if included. Reopen on new relevant evidence; do not infer fleet-only status from right-hand drive or presume retail eligibility from Edmunds.

## Known deferrals

| ID | Manufacturer / model / generation | Model year | Configuration and model/QOP | Status | Reason | Reopening requirements | Evidence / decision | Resolution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| JL-RHD-2021 | Jeep Wrangler JL, four-door Unlimited Sport RHD | 2021 | `JLUL74`; QOP as supported in retained MY2021 evidence | Deferred — consumer-market applicability unresolved | Observed in ordering materials; ordinary US consumer-market applicability has not been established. Not asserted fleet-only or permanently excluded. | Supported market/customer applicability, exact canonical identity and separately authorized adjudication/import decision. | [MY2021 discovery](handoffs/MY2021_JL/README.md); retained `CLASS-075` classification deferral in MY2021 handoff; [MY2021 current status](CURRENT_STATE.md) | Open |
| JL-RHD-2022 | Jeep Wrangler JL, four-door Unlimited Sport RHD | 2022 | `JLUL74 / 22A` in retained US guide discovery | Deferred — consumer-market applicability unresolved | Ordering-guide observation is not sufficient to establish ordinary US consumer-market applicability; not asserted fleet-only or permanently excluded. | Supported market/customer applicability, exact canonical identity and separately authorized adjudication/import decision. | [MY2022 discovery](handoffs/MY2022_JL/discovery_20261109/UNRESOLVED_AND_NEXT_STAGE.md); [MY2022 inventory](handoffs/MY2022_JL/discovery_20261109/README.md); [candidate checkpoint](handoffs/MY2022_JL/lightweight_candidates_20261109/README.md) | Open |

## Maintenance

Update this register when a known offering is intentionally deferred, when new evidence materially changes its scope, or when it is resolved. Preserve prior reasoning in handoffs/decision artifacts; record actual approval and import identifiers before changing to **Resolved — included**. Workflow W2's provisional Edmunds acceptance does not automatically close consumer-market scope deferrals.
