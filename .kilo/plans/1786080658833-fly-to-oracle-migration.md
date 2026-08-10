# Test-user accounts (limited per-project role)

## Goal

As an admin, generate credentials for "test users": each test user can log in
with name+password, create **one** project (their own), vote, add options, and
invite others (join link) to do the same in that project — without admin
powers and without seeing other projects.

## Decisions (confirmed)

| Decision | Choice |
|---|---|
| Credential creation | Admin UI tab ("Test users"): type a name → app generates a password → shows it once → stores a hash |
| Storage | `data/.users.json`, stdlib `hashlib.pbkdf2_hmac` (per-user salt), `chmod 600` after write; already gitignored via `data/*` |
| Test user voting | Their own personal voting link (reuse the existing `/vote/...` page); auto-create them as an evaluator on first login |
| Project scoping | One project per user, key = `_label_to_key(username)`; `owner` marker in `config.json` enforces isolation |
| Auth | Shared login page checks admins, then users; session stores role (`admin` / `user`) |

## Implementation

### 1. New module `src/should_we/users.py` (~50 lines)

- `users_path() -> Path` → `data_dir() / ".users.json"`
- `load_users() -> dict[str, str]` (name → pbkdf2 hash), `save_users(dict)` with `chmod 600`
- `hash_password(pw, salt) -> str` via `hashlib.pbkdf2_hmac("sha256", ...)`
- `create_user(name) -> (password, error)` — reject blank/dup names and keys that collide with an existing project (`project_paths(key)[0].exists()`); generate `secrets.token_urlsafe(12)`; store hash
- `verify_user(name, pw) -> bool` (constant-time compare, `secrets.compare_digest`)
- `delete_user(name) -> None`
- No locking (`ponytail: single-file store, fine at this scale; per-file locks if concurrent admins matter`)

### 2. `config.py` — owner marker

- Add `owner: str | None = None` field to `ScoringConfig`; persist/load it in `save_config`/`load_config` (absent in old files → `None`, backward compatible).

### 3. `ui.py`

- **Login** (`_login_page` + `_check_login`): try admins, then users (`verify_user`). `_try_login` sets `app.storage.user["role"]` and `app.storage.user["name"]`. Update the "Admin area" caption to a neutral one.
- **`index()`** branches by role:
  - admin → unchanged behavior
  - user → `_user_home(name)`:
    - Re-validate the account still exists (`load_users()`); if deleted → clear session, show login
    - `key = _label_to_key(name)`; if project missing or `config.owner != name` → render a create-project form (reuse `setup_panel` logic: templates, features; project name field hidden/pre-filled with their name, and **the save handler forces `project=pkey` of the username**, sets `owner=name`)
    - If project exists → show the project's Rankings content: `_invite_card(key, config)` + `_results_list(key, config)` (non-readonly: they may delete options in their own project), a "Vote & add options" button → `f"/vote/{key}/{get_or_create_token(key, name)}"` (auto-creates them as evaluator on first login), and a "Copy results link" affordance
    - No project dropdown, no Delete-project button, no Setup tab for other keys
  - `?project=` query param: for users, only honored when it equals their key; `tab=` ignored
- **Admin "Test users" tab** (`test_users_panel`, refreshable, shown alongside Setup/Rankings):
  - List existing users (name; masked/placeholder password hint)
  - "Create" → name input → dialog shows the generated password once (copy button) → "Delete" per row with optional "also delete their project" (confirm dialog)
- **Leave unchanged**: `/results/{project}` (token-less) stays admin-only — test users use the token'd results link from their invite card; join/vote pages are already token-scoped; `_extend_link`/`_regenerate` are safe on their own project (reused as-is).

### 4. Tests — `tests/test_users.py` (mirror `test_auth.py` style, monkeypatch)

- create/verify roundtrip; wrong password fails; duplicate name rejected; key-collision rejected (pre-existing project at that key); delete_user removes; load/save roundtrip with 600 perms; login routing prefers admins over users.

## Security boundaries (must hold)

- A test user can only ever reach their own project: `index()` scopes state to their key; `_set_project`/dropdown never offered; `?project=` cross-key ignored; `/results/<other>` is admin-only.
- User create-form refuses to overwrite a project at their key that isn't theirs (`owner` mismatch).
- Password shown once; only the hash is stored; fail closed when the users file is unreadable.

## Validation

- `pixi run check` (ruff + format + pytest, incl. new tests)
- Manual: admin creates test user → logs in as user → creates project → votes/adds option via own voting link → invites a second person via join link (they vote too) → user sees rankings; verify user cannot open `/results/<other>` or `/?project=<other>`; admin sees all projects + test user's data; delete test user → login blocked, project remains unless "delete project" checked.

## Rollout

- `git push`, then on the VM: `cd /opt/should-we && git pull && sudo docker compose up -d --build`
- Additive feature; existing admin flow and all join/vote links unaffected. `data/.users.json` appears on first user creation (gitignored already).
