# JLUL74 Sport RHD identity and scope

Created: 2026-11-08
Status: Proposed — owner approval pending

**Recommendation: preserve as manufacturer evidence but defer canonical
representation.** Keep research row JL21-71, EC1/DFT/22A, and all source lineage.
Do not silently exclude it, merge it into ordinary Sport, or assert fleet-only use.

## What is established

The October 14 US MY2021 four-door guide, PDF page 17, explicitly lists WRANGLER
UNLIMITED SPORT RHD as JLUL74, with EC1/DFT/22A, MSRP and selectable options. The
August 6 guide retains it on PDF page 21. Source SHA-256 values, every supporting
revision and QOP observation remain in the original inventories and the separate
`preserved_RHD_scope.json` record. US commercial offering is directly established.
It is a real manufacturer right-hand-drive factory configuration rather than a
foreign-market import or a dealer steering conversion.

A June 28, 2021 Jalopnik report describes delivery/postal fleet appeal and an
available retail RHD Unlimited offering. Edmunds independently lists Unlimited
Sport RHD. These support niche delivery/postal use but do not establish that USPS
bought it, that a postal contract was required, or that ordinary buyers were barred.
The retained US order-guide page does not state a fleet-only restriction.
Primary eligibility rules (including any sold-order/fleet-account constraints over
time) have not been located exhaustively. Do not promote forum ordering anecdotes
to manufacturer eligibility facts. The discovery's consumer-scope partition is a
construction decision, not proof of retail exclusion.

## Identity and architecture

RHD demonstrates a factory difference from ordinary Unlimited Sport. It should
not be merged by matching year/engine/4WD/market or by dropping the model-code
context. The code itself is not a canonical key or independent identity permission.

The current VehicleDefinition stores a trim string and generic drivetrain, but
no steering position, factory-variant category or consumer/fleet visibility field.
A string such as Unlimited Sport RHD can technically be stored; that alone does
not justify reinterpreting a steering configuration as an approved grade under
ADR-0005. Accepted Wrangler body normalization covers two-door/Unlimited, not a
general license to add arbitrary configuration suffixes.

`get_generation_hub_context` exposes active definitions without a consumer/fleet
predicate. `is_active=False` is lifecycle state, not an approved way to label a
valid but hidden fleet offering. Thus a separately classified factory variant
outside the consumer configurator cannot currently be represented independently
with the requested semantics. No visibility flag, schema or application change
is introduced by this review.

## Owner decision

Approve deferral of canonical representation for JL21-71 while retaining it in
US reference research evidence. Proceed separately with 73 proposed construction
rows if approved. One EC1/nonhybrid field decision remains associated with the RHD
row and is reviewed but recommended deferred alongside representation.

If the owner wishes to include it now as a named manufacturer grade instead,
request a bounded interpretation of existing grade/identity rules first. This
report does not decide that architecture question or start a new milestone.
There is no evidence-based reason here to insist it must be outside the public
consumer configurator merely because delivery fleets may use it.
