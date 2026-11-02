# Homepage Approved Paper Asset Production

Date: 2026-11-01. Implemented experimentally; responsive verification incomplete and visual approval pending. No stage, commit or push.

## Authority and limits

Authoritative reference: docs/design/wireframes/homepage_hero_diagram_&background_approved.png (1505x1045). This is the newly manually corrected/staged file, without the requested filename's `(1)` suffix. Earlier wireframes were not substituted. The standalone original blueprint has no labels and the prior derived SVG has blank label slots; neither matches the approved dimensioned source. User explicitly selected: “Extract the exact diagram from the approved reference.” No vehicle or label regeneration. Existing labels are preserved as decorative reference artwork; their accuracy/applicable configuration was not verified, and no reference measurement records were changed.

## Inventory and construction

Retained originals: 4runner-outdoor-hero.png (1536x1024); Toyota 4Runner Technical Blueprint.png (1024x1535); prior toyota-4runner-technical-annotated.svg; paper.svg; topographic-contours.svg; all wireframes. Source photograph SHA256 7ec9f8d1351b2f64c9a5855a17cc9c28cb5e21182c588f5550b9131921c0a950 equals committed source byte-for-byte.

New assets in static/images/homepage:
- 4runner-diagram-approved-paper.png: 502x514 RGBA, 514918bytes. Reference crop origin(950,146). All258028 source RGB pixels preserved exactly; only outer-perimeter alpha changes remove surrounding map/shadow pixels. Drawing proportions, dimension positions/values, handwritten labels and source paper/grid remain. Native source width is only502px: high-DPI detail is limited compared with the original unlabeled blueprint. Some fine paper shading is inherent in the flattened source; no large directional shadow added to PNG.
- hero-photo-paper.png: 1024x1024 RGBA, 332927bytes. Deterministic almost-white paper grain and subpixel irregular perimeter; transparent exterior, no baked shadow, folds or cardboard edge. Used as a separate CSS backing behind the original photograph, not composited into its pixels. Nearly square corners and existing padding/rotation retained.
- topographic-approved-neutral.png: 1536x1536 RGBA, 815446bytes. Deterministic periodic multiscale terrain, marching-square contours, varied spacing and extremely restrained neutral grain. Not a wireframe crop; no foreground/shadows or elevation claims. Opposite-edge mean gray difference below1 intensity unit, tested below2. Terrain geometry approximates the reference's natural drafting character; it is not an exact tracing or a geographical map.

Dependency-free production source: docs/design/homepage-paper-assets.cjs. Runs only when invoked directly with Node, writes only these three derived PNG filenames, uses built-in fs/zlib/path/crypto, imports without producing files for tests. No runtime asset generation or new dependency. Original source assets remain available for rollback.

## Integration

Only templates/home.html and homepage-scoped static/css/homepage.css change presentation. Image intrinsic dimensions updated and stylesheet revision query advanced. Photo paper is a separate backing pseudo-element; thin CSS drop shadows establish direction/contact, without heavy border outlines. Diagram perimeter transparency receives its own CSS drop-shadow. Existing desktop2:1 grid is retained; no heading, photo, label, typography or navigation redesign. A briefly trialed1.8:1 rule was removed when final browser verification became unavailable; no pending desktop ratio change remains.

Homepage-only body:has selector supplies full-width neutral contour texture without affecting other vehicle pages. Shared header remains opaque and unchanged. Mobile/tablet frame uses502/514 aspect ratio and contain sizing, matching the entire approved sheet; width104..180px, lower-right overlap,1deg clockwise outer rotation and <=360px suppression retained. No added layout space delays Vehicle Platforms. No alternate crop was needed based on source inspection; final requested mobile rendering acceptance is pending.

## Verification actually completed

- venv/py313/bin/python -B /tmp/rigarchive_ui_verify.py checks: system check no issues; makemigrations check/dry-run no changes. No development migrations run.
- Same guarded wrapper full suite:358 tests passed in13.905s, isolated memory SQLite and temporary media/uploads. Non-memory connections refused by runtime guard.
- node --test reference/tests/js/homepage_paper_assets.test.cjs reference/tests/js/header_navigation.test.cjs reference/tests/js/vehicle_quick_selector.test.cjs reference/tests/js/generation_configurator.test.cjs:28 passed,0 failed. New tests verify complete source RGB preservation, perimeter transparency and neutral/seam-safe background.
- /opt/homebrew/bin/git diff --check: passed.
- Original hero verified equal to HEAD bytes; exact diagram RGB comparison passed for all258028 pixels.

Managed browser initially captured before/after1440px composition with new PNGs. After a reload, supported viewport overrides stopped changing the actual document size (762x529), including a fresh managed-browser tab/capability. No alternative browser, terminal HTTP or access workaround used. Available actual762x529 view has no horizontal overflow, all eager images loaded, empty warning/error logs, correct tagline/clean opaque header, and sketch accent rather than portrait row. Initial scroll0 observed. Viewport overrides reset.

Not complete: final1440x1000,768x1024,390x844,375x812,320x700 acceptance; final390px after screenshot; full visual seam/edge review at those sizes. Source/CSS and tests preserve the320px hiding rule but that is not claimed as newly browser verified. Earlier screenshots from prior tasks are not evidence for the new assets.

Proof artifacts outside repository: asset-production-before-desktop.jpg, asset-production-before-390.jpg, asset-production-after-desktop.jpg (initial1440px integration), asset-production-after-available-viewport.jpg and asset-production-after-available-full.jpg (actual762px view). No final390px after image was available.

## Preservation

Baseline already contained modified settings/database, previous illustration experiment files/docs/tests, markers, unrelated untracked homepage assets and a staged approved wireframe. All preserved. No database operation, vehicle/reference/measurement edit, migration, route/header change, dependency install or Git mutation. Only task implementation/test/docs/derived assets changed. User manually controls staging/commit/publication.
