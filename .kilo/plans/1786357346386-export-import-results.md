# Export/Import Project Data (should-we)

Admins and test users can download a full project backup (one JSON file) and import it back. No new dependencies, no new files (one added test in an existing file). Existing button labels and element kinds stay identical — `test_ui_flow.py` / `test_ui_panel.py` keep passing.

## Format: single JSON bundle (decision, user-approved)

Storage is already three JSON files per project (`config.json`, `options.json`, `votes.json` — `project_paths()` in `src/should_we/config.py:51`). JSON is the only lossless stdlib round-trip:

- **CSV rejected** — existing `_csv_content` (ui.py:481) only exports per-evaluator *combined* scores; per-feature scores, weights, voting tokens, notes and vote timestamps don't survive → import would silently corrupt.
- **TOML/YAML rejected** — writing TOML needs `tomli_w`, YAML needs PyYAML; both are new deps for what stdlib `json` does.

Bundle schema (one string + one int — cheap insurance for a cross-instance file format):

```json
{
  "format": "should-we-results",
  "version": 1,
  "exported_at": "<iso timestamp>",
  "config":  { ...verbatim config.json... },
  "options": [ ...verbatim options.json... ],
  "votes":   { ...verbatim votes.json... }
}
```

## Semantics (user-approved)

- **Export**: "Export data" button next to the existing "Export CSV" in the `_results_list` button row (ui.py:380) — visible to admins (rankings tab) and test users (home page), since that row already renders for both (`readonly=False`). The results *page* (`readonly=True`) stays export-free.
- **Admin import**: creates a **new** project from the bundle (key = `_label_to_key(project_name)`). If that key already exists → negative notify, nothing touched (non-destructive). On success: `_set_project(key)` auto-selects it and refresh panels.
- **Test-user import**: **replaces** their own project (their home is hard-locked to `_label_to_key(name)` — a new project would be invisible to them). The dialog text explicitly warns "replaces all your project's data" (same confirmation pattern as existing delete dialogs). Force `owner` back to their name after import, or their home falls back to the setup form (`config.owner != name` check in `_user_home_body`, ui.py:695).
- Voting tokens, join token, expiry come along verbatim — restored links keep working.

## Tasks

1. **`src/should_we/storage.py` — two functions**
   - `export_project(project: str) -> dict` (near `load_votes`, ~line 170): read `config.json` / `options.json` / `votes.json` via existing `project_paths` / `_read_json` / `load_votes`, return the bundle dict above.
   - `import_project(project: str, data: dict) -> int` (returns option count): **validate at this trust boundary** — top-level dict with `format == "should-we-results"`, `version` an int, `config` dict with non-empty `features` list and `project_name` str, `options` list, `votes` dict; raise `ValueError` on any violation. Write the three files into `project_paths(project)` (reuse `_write_json`, which handles mkdir; votes.json is a dict — `_write_json`'s `list[dict]` hint is already loose, `load_votes` returns dict).
   - Keep raw data as-is; do NOT re-run `reprocess_all` (exported breakdown is already valid).

2. **`src/should_we/ui.py` — buttons + import dialog** (in `_results_list`, ~line 380)
   - Add to the existing `flex-col sm:flex-row gap-2 sm:items-center` row (both get `w-full sm:w-auto`):
     - `ui.button("Export data", icon="file_download")` → `ui.download(json.dumps(export_project(project), indent=2) + "\n", f"{project}-export.json")`.
     - `ui.button("Import data", icon="file_upload")` → opens the import dialog.
   - Import dialog (created inside `_results_list`, same pattern as the delete-option dialog):
     - Label: admin → "Imports a should-we export as a new project."; test user → "This replaces all your project's data." (distinguish via `_is_admin()`).
     - `ui.upload(on_upload=..., auto_upload=True, max_files=1).props('accept=".json"')` — built-in NiceGUI element, no dep.
     - `on_upload`: `json.loads(e.content.read().decode("utf-8"))`; on `ValueError`/`json.JSONDecodeError` → `ui.notify("Not a valid should-we export.", type="negative")`. On success show a status label ("Bundle OK: {project_name} · {n} options") + button row `justify-end gap-2 mt-4 flex-wrap`: Cancel / Import.
     - **Import on_click**:
       - Admin: `key = _label_to_key(parsed["config"]["project_name"])`; if `key in list_projects()` → negative notify "already exists"; else `import_project(key, parsed)`, `_set_project(key)` (ui.py:142 — refreshes panels + dropdown), positive notify, close dialog.
       - Test user: `import_project(key, parsed)` then force `owner` — simplest: read back the written config and rewrite with `owner=name` via `save_config(replace(load_config(key), owner=name), project=key)`; refresh `_user_home_body`, positive notify, close dialog.
   - Closure state (`parsed` dict) inside the refreshable is fine — the dialog is rebuilt on refresh like existing dialogs.

3. **`tests/test_core.py` — one round-trip test** (ponytail: the single check that fails if this logic breaks)
   - Save a config with features + an evaluator, `save_option` with per-feature scores + notes, `save_vote`; `export_project` → `import_project` into a fresh key → assert `load_config` / `load_options` (scores, notes) / `load_votes` match the originals; assert `import_project` raises `ValueError` on a junk dict (`{"format": "nope"}`).

## Validation

- `pixi run check` (ruff + pytest). Existing UI tests are safe: no label/order changes to existing buttons; `ui.upload` is not a `ui.input`, so `inputs[0]`/`max(e.id)` index assumptions in `test_ui_flow.py` hold.
- Manual: `pixi run ui` → admin: Export data on Rankings tab → import into a fresh instance/rename → project appears in dropdown. Test user: export from their home, import → their data is replaced, home still renders (owner preserved).

## Risks / notes

- Test-user import is destructive by nature — the dialog text is the confirmation; keep it explicit.
- Admin import collision → notify, never overwrite.
- If a future format bump is needed, the `version` field gates it; schema is per-field validated at upload (trust boundary).
