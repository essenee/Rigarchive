# MY2021 trim and edition review

Created: 2026-11-08
Status: Proposed

Authority: ADR-0005 manufacturer taxonomy, ADR-0010 transmission/package
subordination, approved Wrangler two-door/Unlimited normalization preserved by
ADR-0011, ADR-0012/RA-044 structured powertrain identity. Live implementation is
authoritative; no new trim-ranking, body schema or steering-field design is proposed.

A QOP code does not alone create a trim. The proposed marketed editions have
named guide columns, recurring model-year availability, distinct content/badging
and independent Edmunds listings. Keep their Sport/Sahara family relationships in
provenance. An edition may be implemented as a manufacturer quick-order package
while qualifying as an established marketed grade under the accepted rule; this
is a review conclusion, not a claim that every optional package is a trim.

| Proposed display label | Model code | Engine codes | Rows |
| --- | --- | --- | ---: |
| 80th Anniversary Edition | JLJL72 | EC1, ERG | 2 |
| Freedom | JLJL72 | EC1, ERC, ERG | 3 |
| Islander | JLJL72 | EC1, ERC, ERG | 3 |
| Rubicon | JLJS72 | EC1, ERC, ERG | 3 |
| Sport | JLJL72 | EC1, ERC, ERG | 3 |
| Sport S | JLJL72 | EC1, ERC, ERG | 3 |
| Unlimited 80th Anniversary Edition | JLJL74 | EC1, ERG, EXJ | 3 |
| Unlimited Freedom | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited High Altitude | JLJP74 | EC1, ERG, EXJ | 3 |
| Unlimited High Altitude 4xe | JLXP74 | ECX | 1 |
| Unlimited Islander | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Rubicon | JLJS74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Rubicon 392 | JLJX74 | ESG | 1 |
| Unlimited Rubicon 4xe | JLXS74 | ECX | 1 |
| Unlimited Sahara | JLJP74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Sahara 4xe | JLXP74 | ECX | 1 |
| Unlimited Sahara Altitude | JLJP74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Sport | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Sport Altitude | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Sport RHD | JLUL74 | EC1 | 1 |
| Unlimited Sport S | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Willys | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Willys Sport | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Willys | JLJL72 | EC1, ERC, ERG | 3 |
| Willys Sport | JLJL72 | EC1, ERC, ERG | 3 |

## Bounded normalization proposals

- Sport, Sport S, Willys Sport and Willys are separate named guide columns. Preserve
  the difference between Willys and Willys Sport; do not merge by similar names.
- `80TH` / `80TH EDITION` / `80TH ANNIVERSARY` normalize provisionally to
  `80th Anniversary Edition`. Do not create an ERC version: its 23Q cell is blank.
- Freedom and Islander are distinct marketed edition columns. Preserve earlier
  observations after they disappear; guide omission does not establish cancellation.
- Four-door Sport-family `ALTITUDE` normalizes to `Unlimited Sport Altitude`;
  Sahara-family `ALTITUDE` to `Unlimited Sahara Altitude`.
- Sahara-family `HIGH ALTITUDE` normalizes to `Unlimited High Altitude`, preserving
  JLJP74 parent-family evidence. No ERC cell exists for this edition.
- JLXP74 29N is proposed `Unlimited High Altitude 4xe`; 29P is `Unlimited Sahara
  4xe`. The guide explicitly calls 29N High Altitude and includes High Altitude
  badging/content. Edmunds' separate 4xe catalogue supports the marketed edition.
  No Willys/Sport 4xe or two-door 4xe is supported in this MY2021 guide union.
- JLJX74 27X is `Unlimited Rubicon 392`. No second identity for a Launch Edition
  marketing/pricing description without an independently demonstrated grade.
- Xtreme Recon (AGB) and wheel/tire, roof, door, towing and transmission
  choices remain optional offerings under existing rules, not new VehicleDefinitions.
  There is no MY2020-style Rubicon Recon marketed QOP column in this union. Do not
  manufacture one from the presence of an Xtreme Recon option.

## Sport RHD: preserve discovery, block canonical construction pending direction

JLUL74/22A/EC1/DFT first appears in the October 14 four-door guide and remains
through August. It is explicitly a United States MY2021 manufacturer factory
entry, corroborated by Edmunds. It is not excluded as foreign-market or aftermarket.

RHD describes a steering/factory configuration rather than automatically a consumer
trim. Current Wrangler identity has no assessed steering dimension, and accepted
body normalization is not permission for arbitrary suffixes. Representing it as
ordinary Sport would erase the demonstrated factory distinction; treating `Sport
RHD` as an approved grade is also not authorized by discovery. Retain the row and
seek a bounded owner/architecture interpretation of existing identity rules before
Candidate construction for that row. The other 73 proposals are separable.

All displayed names in this report are proposed MY2021 normalizations. No human
approval or Candidate revision has been created or applied.
