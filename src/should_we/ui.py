from __future__ import annotations

import csv
import io
import json
import os
import secrets
from pathlib import Path

from nicegui import app, ui

from .config import (
    Feature,
    ScoringConfig,
    _label_to_key,
    add_evaluator,
    default_join_expiry,
    delete_project,
    extend_join_link,
    get_join_token,
    get_or_create_token,
    join_link_days_left,
    join_link_expired,
    list_projects,
    load_config,
    regenerate_token,
    save_config,
    set_weights,
)
from .scoring import compute_combined, disagreement
from .storage import (
    delete_option,
    find_option,
    load_options,
    load_votes,
    reprocess_all,
    save_option,
    save_vote,
    update_notes,
)
from .users import create_user, delete_user, load_users, verify_user

_assets = Path(__file__).resolve().parent.parent.parent / "docs" / "assets"
if _assets.is_dir():
    app.add_static_files("/assets", str(_assets))

_pwa = Path(__file__).resolve().parent / "pwa"
app.add_static_file(local_file=_pwa / "manifest.json", url_path="/manifest.json")
app.add_static_file(local_file=_pwa / "sw.js", url_path="/sw.js")
app.add_static_files("/pwa", str(_pwa))
ui.add_head_html(
    '<link rel="manifest" href="/manifest.json">'
    '<link rel="apple-touch-icon" href="/pwa/icon-180.png">'
    '<meta name="theme-color" content="#121212">'
    '<script>if ("serviceWorker" in navigator) {'
    'window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));'
    "}</script>",
    shared=True,
)

app.colors(primary="#6366f1", secondary="#8b5cf6", accent="#22d3ee")
ui.add_css(
    """
    .q-card { border-radius: 12px; border: 1px solid rgba(255,255,255,.06); }
    .q-expansion-item .q-item { border-radius: 8px; }
    .q-card, .q-btn { transition: all .15s ease; }
    @media (max-width: 640px) {
        .q-header { height: auto !important; min-height: 56px; }
        .q-btn:not(.q-btn--dense):not(.q-btn--flat):not(.q-btn--round) {
            min-height: 44px;
        }
        .q-field__control { min-height: 44px; }
    }
    """,
    shared=True,
)

_project_key: str | None = None
_config: ScoringConfig | None = None
_dropdown: ui.select | None = None
_panels: ui.tab_panels | None = None
_tab_rankings: ui.tab | None = None


def _init_state():
    global _project_key, _config
    projects = list_projects()
    if projects:
        _project_key = projects[0]
        _config = load_config(_project_key)


def _admins() -> dict[str, str]:
    """Admin name → password map from SHOULD_WE_ADMINS (JSON). Empty means no admins configured."""
    raw = os.environ.get("SHOULD_WE_ADMINS", "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _check_login(name: str | None, password: str | None) -> bool:
    expected = _admins().get((name or "").strip())
    return bool(expected) and secrets.compare_digest(expected, password or "")


def _login_role(name: str | None, password: str | None) -> str | None:
    """Admin credentials win; otherwise fall back to test-user accounts."""
    if _check_login(name, password):
        return "admin"
    if verify_user(name or "", password or ""):
        return "user"
    return None


def _is_admin() -> bool:
    try:
        return bool(app.storage.user.get("admin"))
    except RuntimeError:  # storage_secret missing → fail closed
        return False


def _session_user() -> str | None:
    try:
        name = app.storage.user.get("name")
    except RuntimeError:
        return None
    return name or None


def _is_user_project(name: str | None, project: str) -> bool:
    return bool(name) and _label_to_key(name) == project


def _results_allowed(token: str, join_token: str, is_admin: bool) -> bool:
    return is_admin or bool(join_token) and secrets.compare_digest(token or "", join_token)


def _set_project(key: str):
    global _project_key, _config
    try:
        _config = load_config(key)
        _project_key = key
    except SystemExit:
        projects = list_projects()
        if projects:
            _set_project(projects[0])
        return
    rankings_panel.refresh()
    setup_panel.refresh()
    if _dropdown:
        _dropdown.visible = True
        _dropdown.options = list_projects()
        _dropdown.value = key
        _dropdown.update()


def _on_project_change(e):
    _set_project(e.value)


def _open_delete_dialog(dialog, label):
    label.text = f"Delete project '{_project_key}' and all its options?"
    dialog.open()


def _do_delete(dialog):
    global _project_key, _config
    if not _project_key:
        return
    deleted = _project_key
    delete_project(_project_key)
    dialog.close()
    ui.notify(f"Deleted project '{deleted}'.", type="warning")
    projects = list_projects()
    if projects:
        _set_project(projects[0])
    else:
        _project_key = None
        _config = None
        if _dropdown:
            _dropdown.visible = False
        rankings_panel.refresh()
        setup_panel.refresh()


def _option_delete_dialog(name: str, project: str) -> ui.dialog:
    with ui.dialog() as dialog, ui.card():
        ui.label(f"Delete option '{name}'?").classes("text-h6")
        ui.label("This cannot be undone.")
        with ui.row().classes("justify-end gap-2 mt-4 flex-wrap"):
            ui.button("Cancel", on_click=dialog.close)
            ui.button(
                "Delete",
                on_click=lambda: _do_delete_option(dialog, name, project),
                color="red",
            )
    return dialog


def _do_delete_option(dialog, name: str, project: str | None = None) -> None:
    project = project or _project_key
    if not project:
        return
    delete_option(name, project)
    dialog.close()
    ui.notify(f"Deleted option '{name}'.", type="warning")
    rankings_panel.refresh()
    _user_home_body.refresh()


def _score_bar(value: float) -> None:
    ui.linear_progress(value=min(max(value / 5.0, 0.0), 1.0), show_value=False).classes("flex-grow")


def _abs_url(path: str) -> str:
    path = "/" + path.lstrip("/")
    try:
        req = ui.context.client.request
        origin = f"{req.url.scheme}://{req.headers.get('host', 'localhost')}"
    except Exception:
        origin = ""
    return f"{origin}{path}"


def _copy_text(text: str, label: str = "Link copied") -> None:
    # ponytail: execCommand works on plain http (LAN) too; navigator.clipboard
    # silently fails outside https/localhost
    js = (
        f"const ta=document.createElement('textarea');ta.value={json.dumps(text)};"
        "document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();"
    )
    ui.run_javascript(js)
    ui.notify(label, type="positive")


def _invite_card(project: str, config: ScoringConfig) -> None:
    with ui.card().classes("w-full mb-4"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("how_to_vote").classes("text-primary")
            ui.markdown("### 🔗 Share this one link with your group").classes("mb-0")
        ui.label(
            "Everyone who opens it picks a name, sets how much each feature matters "
            "to them, then adds options and votes. No account, no install."
        ).classes("text-caption")
        join_url = _abs_url(f"join/{project}/{get_join_token(project)}")
        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
            ui.input(value=join_url).classes("w-full sm:w-auto sm:flex-grow min-w-0").props(
                "readonly dense"
            )
            ui.button(
                "Copy join link",
                on_click=lambda: _copy_text(join_url, "Join link copied"),
                icon="copy",
            ).props("outline")

        if config.join_expires_at:
            left = join_link_days_left(config)
            expired = left is not None and left < 0
            text = f"Join link expires: {config.join_expires_at}"
            if expired:
                text += " — expired, no one new can join"
            elif left is not None and left <= 7:
                text += f" ({left} day{'s' if left != 1 else ''} left)"
            color = (
                "text-negative"
                if expired
                else ("text-warning" if left is not None and left <= 7 else "text-grey-6")
            )
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(text).classes(f"text-caption {color}")
                ui.button(
                    "Extend 30 days",
                    on_click=lambda: _extend_link(project),
                    icon="update",
                ).props("outline dense size=sm")

        if not config.evaluators:
            ui.label("No one has joined yet — send them the link above.").classes(
                "text-caption text-grey-6"
            )
        else:
            ui.markdown("#### 👥 Joined people").classes("mb-1")
            for ev in config.evaluators:
                url = _abs_url(f"vote/{project}/{get_or_create_token(project, ev.name)}")
                with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                    ui.label(ev.name).classes("w-full sm:w-28")
                    ui.input(value=url).classes("w-full sm:w-auto sm:flex-grow min-w-0").props(
                        "readonly dense"
                    )
                    ui.button(
                        "Copy",
                        on_click=lambda u=url, n=ev.name: _copy_text(u, f"{n}'s link copied"),
                        icon="copy",
                    ).props("outline dense size=sm")
                    ui.button(
                        icon="refresh",
                        on_click=lambda n=ev.name: _regenerate(n, project),
                    ).props("flat round size=sm").tooltip(
                        "New link for this person (old one stops working)"
                    )


def _extend_link(project: str) -> None:
    global _config
    expires = extend_join_link(project)
    if _project_key == project:
        _config = load_config(project)
    rankings_panel.refresh()
    _user_home_body.refresh()
    ui.notify(f"Join link extended to {expires}.", type="positive")


@ui.refreshable
def _vote_status(project: str, config: ScoringConfig) -> None:
    options = load_options(project)
    if not options:
        return
    votes = load_votes(project)
    with ui.row().classes("gap-4 mb-2 flex-wrap"):
        for ev in config.evaluators:
            voted = len(votes.get(ev.name, {}))
            ui.label(f"{'✅' if voted else '⏳'} {ev.name}: {voted}/{len(options)} voted").classes(
                "text-caption text-primary"
            )


@ui.refreshable
def _results_list(project: str, config: ScoringConfig, *, readonly: bool = False) -> None:
    options = load_options(project)
    votes = load_votes(project)
    sorted_opts = sorted(options, key=lambda o: compute_combined(o.breakdown), reverse=True)

    if not options:
        with ui.card().classes("w-full"):
            with ui.column().classes("gap-1"):
                ui.markdown("### 📭 No options yet").classes("mb-1")
                ui.label(
                    "Anyone can add the first one — open your voting link (join link above) "
                    "and use the 'Add an option' box."
                )
        return

    _vote_status(project, config)
    _charts_body(sorted_opts, config)

    ui.markdown(
        "Options ranked by combined score (average of all evaluators). "
        "Click any option to see each person's individual score."
    ).classes("mb-4")

    with ui.column().classes("w-full gap-2"):
        for i, opt in enumerate(sorted_opts):
            combined = compute_combined(opt.breakdown)
            icon = ["military_tech", "workspace_premium", "star"][i] if i < 3 else None
            d = disagreement(opt.breakdown)
            tag = "  🤔" if d is not None and d >= 1.5 else ""
            with ui.expansion(f"#{i + 1}  {opt.name}  —  {combined:.3f}{tag}", icon=icon).classes(
                "w-full"
            ):
                for ev in config.evaluators:
                    score = opt.breakdown.get(ev.name)
                    chip = "✅" if opt.name in votes.get(ev.name, {}) else "⏳"
                    with ui.row().classes("w-full items-center gap-3"):
                        ui.label(f"{chip} {ev.name}").classes("w-24 min-w-0 text-caption")
                        if score is None:
                            ui.label("not voted").classes("text-grey-6 text-caption")
                        else:
                            _score_bar(score)
                            ui.label(f"{score:.3f}").classes("w-14 text-right")
                if not readonly:
                    del_dialog = _option_delete_dialog(opt.name, project)
                    ui.button(icon="delete", on_click=del_dialog.open).props(
                        "flat round size=sm"
                    ).classes("text-red").tooltip("Delete option")

    if not readonly:
        with ui.row().classes("flex-col sm:flex-row gap-2 sm:items-center"):
            ui.button(
                "Copy results link",
                on_click=lambda: _copy_text(
                    _abs_url(f"results/{project}/{get_join_token(project)}"), "Results link copied"
                ),
                icon="link",
            ).props("outline").classes("w-full sm:w-auto")
            ui.button(
                "Reprocess",
                on_click=lambda p=project: _reprocess(p),
                icon="refresh",
            ).classes("w-full sm:w-auto")
            ui.button(
                "Export CSV",
                on_click=lambda: ui.download(
                    _csv_content(config, sorted_opts), f"{project}-rankings.csv"
                ),
                icon="download",
            ).classes("w-full sm:w-auto")
        # ponytail: poll only the tiny status line, never the list itself —
        # rebuilding expansions every few seconds makes them unclickable
        ui.timer(5.0, lambda: _vote_status.refresh())


def _charts_body(sorted_opts, config: ScoringConfig) -> None:
    names = [o.name for o in sorted_opts]
    with ui.column().classes("w-full gap-2 mb-4"):
        ui.echart(
            {
                "tooltip": {},
                "grid": {"left": 36, "right": 12, "top": 30, "bottom": 70},
                "xAxis": {
                    "type": "category",
                    "data": names,
                    "axisLabel": {
                        "rotate": 30,
                        "fontSize": 10,
                        "interval": 0,
                        "hideOverlap": True,
                    },
                },
                "yAxis": {"type": "value", "min": 0, "max": 5},
                "series": [
                    {
                        "type": "bar",
                        "data": [round(compute_combined(o.breakdown), 3) for o in sorted_opts],
                    }
                ],
            }
        ).classes("w-full h-64")
        ev_names = [e.name for e in config.evaluators]
        # ponytail: cell "name" carries option · person — note; echarts shows it
        # in the default tooltip as "name : score" (formatter functions can't be
        # serialized into NiceGUI's JSON chart options)
        heat = []
        for oi, opt in enumerate(sorted_opts):
            for ei, ev in enumerate(config.evaluators):
                v = opt.breakdown.get(ev.name)
                if v is not None:
                    cell = f"{opt.name} · {ev.name}"
                    if opt.notes:
                        cell += f" — {opt.notes}"
                    heat.append({"value": [oi, ei, round(v, 3)], "name": cell})
        ui.echart(
            {
                "tooltip": {},
                "grid": {"left": 64, "right": 16, "top": 30, "bottom": 80},
                "xAxis": {
                    "type": "category",
                    "data": names,
                    "axisLabel": {"rotate": 30, "fontSize": 10},
                },
                "yAxis": {"type": "category", "data": ev_names},
                "visualMap": {
                    "min": 0,
                    "max": 5,
                    "calculable": True,
                    "orient": "horizontal",
                    "left": "center",
                    "bottom": 0,
                },
                "series": [{"type": "heatmap", "data": heat, "label": {"show": True}}],
            }
        ).classes("w-full h-72")


def _reprocess(project: str | None = None) -> None:
    reprocess_all(project or _project_key)
    rankings_panel.refresh()
    _user_home_body.refresh()


def _regenerate(evaluator: str, project: str) -> None:
    regenerate_token(project, evaluator)
    ui.notify(f"New link created for {evaluator}.")
    rankings_panel.refresh()
    _user_home_body.refresh()


def _csv_content(config: ScoringConfig, options) -> str:
    ev_names = [ev.name for ev in config.evaluators]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["option", "combined"] + ev_names)
    for opt in options:
        combined = compute_combined(opt.breakdown)
        row = [opt.name, f"{combined:.4f}"] + [
            f"{opt.breakdown.get(name, 0.0):.4f}" for name in ev_names
        ]
        w.writerow(row)
    return buf.getvalue()


@ui.refreshable
def rankings_panel():
    if not _config or not _project_key:
        ui.label("No project selected. Use the dropdown in the top bar.")
        return
    _invite_card(_project_key, _config)
    _results_list(_project_key, _config)


@ui.refreshable
def setup_panel():
    with ui.card().classes("w-full mb-4"):
        with ui.column().classes("gap-1"):
            ui.markdown("### 🛠️ How to set up a project").classes("mb-2")
            ui.label("1. Enter a project name and the features you care about.")
            ui.label("2. Click Save Config — the new project auto-selects in the top bar.")
            ui.label("3. Share the join link from the Rankings tab.")
            ui.label(
                "4. Everyone opens it, picks a name, sets their own weights — "
                "then adds options and votes."
            )

    project_name = ui.input("Project name").classes("w-full sm:w-64")
    feature_labels = ui.textarea("Feature labels (one per line)").classes("w-full sm:w-64")

    template_dir = Path(__file__).resolve().parent / "templates"
    templates = sorted(template_dir.glob("*.json")) if template_dir.is_dir() else []

    def _apply_template(path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        project_name.value = raw["project_name"]
        feature_labels.value = "\n".join(f["label"] for f in raw["features"])
        ui.notify(f"Template '{path.stem}' loaded — adjust and save.", type="positive")

    if templates:
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.select(
                label="Start from template",
                options={p.stem: p.stem for p in templates},
                on_change=lambda e: _apply_template(template_dir / f"{e.value}.json"),
            ).classes("w-full sm:w-56")

    def _save_config():
        pname = project_name.value.strip()
        if not pname:
            ui.notify("Project name required.", type="negative")
            return
        feat_labels = [
            label.strip() for label in feature_labels.value.strip().split("\n") if label.strip()
        ]
        if not feat_labels:
            ui.notify("Enter at least one feature.", type="negative")
            return
        pkey = _label_to_key(pname)
        features = [Feature(key=_label_to_key(label), label=label) for label in feat_labels]
        save_config(
            ScoringConfig(
                project_name=pname,
                features=features,
                evaluators=[],
                join_expires_at=default_join_expiry(),
            ),
            project=pkey,
        )
        ui.notify(f"Project '{pname}' saved!", type="positive")
        _set_project(pkey)
        join_url_inp.value = _abs_url(f"join/{pkey}/{get_join_token(pkey)}")
        ready_dialog.open()

    with ui.dialog() as ready_dialog, ui.card():
        ui.markdown("### 🎉 Project ready!").classes("mb-1")
        ui.label("Share the join link with your group:")
        join_url_inp = ui.input().classes("w-full").props("readonly")
        with ui.row().classes("justify-end gap-2 mt-4 flex-wrap"):
            ui.button(
                "Copy",
                on_click=lambda: _copy_text(join_url_inp.value, "Join link copied"),
                icon="copy",
            ).props("outline")
            ui.button("Go to Rankings", on_click=lambda: _go_rankings(ready_dialog), icon="launch")

    ui.button("Save Config", on_click=_save_config, icon="save")


@ui.refreshable
def test_users_panel():
    with ui.card().classes("w-full mb-4"):
        with ui.column().classes("gap-1"):
            ui.markdown("### 🧪 Test users").classes("mb-2")
            ui.label(
                "Each test user gets their own private project — no admin powers. "
                "The password is shown once; only its hash is stored."
            )
    with ui.dialog() as cred_dialog, ui.card():
        ui.markdown("### 🔑 Test user created").classes("mb-1")
        cred_name = ui.label().classes("text-caption")
        cred_password = ui.input().props("readonly").classes("w-full")
        ui.label("Share name + password once — it cannot be shown again.").classes(
            "text-caption text-warning"
        )
        with ui.row().classes("justify-end gap-2 mt-4 flex-wrap"):
            ui.button(
                "Copy password",
                on_click=lambda: _copy_text(cred_password.value, "Password copied"),
                icon="copy",
            ).props("outline")
            ui.button("Done", on_click=cred_dialog.close)

    def _refresh_list_on_close(e) -> None:
        if not e.value:
            test_users_panel.refresh()

    cred_dialog.on_value_change(_refresh_list_on_close)

    new_name = ui.input("Name").classes("w-full sm:w-64")

    def _create():
        try:
            password, error = create_user(new_name.value)
        except OSError as e:
            ui.notify(f"Could not write the users file: {e}", type="negative")
            return
        if error:
            ui.notify(error, type="negative")
            return
        created_name = (new_name.value or "").strip()
        new_name.value = ""
        cred_name.text = f"Name: {created_name}"
        cred_password.value = password
        cred_dialog.open()

    ui.button("Create user", on_click=_create, icon="person_add")

    users = load_users()
    if not users:
        ui.label("No test users yet.").classes("text-caption text-grey-6")
        return
    ui.markdown("#### 👥 Existing test users").classes("mt-4 mb-1")
    for name in sorted(users):
        with ui.row().classes("w-full items-center gap-2"):
            ui.label(name).classes("flex-grow")
            with ui.dialog() as del_dialog, ui.card():
                ui.markdown(f"### Delete {name}?").classes("mb-1")
                also_proj = ui.checkbox("Also delete their project")
                with ui.row().classes("justify-end gap-2 mt-4 flex-wrap"):
                    ui.button("Cancel", on_click=del_dialog.close)
                    ui.button(
                        "Delete",
                        color="red",
                        on_click=lambda d=del_dialog, n=name, c=also_proj: _do_delete_user(
                            d, n, c.value
                        ),
                    )
            ui.button(icon="delete", on_click=del_dialog.open).props("flat round size=sm").classes(
                "text-red"
            )


def _do_delete_user(dialog, name: str, also_project: bool) -> None:
    delete_user(name)
    if also_project:
        delete_project(_label_to_key(name))
    dialog.close()
    ui.notify(f"User '{name}' deleted.", type="warning")
    test_users_panel.refresh()


def _go_rankings(dialog) -> None:
    dialog.close()
    if _panels is not None and _tab_rankings is not None:
        _panels.value = _tab_rankings


def _vote_as_user(project: str, name: str) -> None:
    add_evaluator(project, name)
    ui.navigate.to(f"/vote/{project}/{get_or_create_token(project, name)}")


def _user_home(name: str) -> None:
    if name not in load_users():
        app.storage.user.clear()
        _login_page()
        return
    ui.dark_mode().enable()
    key = _label_to_key(name)
    with ui.header(elevated=True).classes("items-center justify-between px-4 flex-wrap gap-2"):
        with ui.row().classes("items-center gap-3"):
            ui.image("/assets/logo.png").classes("w-9")
            ui.label("should-we").classes("text-h5")
        with ui.row().classes("items-center gap-2"):
            ui.badge("test user", color="secondary", outline=True).tooltip("Logged in as test user")
            ui.label(name).classes("hidden sm:inline text-caption")
            ui.button("Logout", on_click=_logout, icon="logout", color="white").props(
                "unelevated"
            ).classes("text-black")
    with ui.column().classes("w-full max-w-4xl mx-auto px-4 py-4"):
        _user_home_body(name, key)


@ui.refreshable
def _user_home_body(name: str, key: str) -> None:
    try:
        config = load_config(key)
    except SystemExit:
        config = None
    if config is None or config.owner != name:
        _user_create_form(name, key)
        return
    _invite_card(key, config)
    _results_list(key, config)
    with ui.row().classes("flex-col sm:flex-row gap-2 sm:items-center"):
        ui.button(
            "Vote & add options",
            icon="how_to_vote",
            on_click=lambda: _vote_as_user(key, name),
        ).props("unelevated").classes("w-full sm:w-auto")
        ui.button(
            "Copy results link",
            icon="link",
            on_click=lambda: _copy_text(
                _abs_url(f"results/{key}/{get_join_token(key)}"), "Results link copied"
            ),
        ).props("outline").classes("w-full sm:w-auto")


def _user_create_form(name: str, key: str) -> None:
    with ui.card().classes("w-full mb-4"):
        with ui.column().classes("gap-1"):
            ui.markdown("### 🛠️ Create your project").classes("mb-2")
            ui.label(f"Your project lives at '{key}' — only you can see it.")
            ui.label("1. Enter the features you care about (one per line).")
            ui.label("2. Click Create — then share your join link from the Rankings view.")
    ui.input("Project name", value=name).props("readonly").classes("w-full sm:w-64")
    feature_labels = ui.textarea("Feature labels (one per line)").classes("w-full sm:w-64")

    template_dir = Path(__file__).resolve().parent / "templates"
    templates = sorted(template_dir.glob("*.json")) if template_dir.is_dir() else []

    def _apply_template(path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        feature_labels.value = "\n".join(f["label"] for f in raw["features"])
        ui.notify(f"Template '{path.stem}' loaded — adjust and save.", type="positive")

    if templates:
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.select(
                label="Start from template",
                options={p.stem: p.stem for p in templates},
                on_change=lambda e: _apply_template(template_dir / f"{e.value}.json"),
            ).classes("w-full sm:w-56")

    def _save():
        feat_labels = [
            label.strip() for label in feature_labels.value.strip().split("\n") if label.strip()
        ]
        if not feat_labels:
            ui.notify("Enter at least one feature.", type="negative")
            return
        try:
            existing = load_config(key)
        except SystemExit:
            existing = None
        if existing is not None and existing.owner != name:
            ui.notify(f"Project '{key}' already exists and isn't yours.", type="negative")
            return
        features = [Feature(key=_label_to_key(label), label=label) for label in feat_labels]
        save_config(
            ScoringConfig(
                project_name=name,
                features=features,
                evaluators=[],
                join_expires_at=default_join_expiry(),
                owner=name,
            ),
            project=key,
        )
        ui.notify(f"Project '{name}' created!", type="positive")
        _user_home_body.refresh()

    ui.button("Create project", on_click=_save, icon="save")


@ui.page("/vote/{project}/{token}")
def vote_page(project: str, token: str):
    ui.dark_mode().enable()
    try:
        config = load_config(project)
    except SystemExit:
        _bad_link()
        return
    evaluator = next((ev for ev, tok in config.voting_tokens.items() if tok == token), None)
    if evaluator is None:
        _bad_link()
        return

    with ui.header(elevated=True).classes("items-center justify-between px-4 flex-wrap gap-2"):
        with ui.column().classes("gap-0"):
            ui.label(f"{config.project_name} — vote").classes("text-h6")
            ui.label(f"voting as {evaluator}").classes("text-caption")
        with ui.row().classes("gap-2 flex-wrap"):
            ui.button(
                "See current results",
                on_click=lambda: ui.navigate.to(f"/results/{project}/{get_join_token(project)}"),
            ).props("outline").classes("min-h-10")
            if _is_user_project(_session_user(), project):
                ui.button(
                    "My project",
                    icon="home",
                    on_click=lambda: ui.navigate.to("/"),
                ).classes("min-h-10")
            else:
                ui.button(
                    "See rankings",
                    icon="leaderboard",
                    on_click=lambda: ui.navigate.to(f"/?project={project}&tab=rankings"),
                ).classes("min-h-10")

    with ui.column().classes("w-full max-w-3xl mx-auto px-4 py-4"):
        if app.storage.user.pop("welcome", False):
            with ui.card().classes("w-full mb-4"):
                ui.markdown(f"### 👋 Welcome, {evaluator}!").classes("mb-1")
                if config.join_expires_at:
                    ui.label(
                        f"The link you joined with is valid until {config.join_expires_at} — "
                        "after that, no new people can join. Your personal voting link below "
                        "keeps working."
                    ).classes("text-caption")
        _vote_body(project, config, evaluator)


@ui.refreshable
def _vote_body(project: str, config: ScoringConfig, evaluator: str) -> None:
    # ponytail: reload every render — the page-level config goes stale after
    # weights are saved, and refresh() re-runs with the old arguments
    config = load_config(project)
    ev_config = next(e for e in config.evaluators if e.name == evaluator)
    options = load_options(project)
    votes = load_votes(project)

    with ui.card().classes("w-full mb-4"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("tune").classes("text-primary")
            ui.markdown(f"### ⚖️ What matters to you in general, {evaluator}?").classes("mb-0")
        ui.label(
            "These are your general priorities — they apply to every option, "
            "not to any specific one. 0 = don't care  |  3 = important  |  5 = dealbreaker"
        ).classes("text-caption")
        sliders: dict[str, ui.slider] = {}
        for feat in config.features:
            with ui.row().classes(
                "w-full items-start gap-1 flex-col sm:items-center sm:gap-0 sm:flex-row"
            ):
                ui.label(feat.label).classes("w-full sm:w-32")
                s = (
                    ui.slider(min=0, max=5, step=1, value=ev_config.weights.get(feat.key, 3))
                    .props("label-always")
                    .classes("w-full sm:w-auto sm:flex-grow")
                )
                sliders[feat.key] = s

        def _save_weights():
            set_weights(project, evaluator, {k: int(v.value) for k, v in sliders.items()})
            ui.notify("Weights saved.", type="positive")
            _vote_body.refresh()

        ui.label("Then press 'Save my weights' — nothing counts until you do.").classes(
            "text-caption text-warning"
        )
        ui.button("Save my weights", on_click=_save_weights, icon="save").props("unelevated")

    if not ev_config.weights:
        ui.label("Save your weights above first — without them your votes don't count.").classes(
            "text-warning mb-2"
        )

    if not options:
        with ui.card().classes("w-full mb-4"):
            ui.label("No options yet — add the first one below 👇").classes("text-grey-6")
    else:
        ui.markdown(
            "For each option, rate how well it does on each feature — "
            "then press **Save vote** (nothing counts until you save)."
        ).classes("mb-2")
        for opt in options:
            with ui.card().classes("w-full mb-4"):
                ui.label(opt.name).classes("text-h6")
                ui.label(
                    "How well does this option do on each feature? (0 = poor  |  5 = excellent)"
                ).classes("text-caption")
                if opt.name in votes.get(evaluator, {}):
                    ui.label("✓ voted").classes("text-positive text-caption")
                ev_inps: dict[str, ui.slider] = {}
                with ui.column().classes("w-full gap-2"):
                    for feat in config.features:
                        with ui.row().classes(
                            "w-full items-start gap-1 flex-col sm:items-center sm:gap-0 sm:flex-row"
                        ):
                            ui.label(feat.label).classes("w-full sm:w-32")
                            s = (
                                ui.slider(
                                    min=0,
                                    max=5,
                                    step=0.5,
                                    value=float(opt.scores.get(evaluator, {}).get(feat.key, 0.0)),
                                )
                                .props("label-always")
                                .classes("w-full sm:w-auto sm:flex-grow")
                            )
                            ev_inps[feat.key] = s
                with ui.row().classes("w-full items-center gap-2 mt-2 flex-wrap"):
                    note_inp = (
                        ui.input(value=opt.notes, placeholder="Link or note")
                        .props("dense")
                        .classes("flex-grow")
                    )
                    ui.button(
                        "Save note",
                        icon="link",
                        on_click=lambda n=opt.name, inp=note_inp: _save_note(project, n, inp.value),
                    ).props("flat dense")
                    ui.button(
                        "Save my vote",
                        icon="save",
                        on_click=lambda n=opt.name, ev=ev_inps: _save_vote(
                            project, evaluator, n, {k: v.value for k, v in ev.items()}
                        ),
                    ).props("unelevated").classes("w-full sm:w-auto")

    with ui.card().classes("w-full mb-4"):
        ui.markdown("### ➕ Add an option").classes("mb-2")
        ui.label("Add one any time — everyone else can vote on it too.").classes("text-caption")
        new_name = ui.input("Option name").classes("w-full sm:w-64")
        new_notes = ui.input("Link or note (optional)").classes("w-full sm:w-64")

        def _add_option():
            name = new_name.value.strip()
            if not name:
                ui.notify("Option name required.", type="negative")
                return
            if find_option(name, project=project):
                ui.notify(
                    "Already exists — pick another name, or update its link/note below.",
                    type="warning",
                )
                return
            save_option(name, {evaluator: {}}, project=project, notes=new_notes.value.strip())
            ui.notify(f"'{name}' added — now rate it above.", type="positive")
            new_name.value = ""
            new_notes.value = ""
            _vote_body.refresh()

        ui.button("Add option", on_click=_add_option, icon="add")

    ui.button(
        "See current results",
        on_click=lambda: ui.navigate.to(f"/results/{project}/{get_join_token(project)}"),
        icon="assessment",
    ).props("outline").classes("w-full")


@ui.page("/join/{project}/{token}")
def join_page(project: str, token: str):
    ui.dark_mode().enable()
    try:
        config = load_config(project)
    except SystemExit:
        _bad_link()
        return
    if not config.join_token or config.join_token != token:
        _bad_link()
        return
    if join_link_expired(config):
        ui.dark_mode().enable()
        with ui.column().classes("items-center justify-center min-h-screen gap-2"):
            ui.label("This join link has expired.").classes("text-h5")
            ui.label(
                f"It stopped working on {config.join_expires_at}. "
                "Ask the project owner for a fresh link."
            ).classes("text-caption")
        return

    with ui.header(elevated=True).classes("items-center justify-between px-4"):
        ui.label(f"Join {config.project_name}").classes("text-h6")

    with ui.column().classes(
        "items-center justify-center min-h-screen gap-2 w-full max-w-2xl mx-auto px-4"
    ):
        ui.markdown(
            "Pick a name — then you'll set your weights and can vote on every option."
        ).classes("text-center")
        name_inp = ui.input("Your name (e.g. Alice)").classes("w-full sm:w-64")

        def _join():
            name = name_inp.value.strip()
            if not name:
                ui.notify("Enter a name.", type="negative")
                return
            add_evaluator(project, name)
            token2 = get_or_create_token(project, name)
            app.storage.user["welcome"] = True
            ui.navigate.to(f"/vote/{project}/{token2}")

        ui.button("Join and vote", on_click=_join, icon="login").classes("w-full sm:w-auto")


def _save_vote(project: str, evaluator: str, option_name: str, scores: dict[str, float]) -> None:
    save_vote(project, evaluator, option_name, scores)
    ui.notify(f"Vote saved for '{option_name}'.", type="positive")


def _save_note(project: str, option_name: str, notes: str) -> None:
    update_notes(option_name, notes.strip(), project=project)
    ui.notify(f"Note saved for '{option_name}'.", type="positive")
    _vote_body.refresh()


def _bad_link() -> None:
    ui.dark_mode().enable()
    with ui.column().classes("items-center justify-center min-h-screen gap-2"):
        ui.label("Invalid or expired link.").classes("text-h5")
        ui.label("Ask the project owner for a fresh voting link.").classes("text-caption")


def _login_page() -> None:
    ui.dark_mode().enable()
    with ui.column().classes(
        "items-center justify-center min-h-screen gap-2 w-full max-w-sm mx-auto px-4"
    ):
        ui.image("/pwa/icon-192.png").classes("w-24")
        ui.markdown("### should-we").classes("mb-2")
        ui.label("Log in as a project owner or test user.").classes("text-caption text-grey-6")
        name_inp = ui.input("Name").classes("w-full")
        pw_inp = ui.input("Password", password=True, password_toggle_button=True).classes("w-full")

        def _try_login():
            role = _login_role(name_inp.value, pw_inp.value)
            if not role:
                if not _admins() and not load_users():
                    ui.notify(
                        "No accounts configured — set SHOULD_WE_ADMINS or create test users.",
                        type="negative",
                    )
                else:
                    ui.notify("Wrong name or password.", type="negative")
                return
            name = (name_inp.value or "").strip()
            app.storage.user["role"] = role
            app.storage.user["name"] = name
            if role == "admin":
                app.storage.user["admin"] = name
            ui.navigate.reload()

        ui.button("Log in", on_click=_try_login, icon="login").classes("w-full")


def _logout() -> None:
    app.storage.user.clear()
    ui.navigate.reload()


def _results_body(project: str, config: ScoringConfig) -> None:
    with ui.header(elevated=True).classes("items-center justify-between px-4 flex-wrap gap-2"):
        ui.label(f"{config.project_name} — results").classes("text-h6")
        with ui.row().classes("items-center gap-2"):
            if _is_user_project(_session_user(), project):
                ui.button(
                    "My project",
                    icon="home",
                    on_click=lambda: ui.navigate.to("/"),
                ).props("outline").classes("min-h-10")
            ui.button(
                "See rankings",
                icon="leaderboard",
                on_click=lambda: ui.navigate.to(f"/?project={project}&tab=rankings"),
            ).props("outline").classes("min-h-10")
    with ui.column().classes("w-full max-w-4xl mx-auto px-4 py-4"):
        _results_list(project, config, readonly=True)


@ui.page("/results/{project}/{token}")
def results_page(project: str, token: str):
    ui.dark_mode().enable()
    try:
        config = load_config(project)
    except SystemExit:
        ui.label("Project not found.").classes("text-h5")
        return
    if not _results_allowed(token, config.join_token or "", _is_admin()):
        _bad_link()
        return
    _results_body(project, config)


@ui.page("/results/{project}")
def results_admin_page(project: str):
    ui.dark_mode().enable()
    try:
        config = load_config(project)
    except SystemExit:
        ui.label("Project not found.").classes("text-h5")
        return
    if not _is_admin():
        _bad_link()
        return
    _results_body(project, config)


@ui.page("/", title="should-we", favicon="/assets/logo.png")
def index():
    if not _is_admin():
        name = None
        try:
            name = app.storage.user.get("name")
        except RuntimeError:
            name = None
        if name:
            _user_home(name)
        else:
            _login_page()
        return
    global _dropdown, _panels, _tab_rankings, _project_key, _config

    ui.dark_mode().enable()
    _init_state()
    try:
        q = ui.context.client.request.query_params
    except Exception:
        q = {}
    projects = list_projects()
    if projects and q.get("project") in projects:
        _project_key = q["project"]
        _config = load_config(_project_key)

    with ui.header(elevated=True).classes("items-center justify-between px-4 flex-wrap gap-2"):
        with ui.row().classes("items-center gap-3 flex-wrap"):
            ui.image("/assets/logo.png").classes("w-9")
            ui.label("should-we").classes("text-h5")
        with ui.row().classes("items-center gap-2 flex-wrap"):
            admin_name = app.storage.user.get("name")
            if admin_name:
                ui.badge("admin", color="positive", outline=True).tooltip(
                    "Logged in as project owner"
                )
                ui.label(admin_name).classes("text-caption")
            ui.button("Logout", on_click=_logout, icon="logout", color="white").props(
                "unelevated"
            ).classes("text-black")
        projects = list_projects()
        if projects:
            with ui.row().classes("items-center gap-2"):
                _dropdown = ui.select(
                    label="Project",
                    options=projects,
                    value=_project_key,
                    on_change=_on_project_change,
                ).classes("w-full sm:w-48")
                with ui.dialog() as delete_dialog, ui.card():
                    delete_label = ui.label().classes("text-h6")
                    ui.label("This cannot be undone.")
                    with ui.row().classes("justify-end gap-2 mt-4 flex-wrap"):
                        ui.button("Cancel", on_click=delete_dialog.close)
                        ui.button(
                            "Delete",
                            on_click=lambda: _do_delete(delete_dialog),
                            color="red",
                        )
                ui.button(
                    icon="delete",
                    on_click=lambda: _open_delete_dialog(delete_dialog, delete_label),
                ).props("round").classes("text-red")

    with ui.column().classes("w-full max-w-4xl mx-auto px-4"):
        with ui.tabs() as tabs:
            tab_setup = ui.tab("Setup")
            tab_rankings = ui.tab("Rankings")
            tab_users = ui.tab("Test users")

        with ui.tab_panels(
            tabs, value=tab_rankings if q.get("tab") == "rankings" else tab_setup
        ) as panels:
            _panels = panels
            _tab_rankings = tab_rankings
            with ui.tab_panel(tab_setup):
                setup_panel()
            with ui.tab_panel(tab_rankings):
                rankings_panel()
            with ui.tab_panel(tab_users):
                test_users_panel()


def run():
    ui.run(
        reload=False,
        host=os.environ.get("SHOULD_WE_HOST", "127.0.0.1"),
        storage_secret=os.environ.get("SHOULD_WE_STORAGE_SECRET"),
        session_middleware_kwargs={"https_only": True},
    )
