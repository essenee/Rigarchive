# Responsive Shared Header and Homepage Hero

Date: 2026-10-31. Status: implemented and verified; experimental visual review pending. No stage, commit or push.

### Responsive shared header and homepage hero (2026-10-31)

- Preserved the manually selected Adventure vehicle info archive tagline and desktop header/hero. Enhanced phone header uses branding, Vehicles/More/Garage, and full-width search rows; tablet uses two rows. Secondary destinations remain ordinary links, visible without JavaScript. The progressive disclosure supports native Enter/Space, Escape, outside/focus-exit dismissal and predictable resize focus; DOM order follows visual rows. ResizeObserver measures sticky-header height for scroll padding, with focus correction for obscured content. Unenhanced narrow headers remain non-sticky with wrapped visible navigation.
- Preserved the 36x44px Vehicles caret target and 6px label-to-caret spacing; removed the redundant following flex gap without overlapping targets. Panels are sized against the header container, avoiding scrollbar-width overflow.
- At <=1024px the photo remains dominant with a bounded, cropped decorative sketch accent, hidden at <=360px. Source images are unchanged. Decorative sketch uses empty alt text and an aria-hidden wrapper; explicit image dimensions/aspect ratios reserve layout space. Phone label typography is reduced.
- Verified managed-browser headers at 1440x1000: 87.4px; 768x1024: 123.4px; 390x844, 375x812 and 320x700: 171.4px. Initial scroll position zero and no horizontal overflow at all sizes. Checked both disclosures with Enter/Space/Escape, visible focus/restoration, 320px open-panel bounds, skip link, content focus, photo/label visibility and selector/model-list regressions. No captured console warnings/errors or observed broken loaded images. Human visual approval remains pending.
- Verification: 50 focused and 356 full Django tests passed with isolated memory SQLite and temporary media; all 25 JavaScript tests passed (eight new header tests). System check, migration-consistency dry-run, JavaScript syntax and whitespace checks passed. No development database operations, migrations, dependencies, routes, reference records, measurements or image assignments changed.

## Files and boundaries

- templates/base.html: existing links wrapped in secondary disclosure; hidden enhancement-only native button, added deferred header script and stylesheet version query. Preserves both pre-existing manual changes: default title Adventure Vehicle Archive and exact tagline Adventure vehicle info archive.
- static/js/header_navigation.js (new): progressive secondary disclosure, breakpoint DOM order/focus, header-height observation and sticky-focus correction. Existing vehicle_quick_selector.js is unchanged.
- static/css/site.css: scoped secondary/header rules and caret whitespace correction. Three rows <=600px, two rows <=1024px; existing desktop flex composition remains. No changes to generation-page card/detail layouts.
- templates/home.html: versioned homepage stylesheet; decorative sketch wrapper aria-hidden with empty image alt. Both source image references/dimensions unchanged.
- static/css/homepage.css: replaces full-width portrait fallback with bounded absolute accent (88-160px wide, 1.4 aspect ratio, cropped at center 35%) and 24px reserved lower footprint; hidden <=360px. Photo retains 1.63 landscape ratio, no distorted assets; smaller phone label.
- config/tests.py: two server-rendered fallback/destination/decorative-image regression tests.
- reference/tests/js/header_navigation.test.cjs (new): eight tests for disclosure, focus, dismissal, breakpoint ordering and missing-header fallback.
- CHANGELOG.md, CURRENT_STATE.md, this task record: verified implementation state.

## Verification

venv/py313/bin/python -B /tmp/rigarchive_ui_verify.py config.tests reference.tests.test_vehicle_quick_selector reference.tests.test_vehicle_visual_continuity reference.tests.test_experimental_hub: 50 passed. Full suite through the same wrapper: 356 passed. The temporary wrapper sets RIGARCHIVE_TEST_DB_PATH=:memory:, TEST.NAME=:memory:, temporary media/upload directories and a connection_created guard rejecting non-memory SQLite connections. Final full log: /tmp/rigarchive-responsive-final.log.

venv/py313/bin/python -B /tmp/rigarchive_ui_verify.py checks runs call_command('check') and call_command('makemigrations', check=True, dry_run=True): no issues/no changes. No migrate command or development migration ran. node --test reference/tests/js/header_navigation.test.cjs reference/tests/js/vehicle_quick_selector.test.cjs reference/tests/js/generation_configurator.test.cjs: 25 passed. node --check static/js/header_navigation.js and git diff --check passed.

## Browser results

Authorized managed browser only, no terminal HTTP. Measured final sizes (scrollbars reserve some content width):

| Viewport | Header | Photo layout size | Sketch accent |
| --- | --- | --- | --- |
| 1440x1000 | 87.4px | 761x467 | Original desktop panel |
| 768x1024 | 123.4px | 682x419 | 160x114 |
| 390x844 | 171.4px | 304x187 | 88x63 |
| 375x812 | 171.4px | 289x177 | 88x63 |
| 320x700 | 171.4px | 234x144 | Hidden |

All fresh reloads at scrollY=0, skip link outside viewport until focus, exact tagline retained, no horizontal overflow. At 390px sketch area is ~10% of photograph area; photo source remains 1536x1024, portrait sketch 1024x1535. Vehicles label-to-caret measured 6px; caret target 36x44px; adjacent control bounds meet with no overlap. Desktop link typography/alignment and active underline rules are retained.

Enter and Space opened each disclosure at 320/390/768px, focused the first destination/manufacturer with a solid outline, and Escape closed/restored trigger focus. After the scrollbar-boundary correction, both 320px panels end at x=293 inside clientWidth=305 with scrollWidth=305. Native Tab on selector cards and skip-to-main activation kept focus below the sticky header; initial skip focus did not scroll. DOM order follows tablet and phone row order. Server-rendered secondary links remain visible with no JS; buttons are hidden until enhancement. The no-JS fallback was checked through template tests/source inspection, not an actual JS-disabled browser session.

Explore Vehicles plus 4Runner/Tacoma/Touareg model generation listings checked at 390 and 1440px: existing compact selector and photographic generation grids, no overflow or broken loaded images. No generation-detail GETs were issued during this task because they write sessions. Their unchanged templates and behavior remain covered by automated tests. Search form action and Garage destination/status are unchanged; no form submitted. Garage remains an unavailable placeholder, not a newly implemented feature. No captured warning/error console entries. Screen-reader, exhaustive zoom/reflow and performance/CLS instrumentation were not performed; explicit dimensions/ratio frames provide layout reservation.

Representative screenshots saved outside repository in the chat visualization directory: responsive-home-1440.jpg, responsive-home-768.jpg, responsive-home-390.jpg, responsive-home-375.jpg, responsive-home-320.jpg, responsive-secondary-320.jpg, responsive-vehicles-320.jpg and responsive-skip-focused.jpg. Temporary viewport override reset before delivery.

## Preservation and remaining review

Baseline working tree had config/settings.py, db.sqlite3, manually edited templates/base.html, three .codex-* markers and five untracked homepage assets. Settings/database/markers/assets were not edited, reset or cleaned; manual title/tagline preserved. No direct database access, vehicle/reference/measurement operations, assets, assignments, routes, framework/dependency or deployment changes. This task does not claim bytewise database auditing. Test data lived in isolated databases.

Review the ellipsis More control and small decorative sketch crop against screenshots. Existing source imagery and overall archival design remain; approval does not complete the broader experimental design. No Git publication or staging performed.

## Sketch crop follow-up (2026-10-31)

User requested larger decorative artwork with both lower front/rear views complete. Changed only the tablet/mobile accent dimensions/crop in homepage.css and the homepage stylesheet version query. The accent is now clamp(104px, 30%, 180px), aspect ratio .95, center 60% crop; bottom -16px uses existing whitespace without moving Vehicle Platforms. At 375/390px it measures 104x109.5px; at 768px 180x189.5px. Both lower views are visually complete, with 28px clearance before Vehicle Platforms and no photo-label overlap or horizontal overflow. Desktop is unchanged and <=360px remains hidden. Source assets, header, tagline and data are unchanged. Managed browser checked 1440/768/390/375/320 sizes, no captured warnings/errors. Screenshots: responsive-sketch-{width}.jpg in the chat visualization directory. All 356 isolated Django tests passed again; system check/migration dry-run and whitespace checks passed. JavaScript was unchanged; latest JS result remains 25 passing. No stage, commit or push.

## Balanced sketch margins and More label follow-up (2026-10-31)

User approved the responsive layout and requested two narrow adjustments. Source image inspection places the drawing group approximately from y=335 to y=1204 within the 1535px-tall source. Changing object-position from center 60% to center 50% shifts the drawing group down inside the same crop frame, balancing visible top/bottom paper without cutting any vehicle details. Frame dimensions, lower-right location, source asset and <=360px suppression are unchanged.

The secondary toggle now renders More plus an aria-hidden downward caret, with transparent/no-border styling and approximately 47x44px target. Accessible name More navigation, aria-expanded/controls, native button behavior, no-JS fallback and JavaScript are unchanged. Vehicles retains its 36x44px target and 6px label/caret gap. Cache query revisions updated for both stylesheets.

Managed-browser checks at 1440x1000, 768x1024, 390x844, 375x812 and 320x700: no overflow/wrapping, initial scroll zero, complete drawings and visually comparable paper margins. Header heights remain 87.4/123.4/171.4/171.4/171.4px. Both disclosures tested using Enter and Space at applicable sizes; Escape restores correct trigger with aria-expanded=false; focus outline remains visible. Desktop More stays hidden. No captured console warnings/errors. Screenshots refinement-more-margins-390.jpg and refinement-more-margins-768.jpg (plus other widths) saved outside repository. Temporary viewport override reset.

Modified this follow-up: static/css/homepage.css, static/css/site.css, templates/base.html, templates/home.html, config/tests.py, CHANGELOG.md, CURRENT_STATE.md, this task record. The Django fallback test now requires the More/caret markup and rejects ellipsis. Full isolated Django suite: 356 passed; full JavaScript suite: 25 passed; system/migration-consistency and whitespace checks passed. No assets, JS behavior, layouts/routes outside scope, settings, database, reference records or measurements modified. Existing work preserved. No stage, commit or push. Visual approval of these details pending.

## Paper rotation follow-up (2026-10-31)

Added transform: rotate(1deg) to the tablet/mobile hero-schematic-panel outer frame only (<=1024px); no existing transform was replaced. Border/shadow rotate with the clipped image. The center 50% crop, frame dimensions, lower-right positioning, photograph/label and all header controls are unchanged. Desktop remains unrotated; <=360px remains hidden. Homepage stylesheet version query bumped for cache refresh.

Managed-browser verification at 1440/768/390/375/320 widths confirmed the 1-degree clockwise transform matrix at visible tablet/mobile sizes, intact complete drawings and balanced margins, no horizontal overflow or label overlap. Clear space above Vehicle Platforms remains ~26px tablet/~27px phone. Updated screenshots sketch-rotation-390.jpg and sketch-rotation-768.jpg saved outside the repository. Viewport override reset. All 356 isolated Django tests passed again; system/migration-consistency and whitespace checks passed. JavaScript unchanged, latest result remains 25 passing tests. Source assets, settings/database, tagline, unrelated work and Git index preserved; no stage/commit/push. Visual approval pending.

## Trim excess vertical paper (2026-11-01)

User requested genuine removal of paper above/below the drawings, not another positional adjustment. Read-only PNG decoding using Python standard-library zlib/struct measured dark vehicle drawing bounds approximately x=38..985, y=337..1202 in the original 1024x1535 image; pale paper/grid/border excluded from the dark-pixel threshold. Visual inspection confirmed the rooflines, bumpers, mirrors and wheels remain within those bounds. A source-equivalent vertical window of approximately y=299..1236 gives margins comparable to existing 38-39px side margins.

Changed only the <=1024px outer frame aspect ratio from .95 to 1.09 in homepage.css, plus homepage stylesheet cache version in home.html. Width, right/bottom positioning, 1deg outer rotation, object-position:center 50%, image scale, assets, photo/label, header/tagline and hidden <=360px behavior are unchanged. No compensation via new spacing or enlargement. Phone frame decreases from 104x109.5 to 104x95.4px; tablet decreases from 180x189.5 to 180x165.1px. Drawings remain at identical width-driven scale (102/1024 on phones), without distortion. Estimated all-four paper margins including frame border at 390px are top4.82/bottom4.42/left4.79/right4.88px; tablet approximately7.0-7.8px.

Managed browser verified 1440x1000, 768x1024, 390x844, 375x812 and 320x700: complete drawings, balanced margins, clockwise frame/border/shadow rotation, no label overlap, unwanted clipping or horizontal overflow. Desktop remains original; 320px stays suppressed. Screenshots trimmed-paper-home-390.jpg, trimmed-paper-closeup-390.jpg and trimmed-paper-home-768.jpg saved outside repository. Temporary viewport reset. All 356 isolated Django tests passed again; system check/migration-consistency dry-run/whitespace checks passed. No JavaScript changed or rerun; latest JS verification remains 25 passing. Source assets and protected/pre-existing settings/database/markers/assets preserved; no data operations, stage, commit or push.
