# Configurator trim selector scroll and height

Created: 2026-11-09
Status: Complete
Completed: 2026-11-09

## Cause and correction

The progressive enhancement replaces `configuration-content` after every filter
response. The nested trim scroll container was recreated with scrollTop zero.
Existing focus restoration already used preventScroll and the page layout-shift
compensation preserved the outer viewport; neither retained internal list scrolling.
The former 260px cap also allowed flex buttons to shrink instead of retaining their
natural row height.

The list now has a stable `configuration-trims` ID. Just before replacement, the
script reads the current scrollTop and ordered trim-link hrefs (including year).
If the replacement has identical choices, it restores that offset. Reading at
replacement time preserves scrolling that occurs during an in-flight request.
Year/choice changes use a fresh offset. Native anchors and preventScroll focus
restoration remain in place. Initial deep links and history updates reveal an
obscured selected edge only within the list, without centering or page scrolling.
The calculation includes focus padding and rounds outward to avoid fractional-pixel
clipping; a regression test covers that edge. Existing >10-configuration automatic
first-trim selection in services.py is unchanged.

CSS uses shared gap, block-padding, border and focus-inset variables and `1lh`:
maximum = 8 × (one line + 2 × button padding + 2 × border) + 7 × gap + 2 × focus inset.
Lists retain natural height below that cap; buttons use flex:none so they cannot
compress. Wrapped narrow-screen labels scroll within the same cap and can break
long words. The existing focus-visible style remains unchanged.

## Verification

- 46 relevant Django configurator tests passed, including two new rendering/deep-link
  regressions over 4, 6, 7, 8, 12 trims and the existing 10/11 default-selection boundary.
- Full Django suite: 715 tests passed; isolated in-memory database and temporary media.
- 31 frontend test callbacks passed: 17 configurator, 8 header-navigation and 6 vehicle
  quick-selector cases. The shell Node executable is absent; the existing CommonJS
  tests and node:assert assertions ran in the available bundled Node runtime through
  a callback collector and VM. An initial node:test.run attempt in the REPL timed
  out without a test result; the callback execution completed all cases. No package
  or browser-testing framework was installed.
- Django system checks passed; migration dry-run reported no changes. Interpreter:
  `.venv/bin/python`, Python 3.13.1 (the previously documented venv/py313 path is absent).
- Real in-app browser verification used a localhost preview backed by a separate
  SQLite copy. MY2021 JL retained its actual 73 configurations and 24 displayed labels.
  Additional 2022–2026 year fixtures with 4/6/7/8/12 trims existed only in that copy.
- Repeated native mouse clicks at fully visible nearby trims preserved scrollTop 438
  and pageY 649 exactly. Keyboard Tab/Enter retained scrollTop 438, native focus and
  a solid focus-visible outline. Locator helpers can scroll targets before clicking;
  native pointer coordinates were used to distinguish tool scrolling from app behavior.
- Initial `?year=2021&trim=Willys%20Sport#configurations` showed the final selected
  trim fully, with approximately 4px clearance for its focus outline. Mobile 375px
  viewport had no horizontal list or page overflow. Viewport override was reset;
  preview tab closed and temporary preview server stopped.

Measured browser layout for one-line fixture labels (CSS pixels at default font):

| Trims | List height | Scroll needed |
| --- | ---: | --- |
| 4 | 185.24 | No |
| 6 | 277.46 | No |
| 7 | 323.57 | No |
| 8 | 369.68 | No |
| 12 | 369.78 | Yes |

The small eighth-row rounding difference is normal CSS subpixel layout. No fixed
height creates empty rows. These browser measurements are recorded in
[verification details](configurator-trim-selector-browser-verification.json).

## Manual reproduction

1. Open Wrangler JL with `?year=2021#configurations`; the first displayed trim is
   selected automatically. Scroll the page so the whole trim list is visible.
2. Scroll inside the trim list to Unlimited Rubicon/Sahara. Click nearby fully visible
   trims repeatedly. The list and page stay where they were; continue wheel scrolling.
3. Tab to a neighboring trim and press Enter. Confirm visible focus and preserved
   list position. Use browser Back/Forward and confirm the selected trim is visible.
4. Open `?year=2021&trim=Willys%20Sport#configurations` directly. The final button must
   be fully visible without scrolling the list to its top or centering the selection.
5. Switch years; confirm refreshed choices and a fresh list position. On an isolated
   development copy or test fixture, repeat with 4/6/7/8/12 labels: natural heights for
   the first four cases, an eight-row cap with scrolling for 12. Do not add fixtures
   to the operational database.
6. At 375px width or 200% zoom, confirm wrapped labels remain reachable, no horizontal
   overflow appears and keyboard focus remains visible. Zoom was not separately
   exercised in the browser session; this remains a useful manual acceptance check.

## Preservation and checkpoint

Operational database SHA-256 before/after:
`sha256:c37823955537d922c708d091a1494188c80f3cdc458b480c0fa955106d752ef6`.
Read-only totals remain 934 VehicleDefinitions / 3,148 receipts / 159 correspondences.
No canonical data, ingestion, drivetrain presentation, contracts or migrations changed.
Only selector JavaScript/CSS/template, related tests and documentation are included
in the authorized main-branch commit. Operational db.sqlite3 remains unstaged and
intentionally differs from Git's sanitized checkpoint. No push or drive-wheel work.
