from __future__ import annotations

from nicegui import ui

from .config import (
    Evaluator,
    Feature,
    ScoringConfig,
    _label_to_key,
    delete_project,
    list_projects,
    load_config,
    save_config,
)
from .scoring import compute_combined
from .storage import load_options, reprocess_all, save_option


_project_key: str | None = None
_config: ScoringConfig | None = None
_dropdown: ui.select | None = None


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
    score_new_panel.refresh()
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
        score_new_panel.refresh()
        setup_panel.refresh()


@ui.refreshable
def rankings_panel():
    if not _config or not _project_key:
        ui.label("No project selected. Use the dropdown in the top bar.")
        return

    options = load_options(_project_key)
    if not options:
        with ui.card().classes("w-full"):
            with ui.column().classes("gap-1"):
                ui.markdown("### No options scored yet").classes("mb-1")
                ui.label("Go to the Score New tab to rate your first option.")
                ui.label("Need to set up a project first? Head to the Setup tab.")
        return

    ui.markdown(
        "Options ranked by combined score (average of all evaluators). "
        "Click any option to see each person's individual score. "
        "Use **Reprocess** after editing the raw JSON by hand."
    ).classes("mb-4")

    sorted_opts = sorted(options, key=lambda o: compute_combined(o.breakdown), reverse=True)

    with ui.column().classes("w-full gap-2"):
        for i, opt in enumerate(sorted_opts):
            combined = compute_combined(opt.breakdown)
            icon = ["military_tech", "workspace_premium", "star"][i] if i < 3 else None
            with ui.expansion(f"#{i + 1}  {opt.name}  —  {combined:.3f}", icon=icon).classes("w-full"):
                for ev_name, score in opt.breakdown.items():
                    ui.label(f"{ev_name}:  {score:.3f}")

    def _on_reprocess():
        reprocess_all(_project_key)
        rankings_panel.refresh()

    ui.button("Reprocess", on_click=_on_reprocess, icon="refresh")


@ui.refreshable
def score_new_panel():
    if not _config or not _project_key:
        ui.label("No project selected. Create one on the Setup tab or pick one from the top bar dropdown.")
        return

    with ui.card().classes("w-full mb-4"):
        with ui.column().classes("gap-1"):
            ui.markdown("### How to score an option").classes("mb-2")
            ui.label("1. Make sure the right project is selected in the top bar dropdown.")
            ui.label("2. Give your option a name.")
            ui.label("3. For each person, rate every feature (0–5).")
            ui.label("4. Click Save Option — see the results on the Rankings tab.")

    option_name = ui.input("Option name").classes("w-64")
    evaluator_inputs: dict[str, dict[str, ui.number]] = {}

    with ui.column().classes("w-full gap-4"):
        for ev in _config.evaluators:
            with ui.card().classes("w-full"):
                ui.label(ev.name).classes("text-h6")
                ev_scores: dict[str, ui.number] = {}
                with ui.row().classes("gap-4"):
                    for feat in _config.features:
                        with ui.column():
                            ui.label(feat.label).classes("text-caption")
                            inp = ui.number(value=0, min=0, max=5, step=0.5).classes("w-20")
                            ev_scores[feat.key] = inp
                evaluator_inputs[ev.name] = ev_scores

    def _submit():
        name = option_name.value.strip()
        if not name:
            ui.notify("Option name required.", type="negative")
            return
        scores: dict[str, dict[str, float]] = {}
        for ev_name, ev_inps in evaluator_inputs.items():
            scores[ev_name] = {k: v.value for k, v in ev_inps.items()}
        save_option(name=name, scores=scores, project=_project_key)
        ui.notify(f"Saved '{name}'!", type="positive")
        option_name.value = ""
        for ev_inps in evaluator_inputs.values():
            for inp in ev_inps.values():
                inp.value = 0
        rankings_panel.refresh()

    ui.button("Save Option", on_click=_submit, icon="save")


@ui.refreshable
def setup_panel():
    with ui.card().classes("w-full mb-4"):
        with ui.column().classes("gap-1"):
            ui.markdown("### How to set up a project").classes("mb-2")
            ui.label("1. Enter a project name, the names of the people deciding, and the features you care about.")
            ui.label("2. Click Generate weight grid to set how much each feature matters to each person (0–5).")
            ui.label("3. Click Save Config — the new project auto-selects in the top bar.")
            ui.label("4. Switch to the Score New tab to start rating options.")

    project_name = ui.input("Project name").classes("w-64")
    evaluator_names = ui.textarea("Evaluator names (one per line)").classes("w-64")
    feature_labels = ui.textarea("Feature labels (one per line)").classes("w-64")

    weight_grid_container = ui.column()
    evaluators_data: list[dict] = []
    features_data: list[Feature] = []

    def _generate_weight_grid():
        weight_grid_container.clear()
        evaluators_data.clear()
        features_data.clear()

        ev_names = [n.strip() for n in evaluator_names.value.strip().split("\n") if n.strip()]
        feat_labels = [l.strip() for l in feature_labels.value.strip().split("\n") if l.strip()]

        if not ev_names or not feat_labels:
            ui.notify("Enter at least one evaluator and one feature.", type="warning")
            return

        for label in feat_labels:
            features_data.append(Feature(key=_label_to_key(label), label=label))

        with weight_grid_container:
            ui.label(
                "Weight importance: 0 = don't care  |  3 = important  |  5 = dealbreaker"
            ).classes("text-caption mb-2")
            for ev_name in ev_names:
                with ui.card().classes("w-full"):
                    ui.label(ev_name).classes("text-h6")
                    weights: dict[str, ui.slider] = {}
                    for feat in features_data:
                        with ui.row().classes("w-full items-center"):
                            ui.label(feat.label).classes("w-32 text-caption")
                            s = (
                                ui.slider(min=0, max=5, step=1, value=3)
                                .props("label-always")
                                .classes("flex-grow")
                            )
                            weights[feat.key] = s
                    evaluators_data.append({"name": ev_name, "weights": weights})

    ui.button("Generate weight grid", on_click=_generate_weight_grid, icon="build")

    def _save_config():
        pname = project_name.value.strip()
        if not pname:
            ui.notify("Project name required.", type="negative")
            return
        if not evaluators_data or not features_data:
            ui.notify("Generate the weight grid first.", type="warning")
            return
        pkey = _label_to_key(pname)
        evaluators = [
            Evaluator(name=ed["name"], weights={k: int(v.value) for k, v in ed["weights"].items()})
            for ed in evaluators_data
        ]
        config = ScoringConfig(
            project_name=pname,
            features=list(features_data),
            evaluators=evaluators,
        )
        save_config(config, project=pkey)
        ui.notify(f"Project '{pname}' saved!", type="positive")
        _set_project(pkey)

    ui.button("Save Config", on_click=_save_config, icon="save")


@ui.page("/")
def index():
    global _dropdown

    ui.dark_mode().enable()
    _init_state()

    with ui.header(elevated=True).classes("items-center justify-between px-4"):
        ui.label("should-we-buy").classes("text-h5")
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
                        ui.button("Delete", on_click=lambda: _do_delete(delete_dialog), color="red")
                ui.button(icon="delete", on_click=lambda: _open_delete_dialog(delete_dialog, delete_label)).props("round").classes("text-red")

    with ui.tabs() as tabs:
        tab_setup = ui.tab("Setup")
        tab_score = ui.tab("Score New")
        tab_rankings = ui.tab("Rankings")

    with ui.tab_panels(tabs, value=tab_setup):
        with ui.tab_panel(tab_setup):
            setup_panel()
        with ui.tab_panel(tab_score):
            score_new_panel()
        with ui.tab_panel(tab_rankings):
            rankings_panel()


def run():
    ui.run(reload=False)
