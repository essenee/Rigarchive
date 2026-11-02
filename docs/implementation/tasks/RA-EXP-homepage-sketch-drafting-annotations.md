# Homepage Sketch Drafting Annotations

Date: 2026-11-01. Experimental revision implemented; visual approval pending. No stage, commit or push.

## Reference and reason for revision

Primary reference: docs/design/wireframes/homepage-approved.png. Reuse its separation, conventional arrows and numerical-label placement, not its unverified numbers. User explicitly overrides its rear measurement with roofline-to-hatch-bottom height. The first implementation squeezed annotations into the existing paper crop; narrow offsets and small open arrows made the result crowded. It was not visually approved and is superseded here.

## Artwork and geometry

Original static/images/homepage/Toyota 4Runner Technical Blueprint.png (1024x1535) retained unchanged, SHA-256 d41dfed1c23b3d7b4daeb3241df789f06016121e15855b35fca61f37ea428e97. Derived static/images/homepage/toyota-4runner-technical-annotated.svg embeds those exact bytes once and uses native-size clipped viewports. Only blank outer paper/border is excluded. Side and lower views remain complete; lower views translate together to add annotation space. No vehicle redraw, regeneration, distortion or raster resampling. Source blank graph paper supplies the expanded background via an SVG pattern; subtle texture/grid joins are a visual-review limitation.

Output canvas 1200x1340, viewBox 0 60 1200 1340. Native-width artwork is preserved within a wider sheet. At the unchanged small in-page paper width the complete expanded composition scales as a unit, so the vehicle occupies a smaller fraction of the paper. No drawing is independently shrunk to squeeze in lines.

Exactly five dimension groups, in source-image pixel coordinates (not physical measurements):
- Overall side length: x38 to985, above roof; vertical extensions outside end boundaries.
- Overall side height: y337 highest roof-rack point to y728 ground plane, right of body.
- Wheelbase: wheel-center x215 to776, below side view with a clear ground gap.
- Front width: outer tire x75 to481, below both tires.
- Rear hatch height: body roofline y850 to hatch-bottom seam y1080, above bumper, right of rear view. Intentionally excludes rack and tire/ground height.

Five broken dimension lines leave empty numerical-label spaces. Charcoal strokes 2px (extensions 1.5px) and filled 16x12px arrowheads replace the tiny open arrows. Added paths use only horizontal/vertical segments; no diagonal bumper-to-roof line or descriptive captions. No numbers/units were inserted, no measurement sources queried and no verified engineering accuracy or scale claimed.

## Homepage integration

Template references the derived SVG with a revision query and correct intrinsic dimensions. Scoped tablet/mobile frame aspect ratio is 1200/1340 with contain sizing, replacing the old cropped 1.09 frame. Display width clamp(104px,30%,180px), right0/bottom-16px overlap, 1deg outer rotation, border/shadow, center50% alignment, aria-hidden/empty alt and <=360px suppression remain. Desktop composition and header/tagline/photo/label are unchanged. No JavaScript or dependencies added.

## Verification

Full-resolution artwork reviewed through the managed browser before homepage integration review. All five requested measurements, boundary placement, clear arrows/label gaps, complete artwork and absence of added diagonal lines inspected visually.

Managed-browser checks: 1440x1000, 768x1024, 390x844, 375x812 and 320x700. No horizontal overflow, broken eager images, clipping or photo-label overlap observed. Sketch 180x201px at768, 104x116px at390/375, hidden at320. Initial scroll0 throughout. Mobile/tablet outer rotation remains matrix(0.999848,0.0174524,-0.0174524,0.999848,0,0); desktop unrotated as approved. Console warnings/errors empty. No form submission or generation-detail visit. Viewport override reset. At phone size individual strokes/arrows are subtle decorative cues; full-resolution artwork is the geometry review reference, not a readable specification panel.

venv/py313/bin/python -B /tmp/rigarchive_ui_verify.py: all357 passed using memory SQLite, temporary media/uploads and guard refusing non-memory database connections. Wrapper checks: system check no issues; makemigrations check/dry-run no changes. node --test reference/tests/js/header_navigation.test.cjs reference/tests/js/vehicle_quick_selector.test.cjs reference/tests/js/generation_configurator.test.cjs: all25 passed. Focused tests protect original embedded bytes, five dimension groups/paired arrowheads, no numerical text, orthogonal paths, native-size cropped viewports and decorative integration.

Screenshots outside repository in chat visualization directory: drafting-revised-full-resolution.jpg, drafting-revised-home-desktop-viewport.jpg, drafting-revised-home-390-viewport.jpg, drafting-revised-home-768.jpg and drafting-revised-sketch-closeup-390.jpg.

## Preservation

Task files: derived SVG, templates/home.html, static/css/homepage.css, config/tests.py, CHANGELOG.md, CURRENT_STATE.md and this record. Existing config/settings.py and db.sqlite3 modifications, .codex-* markers and unrelated untracked homepage assets preserved. No direct database operations, reference/measurement edits, migrations, routes, header edits, source asset edits, dependency installs or Git mutations. Original fallback retained. Visual approval pending.
