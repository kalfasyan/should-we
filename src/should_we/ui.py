from __future__ import annotations

import csv
import html
import io
import json
import os
from pathlib import Path

from nicegui import app, ui

from .config import (
    Feature,
    ScoringConfig,
    _label_to_key,
    add_evaluator,
    delete_project,
    get_join_token,
    get_or_create_token,
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

_assets = Path(__file__).resolve().parent.parent.parent / "docs" / "assets"
if _assets.is_dir():
    app.add_static_files("/assets", str(_assets))

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


def _option_delete_dialog(name: str) -> ui.dialog:
    with ui.dialog() as dialog, ui.card():
        ui.label(f"Delete option '{name}'?").classes("text-h6")
        ui.label("This cannot be undone.")
        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close)
            ui.button(
                "Delete",
                on_click=lambda: _do_delete_option(dialog, name),
                color="red",
            )
    return dialog


def _do_delete_option(dialog, name: str) -> None:
    if not _project_key:
        return
    delete_option(name, _project_key)
    dialog.close()
    ui.notify(f"Deleted option '{name}'.", type="warning")
    rankings_panel.refresh()


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
        with ui.row().classes("w-full items-center gap-2"):
            ui.input(value=join_url).classes("flex-grow").props("readonly dense")
            ui.button(
                "Copy join link",
                on_click=lambda: _copy_text(join_url, "Join link copied"),
                icon="copy",
            ).props("outline")

        if not config.evaluators:
            ui.label("No one has joined yet — send them the link above.").classes(
                "text-caption text-grey-6"
            )
        else:
            ui.markdown("#### 👥 Joined people").classes("mb-1")
            for ev in config.evaluators:
                url = _abs_url(f"vote/{project}/{get_or_create_token(project, ev.name)}")
                with ui.row().classes("w-full items-center gap-2"):
                    ui.label(ev.name).classes("w-28")
                    ui.input(value=url).classes("flex-grow").props("readonly dense")
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


@ui.refreshable
def _vote_status(project: str, config: ScoringConfig) -> None:
    options = load_options(project)
    if not options:
        return
    votes = load_votes(project)
    with ui.row().classes("gap-4 mb-2"):
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

    if readonly:
        return

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
                        ui.label(f"{chip} {ev.name}").classes("w-32 text-caption")
                        if score is None:
                            ui.label("not voted").classes("text-grey-6 text-caption")
                        else:
                            _score_bar(score)
                            ui.label(f"{score:.3f}").classes("w-14 text-right")
                if not readonly:
                    del_dialog = _option_delete_dialog(opt.name)
                    ui.button(icon="delete", on_click=del_dialog.open).props(
                        "flat round size=sm"
                    ).classes("text-red").tooltip("Delete option")

    if not readonly:
        with ui.row().classes("gap-2 items-center"):
            ui.button(
                "Copy results link",
                on_click=lambda: _copy_text(_abs_url(f"results/{project}"), "Results link copied"),
                icon="link",
            ).props("outline")
            ui.button("Reprocess", on_click=_reprocess, icon="refresh")
            ui.button(
                "Export CSV",
                on_click=lambda: ui.download(
                    _csv_content(project, sorted_opts), f"{project}-rankings.csv"
                ),
                icon="download",
            )
        # ponytail: poll only the tiny status line, never the list itself —
        # rebuilding expansions every few seconds makes them unclickable
        ui.timer(5.0, lambda: _vote_status.refresh())


def _heatmap_tooltip(names, ev_names, opts) -> str:
    notes = {o.name: html.escape(o.notes) for o in opts if o.notes}
    return (
        "(function(params){"
        f"var names={json.dumps(names)};var evs={json.dumps(ev_names)};"
        f"var notes={json.dumps(notes)};"
        "var p=params[0].data;var opt=names[p[0]];var person=evs[p[1]];"
        "var note=notes[opt]||'';"
        "return opt+'<br>'+person+': '+p[2]+(note?'<br>'+note:'');})"
    )


def _charts_body(sorted_opts, config: ScoringConfig) -> None:
    names = [o.name for o in sorted_opts]
    with ui.column().classes("w-full gap-2 mb-4"):
        ui.echart(
            {
                "tooltip": {},
                "grid": {"left": 40, "right": 16, "top": 30, "bottom": 60},
                "xAxis": {"type": "category", "data": names, "axisLabel": {"rotate": 30}},
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
        heat = []
        for oi, opt in enumerate(sorted_opts):
            for ei, ev in enumerate(config.evaluators):
                v = opt.breakdown.get(ev.name)
                if v is not None:
                    heat.append([oi, ei, round(v, 3)])
        ui.echart(
            {
                "tooltip": {"formatter": _heatmap_tooltip(names, ev_names, sorted_opts)},
                "grid": {"left": 80, "right": 16, "top": 30, "bottom": 80},
                "xAxis": {"type": "category", "data": names, "axisLabel": {"rotate": 30}},
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


def _reprocess() -> None:
    reprocess_all(_project_key)
    rankings_panel.refresh()


def _regenerate(evaluator: str, project: str) -> None:
    regenerate_token(project, evaluator)
    ui.notify(f"New link created for {evaluator}.")
    rankings_panel.refresh()


def _csv_content(project: str, options) -> str:
    ev_names = [ev.name for ev in _config.evaluators] if _config else []
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

    project_name = ui.input("Project name").classes("w-64")
    feature_labels = ui.textarea("Feature labels (one per line)").classes("w-64")

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
            ).classes("w-56")

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
            ScoringConfig(project_name=pname, features=features, evaluators=[]), project=pkey
        )
        ui.notify(f"Project '{pname}' saved!", type="positive")
        _set_project(pkey)
        join_url_inp.value = _abs_url(f"join/{pkey}/{get_join_token(pkey)}")
        ready_dialog.open()

    with ui.dialog() as ready_dialog, ui.card():
        ui.markdown("### 🎉 Project ready!").classes("mb-1")
        ui.label("Share the join link with your group:")
        join_url_inp = ui.input().classes("w-full").props("readonly")
        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button(
                "Copy",
                on_click=lambda: _copy_text(join_url_inp.value, "Join link copied"),
                icon="copy",
            ).props("outline")
            ui.button("Go to Rankings", on_click=lambda: _go_rankings(ready_dialog), icon="launch")

    ui.button("Save Config", on_click=_save_config, icon="save")


def _go_rankings(dialog) -> None:
    dialog.close()
    if _panels is not None and _tab_rankings is not None:
        _panels.value = _tab_rankings


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

    with ui.header(elevated=True).classes("items-center justify-between px-4"):
        with ui.row().classes("items-center gap-3"):
            ui.label(f"{config.project_name} — vote").classes("text-h6")
            ui.label(f"voting as {evaluator}").classes("text-caption")
        ui.button(
            "See current results",
            on_click=lambda: ui.navigate.to(f"/results/{project}"),
        ).props("outline")

    with ui.column().classes("w-full max-w-3xl mx-auto px-4 py-4"):
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
            ui.markdown(f"### ⚖️ How much does each feature matter to you, {evaluator}?").classes(
                "mb-0"
            )
        ui.label("0 = don't care  |  3 = important  |  5 = dealbreaker").classes("text-caption")
        sliders: dict[str, ui.slider] = {}
        for feat in config.features:
            with ui.row().classes("w-full items-center"):
                ui.label(feat.label).classes("w-32")
                s = (
                    ui.slider(min=0, max=5, step=1, value=ev_config.weights.get(feat.key, 3))
                    .props("label-always")
                    .classes("flex-grow")
                )
                sliders[feat.key] = s

        def _save_weights():
            set_weights(project, evaluator, {k: int(v.value) for k, v in sliders.items()})
            ui.notify("Weights saved.", type="positive")
            _vote_body.refresh()

        ui.button("Save my weights", on_click=_save_weights, icon="save")

    if not ev_config.weights:
        ui.label("Save your weights above first — without them your votes don't count.").classes(
            "text-warning mb-2"
        )

    with ui.card().classes("w-full mb-4"):
        ui.markdown("### ➕ Add an option").classes("mb-2")
        ui.label("Something to compare? Add it — everyone else can vote on it too.").classes(
            "text-caption"
        )
        new_name = ui.input("Option name").classes("w-64")
        new_notes = ui.input("Link or note (optional)").classes("w-64")

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
            ui.notify(f"'{name}' added — now rate it below.", type="positive")
            new_name.value = ""
            new_notes.value = ""
            _vote_body.refresh()

        ui.button("Add option", on_click=_add_option, icon="add")

    ui.markdown("Rate each option 0–5 per feature, then save your vote.").classes("mb-2")

    if not options:
        with ui.card().classes("w-full"):
            ui.label("No options yet — add the first one above 👆").classes("text-grey-6")
        return

    for opt in options:
        with ui.card().classes("w-full mb-4"):
            ui.label(opt.name).classes("text-h6")
            if opt.name in votes.get(evaluator, {}):
                ui.label("✓ voted").classes("text-positive text-caption")
            ev_inps: dict[str, ui.slider] = {}
            with ui.column().classes("w-full gap-2"):
                for feat in config.features:
                    with ui.row().classes("w-full items-center"):
                        ui.label(feat.label).classes("w-32")
                        s = (
                            ui.slider(
                                min=0,
                                max=5,
                                step=0.5,
                                value=float(opt.scores.get(evaluator, {}).get(feat.key, 0.0)),
                            )
                            .props("label-always")
                            .classes("flex-grow")
                        )
                        ev_inps[feat.key] = s
            with ui.row().classes("w-full items-center gap-2 mt-2"):
                note_inp = (
                    ui.input(value=opt.notes, placeholder="Link or note")
                    .props("dense")
                    .classes("flex-grow")
                )
                ui.button(
                    "Save note",
                    icon="link",
                    on_click=lambda n=opt.name, inp=note_inp: _save_note(project, n, inp.value),
                ).props("outline dense")
                ui.button(
                    "Save my vote",
                    icon="save",
                    on_click=lambda n=opt.name, ev=ev_inps: _save_vote(
                        project, evaluator, n, {k: v.value for k, v in ev.items()}
                    ),
                )


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

    with ui.header(elevated=True).classes("items-center justify-between px-4"):
        ui.label(f"Join {config.project_name}").classes("text-h6")

    with ui.column().classes(
        "items-center justify-center h-screen gap-2 w-full max-w-2xl mx-auto px-4"
    ):
        ui.markdown(
            "Pick a name — then you'll set your weights and can vote on every option."
        ).classes("text-center")
        name_inp = ui.input("Your name (e.g. Alice)").classes("w-64")

        def _join():
            name = name_inp.value.strip()
            if not name:
                ui.notify("Enter a name.", type="negative")
                return
            add_evaluator(project, name)
            token2 = get_or_create_token(project, name)
            ui.navigate.to(f"/vote/{project}/{token2}")

        ui.button("Join and vote", on_click=_join, icon="login")


def _save_vote(project: str, evaluator: str, option_name: str, scores: dict[str, float]) -> None:
    save_vote(project, evaluator, option_name, scores)
    ui.notify(f"Vote saved for '{option_name}'.", type="positive")


def _save_note(project: str, option_name: str, notes: str) -> None:
    update_notes(option_name, notes.strip(), project=project)
    ui.notify(f"Note saved for '{option_name}'.", type="positive")
    _vote_body.refresh()


def _bad_link() -> None:
    ui.dark_mode().enable()
    with ui.column().classes("items-center justify-center h-screen gap-2"):
        ui.label("Invalid or expired link.").classes("text-h5")
        ui.label("Ask the project owner for a fresh voting link.").classes("text-caption")


@ui.page("/results/{project}")
def results_page(project: str):
    ui.dark_mode().enable()
    try:
        config = load_config(project)
    except SystemExit:
        ui.label("Project not found.").classes("text-h5")
        return
    with ui.header(elevated=True).classes("items-center justify-between px-4"):
        ui.label(f"{config.project_name} — results").classes("text-h6")
    with ui.column().classes("w-full max-w-4xl mx-auto px-4 py-4"):
        _results_list(project, config, readonly=True)


@ui.page("/", title="should-we", favicon="/assets/logo.png")
def index():
    global _dropdown, _panels, _tab_rankings

    ui.dark_mode().enable()
    _init_state()

    with ui.header(elevated=True).classes("items-center justify-between px-4"):
        with ui.row().classes("items-center gap-3"):
            ui.image("/assets/logo.png").classes("w-9")
            ui.label("should-we").classes("text-h5")
        projects = list_projects()
        if projects:
            with ui.row().classes("items-center gap-2"):
                _dropdown = ui.select(
                    label="Project",
                    options=projects,
                    value=_project_key,
                    on_change=_on_project_change,
                ).classes("w-48")
                with ui.dialog() as delete_dialog, ui.card():
                    delete_label = ui.label().classes("text-h6")
                    ui.label("This cannot be undone.")
                    with ui.row().classes("justify-end gap-2 mt-4"):
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

        with ui.tab_panels(tabs, value=tab_setup) as panels:
            _panels = panels
            _tab_rankings = tab_rankings
            with ui.tab_panel(tab_setup):
                setup_panel()
            with ui.tab_panel(tab_rankings):
                rankings_panel()


def run():
    ui.run(reload=False, host=os.environ.get("SHOULD_WE_HOST", "127.0.0.1"))
