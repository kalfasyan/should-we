# Mobile-Friendly UI Polish (should-we)

Single-file change in `src/should_we/ui.py` (NiceGUI app). No new dependencies, no new files. All button labels and element kinds stay identical, so `tests/test_ui_flow.py` / `test_ui_panel.py` (which match by label text) keep passing.

## 1. Global theme + CSS (one shared block)

After the existing `ui.add_head_html(...)` PWA block (~line 58), add:

- `app.colors(primary="#6366f1", secondary="#8b5cf6", accent="#22d3ee")` — indigo primary, coherent dark-mode palette; leave negative/warning/positive as Quasar defaults.
- `ui.add_css("...", shared=True)` containing one mobile-first stylesheet:
  - `@media (max-width: 640px)`: `.q-header { height: auto !important; min-height: 56px; }` so wrapped header content grows instead of overflowing the fixed 50px header.
  - Same breakpoint: `.q-btn:not(.q-btn--dense):not(.q-btn--flat):not(.q-btn--round) { min-height: 44px; }` and `.q-field__control { min-height: 44px; }` — proper touch targets; dense/flat/round (link rows, delete icons) stay small.
  - `.q-card { border-radius: 12px; }` and a subtle 1px border (`border: 1px solid rgba(255,255,255,.06)`) for card separation on dark bg.
  - `.q-expansion-item .q-item { border-radius: 8px; }` and smooth `transition` on buttons/cards (150ms).

## 2. Headers wrap on mobile

- `index()` admin header (~line 1106): change container to `items-center justify-between px-4 flex-wrap gap-2`; project `_dropdown` class `w-48` → `w-full sm:w-48` (wraps to its own line on phones). Add `flex-wrap gap-2` to the logo row and the right-side row.
- `_user_home()` header (~line 658): add `flex-wrap gap-2` to container; keep badge, hide the name label on phones (`hidden sm:inline` on the `ui.label(name)`).
- Vote/results headers (lines 768, 1034) already have `flex-wrap gap-2` — only add `min-h-10` to the results header buttons (already on vote header, line 776/782).

## 3. Fixed-width inputs → responsive

- `join_page` name input (~line 963): `w-64` → `w-full sm:w-64`.
- `_vote_body` "Option name" and "Link or note" (lines 904–905): `w-64` → `w-full sm:w-64`.
- Setup/user-create inputs already use `w-full sm:w-64` — leave.

## 4. Action rows stack on mobile (full-width buttons)

- `_results_list` button row (lines 363–383): `ui.row().classes("gap-2 items-center")` → `flex-col sm:flex-row sm:items-center`; each of the 3 buttons gets `w-full sm:w-auto`.
- `_user_home_body` button row (lines 683–695): same treatment for "Vote & add options" / "Copy results link".
- Vote page note/vote row (line 882): add `flex-wrap`; "Save my vote" gets `w-full sm:w-auto`.
- Join button (~line 975): add `w-full sm:w-auto`.
- Login button (line 1025) already `w-full` — leave.
- Dialog action rows (lines 177, 546, 573, 617, 1132): add `flex-wrap` to `justify-end gap-2 mt-4` rows.

## 5. Centering pages don't overflow with mobile keyboard

`h-screen` → `min-h-screen` in: `join_page` expired card (line 947), `_bad_link` (lines 991, 1006), `_login_page` (line 998).

## 6. Charts read better on narrow screens

- Bar chart (`_charts_body`, ~line 395): grid `left: 40→36, right: 16→12, bottom: 60→70`; axisLabel add `"interval": 0, "hideOverlap": True` (keep rotate 30, fontSize 10).
- Heatmap (~line 426): grid `left: 80→64`; keep everything else.

## 7. Rankings expansion rows

Evaluator label `w-32` → `w-24 min-w-0` (line 351) so the score bar gets more room on phones; score column `w-14` stays.

## Validation

- `pixi run check` (ruff lint + format + pytest; UI tests match by label text — unchanged labels keep them green).
- Manual: `pixi run ui`, view at 375px (devtools) — admin header wraps, project dropdown full-width, join/vote pages have full-width inputs, action buttons stack, nothing overflows horizontally; check desktop (≥1024px) unchanged.
