# Homepage Background, Photo Paper and Garage Refinements

Date: 2026-11-01. UI implemented and tested experimentally; user visual approval pending and database-preservation review unresolved. No Git mutation.

## Scope and reference

Authoritative image: docs/design/wireframes/homepage_hero_diagram_&background_approved.png. Repository filename omits the requested `(1)` suffix; it remains manually staged and unmodified. Four changes only: CSS paper palette, realistic transparent contour PNG, homepage desktop Garage alignment, photographic-paper edge wear. No full-page mockup generation, diagram change, route/content/typography redesign, data or architecture change.

## Palette and terrain

Prior opaque near-white PNG covered the sitewide palette. Homepage now explicitly uses var(--bg-paper), #f7f4ee, with transparent neutral-gray contour ink above it. Background color and ink are independently adjustable; header remains opaque #fdfcf9. Technical diagram paper is untouched.

New version of topographic-approved-neutral.png is3072x3072 RGBA,2689746bytes. Periodic multiscale gradient noise with independent domain warps creates ridges/valleys, sparse and dense regions, variable curvature and restrained heavier index lines. This replaces the earlier smoother value-noise/sinusoidal terrain. Large tile reduces conspicuous repetition; pixel-continuity tests compare composited seam differences against ordinary neighboring-pixel variation at the same edges. The prior fixed2-intensity threshold failed after contrast/density changed; diagnosis showed seam differences were lower than natural adjacent differences. Test now measures the actual no-discontinuity invariant rather than a contrast-dependent threshold. PNG alpha has no opaque ground, most pixels are clear, and ink remains subdued.

Two small stroke-drawn decorative map labels follow real contour tangents, with gaps cut in the contour ink:6800 near(462,669),7200 near(1256,668). Second label moved away from View all vehicles after desktop review. No verified geographic elevation claim. Geometry is a procedural approximation of the approved map character, not exact reference tracing or an actual terrain dataset. PNG contrast is reduced independently of CSS color; no page-wide whitening was used.

## Photo edge and preserved diagram

hero-photo-paper.png remains1024x1024 RGBA, now379079bytes. White-neutral backing under the unchanged photograph, with fine border-band grain, low-amplitude tonal variation, nonuniform subpixel edge fibers and transparent exterior. Nearly square corners, thin-paper appearance and existing padding remain. No photo compositing, stretching of the photograph, wrinkles, dark distress or new cardboard shading. Existing CSS directional contact shadows, rotations, tape and label remain. Source photo SHA2567ec9f8d1351b2f64c9a5855a17cc9c28cb5e21182c588f5550b9131921c0a950 preserved.

Approved technical diagram PNG SHA25606d40eb5620247919cc31c4a2685fc8cc53e534bf805fd990051c20ef5448932 preserved exactly. No regeneration, crop, recolor, retouch, label/paper edit or placement change. Native dimensions502x514; frame104x106px on phones,180x184px tablet; hidden at320px. Desktop row panel392x492px contains the original aspect-preserved image.

Production script docs/design/homepage-paper-assets.cjs uses existing built-in Node APIs; default build now writes only map/photo paper, never the diagram. Original diagram extraction routine remains available only through explicit --extract-diagram for the earlier production workflow; it was not invoked in this task. No dependencies or browser runtime asset generation.

## Garage dimensions and scope

Homepage-only @media(min-width:1025px) rules set Garage/search height/min-height36px, center Garage contents and remove its excess vertical padding. Horizontal padding, label/icon, routes, disabled-placeholder semantics and keyboard/disclosure behavior remain. No static/css/site.css or base-template edit; other pages retain their styling.

Initial available-view baseline: Garage125.3x38.5px; search203x40px at762px (tablet min-height). Exact pre-change desktop search height was not captured. Unmodified base rule suggests Garage about39px tall; do not treat that as a recorded1440px before measurement.

Verified after at1440px: search300x36px; Garage125.3x36px; both top25.2px. At768px, original search40px/Garage38.5px remain on their two-row layout. At390/375/320px, search40px/Garage44px remain on the existing three-row header. Phone Garage width114.1px. Desktop36px height exceeds24px minimum target size; phone44px target retained. Existing visible keyboard focus unchanged.

## Browser verification

Only authorized local managed browser used. Its supported viewport/screenshot controls applied about53% of requested dimensions. Calibrated control arguments against read-only actual DOM metrics, then used matching screenshot coordinates. No network workaround, alternative automation, browser permissions, host UI or OS changes. This resolves the previous task's viewport blocker. Temporary viewport override reset and browser hidden afterward.

Actual DOM sizes verified:
-1440x1000: header87.2px; no overflow/broken eager images; Garage/search aligned36px.
-768x1024: header123.2px; no overflow/broken eager images; two-row header/180px diagram accent retained.
-390x844: header171.2px; no overflow/broken eager images; diagram104x106px,1deg rotation; Vehicle Platforms top504.1px.
-375x812: header171.2px; same diagram/rotation; Vehicle Platforms top495.1px.
-320x700: header171.2px; sketch display:none; no overflow; Vehicle Platforms top430.9px.

All initial scroll positions0. Header is clean/opaque, tagline exact. Source images load, photo label remains visible, paper layering has no rectangular overlay seams, and typography/section structure unchanged. Map labels are unobtrusive, outside narrow phone crop, and clear of desktop interface text. Current map geometry/wear remain subject to user aesthetic review rather than pixel-perfect reproduction claims.

Native keyboard: More Enter opens, Escape closes with aria-expanded=false and restores More navigation focus; Vehicles Space opens and Escape restores Choose a vehicle focus. No form submissions or generation-detail visits. Warning/error logs empty. Final approval screenshots: homepage-four-refinements-desktop.jpg and homepage-four-refinements-390.jpg in the chat visualization directory. Earlier calibration captures are not final proof images.

## Tests and checks

venv/py313/bin/python -B /tmp/rigarchive_ui_verify.py checks: system check0 issues; migration-consistency check/dry-run no changes. Full guarded wrapper:358 Django tests passed in14.477s using isolated memory SQLite, temporary media/uploads and non-memory connection guard. No development migration or database operation.

node --test reference/tests/js/homepage_paper_assets.test.cjs reference/tests/js/header_navigation.test.cjs reference/tests/js/vehicle_quick_selector.test.cjs reference/tests/js/generation_configurator.test.cjs:29 passed,0 failed on final assets. New/updated asset assertions cover transparent ground, subdued achromatic ink and true seam continuity; existing exact diagram RGB preservation remains. Django PNG metadata expectation updated to3072px. git diff --check passed.

## Files and preservation

Modified within this task: static/css/homepage.css; templates/home.html (stylesheet revision only); docs/design/homepage-paper-assets.cjs; static/images/homepage/hero-photo-paper.png; static/images/homepage/topographic-approved-neutral.png; config/tests.py; reference/tests/js/homepage_paper_assets.test.cjs; CHANGELOG.md; docs/implementation/CURRENT_STATE.md. Added this task record.

All baseline staged/unstaged/untracked work retained, including previous illustration experiments, settings/database edits, source wireframe staging, markers and unrelated images. Fingerprint checks cover settings, development database, base template/tagline, hero photo, approved diagram and source wireframe. No vehicle/reference/measurement edits, migrations, routes, unrelated pages, dependency installs, Git stage/commit/push/reset/restore/clean/stash operations. User visual approval pending.

## Unresolved preservation exception

Final audit failed the db.sqlite3 fingerprint check: initial7f9c6950f18ccdd2ac88c114a7819a4178359a099afa13072b55f5846505135d; observed final0300932cc06452b58c5a2882b67f2d1e6057c11870a34c9bff896c924efc1a13. Therefore byte-for-byte development database preservation cannot be certified. No direct development database write command, generation-detail visit, form submission or data-edit instruction was issued. All tests used the guarded memory-database wrapper. Homepage get_homepage_context only reads session history; SESSION_SAVE_EVERY_REQUEST is false and no override is present. These facts do not establish the cause of the file change. No logical database inspection was performed, so affected tables/records are unknown and reference-record preservation is not independently certified. The database was left intact, without restore/reset/overwrite or attempted reconciliation. No SQLite journal/WAL/SHM sidecars were present at audit.

All five other protected fingerprints match baseline: config/settings.py; templates/base.html; hero photograph; approved diagram; approved source wireframe. Existing unrelated changes/markers/assets and staged wireframe were not edited by this task. No intentional reference or measurement write occurred. Database-change review remains separate and unresolved; do not bundle the database automatically into a UI commit. Earlier statements about preserving baseline work mean no task-directed discard/replacement, not a successful database-byte audit.
