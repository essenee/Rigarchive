# Homepage Quiet Contours and Compact Control Faces

Date: 2026-11-01. Implementation and verification complete; user visual approval pending. No stage, commit or push.

## Restored source and restrained additions

Recovered the actual earlier 1536x1536 contour asset by running only the map portion of /tmp/ra-paper-assets.cjs, the retained original producer. The recovered PNG matches the recorded original SHA-256 exactly: 9d725fed69af69301d22d5a8b9606445573fc7130e10c22c75ff801b2b74f74e (815446 bytes). Retained at static/images/homepage/topographic-subtle-original.png. No newer terrain opacity reduction was substituted for restoration.

The active topographic-approved-neutral.png (1536x1536, 252675 bytes; SHA-256 3f280a7b6b5663707e89a2efcf09f505040db6bef01e713f62a4491ffb620968) derives its contour ink directly from that earlier PNG. Opaque ground is removed so approved CSS --bg-paper (#f7f4ee) remains independent. No new solid contour formations or increased density. Only three 96px faint dotted arcs follow intermediate levels in the earlier terrain, plus two small decorative elevation labels with inline gaps.

Both labels use a tangent fitted across the local 40px contour span, not a guessed angle or one tiny segment: 6800 near (547,663), 61.7 degrees; 7200 near (1234,617), 47.4 degrees. Parallelism is independently tested against the fitted endpoints. Labels indicate decorative map character, not verified elevations. The pattern is noticeably quieter in actual desktop/mobile screenshots; mean ink alpha decreased from 5.377 in the busy tile to 0.712 in the restored tile. New or removed pixels are restricted to small annotation areas (regression limit under2000 pixels), rather than changing the underlying terrain.

Production script defaults to rebuilding only this map; photograph-paper and diagram extraction remain explicit operations and were not invoked. No dependencies or frontend runtime changes.

## Compact controls and accessibility

Before editing, actual390px measurements confirmed search40px high and Garage44px high. Desktop approved controls remain36px and untouched.

At <=1024px, CSS-only pseudo-elements provide36px visible faces inside44px native input/anchor boxes. Search keeps its existing40px flow row, with the input extending2px into the available vertical space on either side; no overlapping targets. Garage's existing native anchor encloses the smaller face. Pseudo-elements ignore pointer events, so native interaction/focus behavior remains. No JavaScript, form submission, navigation or template structure change. Focused search has the established blue border/white surface, and existing keyboard focus/disclosures remain.

At390px, before/after header height is171.2px, search width358.0px, Garage width114.1px, and Vehicle Platforms top504.1px. All are unchanged. Visible faces measure36.0px and interactive boxes44.0px. Desktop search300x36px and Garage125.3x36px remain top-aligned. Tablet header123.2px, phone header171.2px; original arrangements preserved. The homepage-only CSS leaves unrelated pages unchanged.

## Browser verification

Only authorized managed browser at127.0.0.1:8000 used. Supported viewport/screenshot scaling calibrated against actual DOM measurements, as in the prior task. Actual sizes:1440x1000,768x1024,390x844,375x812,320x700. All initial scroll positions0, no horizontal overflow, broken eager-loaded images, or warning/error logs. Sketch remains hidden at320px and otherwise unchanged. Search focus tested without submission; More Enter/Escape and Vehicles Space/Escape preserve disclosure dismissal and focus restoration. No generation-detail navigation. Overrides reset and browser hidden afterward.

Approval artifacts in the chat visualization directory: quiet-map-controls-desktop.jpg and quiet-map-controls-390.jpg. Baseline quiet-map-before-390.jpg retained for comparison. Background is visibly lighter and less dense, header opaque, labels inline with their local contours, and existing hero/diagram/tape/cards/content remain unchanged.

## Tests and checks

- venv/py313/bin/python -B /tmp/rigarchive_ui_verify.py checks: system check no issues; makemigrations check/dry-run no changes.
- Same isolated wrapper full suite:358 passed in14.040s. Memory SQLite, temporary media/uploads and non-memory connection guard; no development database write command.
- node --test reference/tests/js/homepage_paper_assets.test.cjs reference/tests/js/header_navigation.test.cjs reference/tests/js/vehicle_quick_selector.test.cjs reference/tests/js/generation_configurator.test.cjs:31 passed,0 failed on final artwork. Tests protect exact quiet-source hash, unchanged contour pixels outside annotations, both label tangents, transparency, seam continuity and unchanged diagram pixels. One intermediate alpha test caught overly dark label overdraw; label ink was capped and final tests passed.
- git diff --check passed. No migrations, framework or dependency changes.

## Database audit (read-only)

Audit uses SQLite URI mode=ro, query_only, a read transaction, stable before/after file hashes, all table row counts and SHA-256 content digests for all11 reference/measurement tables. Session diagnostics hash only rowid/expiry metadata; session keys/data and authentication credentials are not read. Audit files reside in /tmp/rigarchive-quiet-map-db-*.json. No restoration, overwrite, migration or data-edit operation.

Initial task hash before any browser visit: 0300932cc06452b58c5a2882b67f2d1e6057c11870a34c9bff896c924efc1a13.
Before final browser pass: 73b83740856afbeb7a8446a99525a3b50bec9728f72bd730486aeef1e6b48c5d.
After final browser pass: 73b83740856afbeb7a8446a99525a3b50bec9728f72bd730486aeef1e6b48c5d.

The final browser pass preserved the file hash exactly, with unchanged session metadata. Between the initial snapshot and pre-final snapshot, file hash changed, all row counts and all11 reference/measurement content digests stayed identical, and session expiry metadata changed. This is consistent with session updates rather than an actual reference-data modification. It does not establish that every non-reference field was unchanged; credential-bearing tables were counted but not fingerprinted. No net reference/measurement change was detected at any checkpoint. Earlier task's unrelated historical hash incident is not retroactively attributed by this audit.

| Table | Initial | Final |
|---|---:|---:|
| accounts_user | 1 | 1 |
| accounts_user_groups | 0 | 0 |
| accounts_user_user_permissions | 0 | 0 |
| auth_group | 0 | 0 |
| auth_group_permissions | 0 | 0 |
| auth_permission | 72 | 72 |
| django_admin_log | 17 | 17 |
| django_content_type | 18 | 18 |
| django_migrations | 26 | 26 |
| django_session | 4 | 4 |
| measurements_applicabilityfeature | 0 | 0 |
| measurements_applicabilitystate | 0 | 0 |
| measurements_measurementdefinition | 4 | 4 |
| measurements_measurementresult | 2 | 2 |
| measurements_measurementresultcondition | 0 | 0 |
| observation_observation | 0 | 0 |
| reference_canonicalrecordcorrection | 31 | 31 |
| reference_generation | 12 | 12 |
| reference_importexecutionreceipt | 2753 | 2753 |
| reference_manufacturer | 2 | 2 |
| reference_vehicledefinition | 698 | 698 |
| reference_vehiclemodel | 3 | 3 |

## Files and preservation

Modified in this task: static/css/homepage.css; templates/home.html (stylesheet revision only); docs/design/homepage-paper-assets.cjs; static/images/homepage/topographic-approved-neutral.png; config/tests.py (1536px expectation); reference/tests/js/homepage_paper_assets.test.cjs; CHANGELOG.md; docs/implementation/CURRENT_STATE.md. Added original quiet PNG source and this record.

Seven protected file fingerprints match baseline: settings, base template/tagline, photograph, photograph paper-edge PNG, diagram PNG, header JavaScript, approved wireframe. Original images, prior task work, staged reference, markers and unrelated assets retained. No Recently Viewed code/content change, vehicle/reference/measurement writes, migrations or Git mutations. Session/database results are described above rather than asserting blanket byte preservation across the whole task. Awaiting visual approval.
