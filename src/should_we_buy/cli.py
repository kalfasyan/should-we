from __future__ import annotations

import argparse
import sys

from .config import (
    Evaluator,
    Feature,
    ScoringConfig,
    _label_to_key,
    delete_project,
    list_projects,
    load_config,
    project_paths,
    save_config,
)
from .scoring import compute_combined
from .storage import find_option, load_options, reprocess_all, save_option


def _parse_score(raw: str, *, default: float = 0.0) -> float:
    raw = raw.strip()
    if raw == "":
        return default
    try:
        return float(raw)
    except ValueError as e:
        raise ValueError(f"Invalid score: {raw!r}") from e


def _add_project_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-p", "--project",
        help="Project to use (auto-detected if only one exists)",
    )


def cmd_new(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    name = input("Option name: ").strip()
    while not name:
        name = input("Option name (cannot be empty): ").strip()

    scores: dict[str, dict[str, float]] = {}
    for ev in config.evaluators:
        print(f"\n--- Scores from {ev.name} (0\u20135, Enter to skip) ---")
        ev_scores: dict[str, float] = {}
        for feat in config.features:
            while True:
                raw = input(f"  {feat.label}: ")
                try:
                    ev_scores[feat.key] = _parse_score(raw, default=0.0)
                    break
                except ValueError as e:
                    print(str(e))
        scores[ev.name] = ev_scores

    option = save_option(name=name, scores=scores, project=args.project)
    print("\nSaved.\n")
    for ev_name, score in option.breakdown.items():
        print(f"{ev_name}:  {score:.3f}")
    print(f"Combined: {compute_combined(option.breakdown):.3f}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    if not args.project:
        projects = list_projects()
        if not projects:
            print("No projects yet. Run: pixi run setup")
            return 0
        print("Projects:")
        for p in projects:
            cfg_path, _ = project_paths(p)
            cfg = load_config(p)
            n_opt = len(load_options(p))
            print(f"  {p}  — \"{cfg.project_name}\" ({n_opt} option(s))")
        print("\nUse --project <name> to list options. E.g.: pixi run list -p home-buying")
        return 0

    options = load_options(args.project)
    if not options:
        print("No saved options yet. Run: python -m should_we_buy new")
        return 0
    for opt in sorted(options, key=lambda x: compute_combined(x.breakdown), reverse=True):
        print(f"{opt.name}  (combined={compute_combined(opt.breakdown):.3f})")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    opt = find_option(args.name, project=args.project)
    if opt is None:
        print(f"Option not found: {args.name!r}")
        return 2
    print(f"Name: {opt.name}")
    for ev_name, score in opt.breakdown.items():
        print(f"{ev_name}:  {score:.3f}")
    print(f"Combined: {compute_combined(opt.breakdown):.3f}")
    return 0


def cmd_reprocess(args: argparse.Namespace) -> int:
    n = reprocess_all(args.project)
    print(f"Reprocessed {n} option(s).")
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    from .ui import run

    run()
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    project = args.project
    if not project:
        print("Usage: python -m should_we_buy delete <project>")
        return 1
    cfg_path, _ = project_paths(project)
    if not cfg_path.exists():
        print(f"Project '{project}' not found.")
        return 1
    confirm = input(f"Delete project '{project}' and all its options? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return 0
    delete_project(project)
    print(f"Deleted project '{project}'.")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    project_name = input("\nWhat are you thinking of buying? (this will be the project name, e.g. 'apartment', 'vacation', 'car'): ").strip()
    while not project_name:
        project_name = input("Let's give it a name (cannot be empty): ").strip()

    project_key = _label_to_key(project_name)
    cfg_path, _ = project_paths(project_key)
    if cfg_path.exists() and not args.force:
        print(f"Project '{project_key}' already exists. Use --force to overwrite.")
        return 1

    raw = input("\nWho's making this decision together? (comma-separated names, e.g. 'Alice, Bob'): ").strip()
    while not raw:
        raw = input("Need at least one person. Names (comma-separated): ").strip()
    evaluator_names = [n.strip() for n in raw.split(",") if n.strip()]

    raw = input("\nWhat are the things you care about when picking one?\n(comma-separated, e.g. 'Price, Location, Parking'): ").strip()
    while not raw:
        raw = input("Need at least one feature. Things you care about (comma-separated): ").strip()
    feature_labels = [f.strip() for f in raw.split(",") if f.strip()]
    features = [Feature(key=_label_to_key(label), label=label) for label in feature_labels]

    print("\nNow, how much does each feature matter to each of you?")
    print("  0 = don't care  |  3 = important  |  5 = dealbreaker\n")
    evaluators: list[Evaluator] = []
    for ev_name in evaluator_names:
        print(f"How much do these matter to you, {ev_name}?")
        weights: dict[str, int] = {}
        for feat in features:
            val = input(f"  {feat.label} (0\u20135): ").strip()
            weights[feat.key] = int(val) if val else 0
        evaluators.append(Evaluator(name=ev_name, weights=weights))

    config = ScoringConfig(project_name=project_name, features=features, evaluators=evaluators)
    save_config(config, project=project_key)
    print(f"\nAll set! Config saved to data/{project_key}/.")
    print(f"  {len(features)} feature(s), {len(evaluators)} people. Ready to `pixi run new`.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="should_we_buy", description="Weighted ranking CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="Interactively enter a new option and compute score")
    _add_project_arg(p_new)
    p_new.set_defaults(func=cmd_new)

    p_list = sub.add_parser("list", help="List projects (or options with --project)")
    _add_project_arg(p_list)
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show one saved option")
    p_show.add_argument("name", help="Option name")
    _add_project_arg(p_show)
    p_show.set_defaults(func=cmd_show)

    p_setup = sub.add_parser("setup", help="Interactively create a new scoring project")
    p_setup.add_argument("--force", action="store_true", help="Overwrite existing project")
    p_setup.set_defaults(func=cmd_setup)

    p_re = sub.add_parser(
        "reprocess",
        help="Recompute scores for all options from the JSON (after manual edits)",
    )
    _add_project_arg(p_re)
    p_re.set_defaults(func=cmd_reprocess)

    p_ui = sub.add_parser("ui", help="Launch the NiceGUI web app")
    p_ui.set_defaults(func=cmd_ui)

    p_delete = sub.add_parser("delete", help="Delete a project and all its options")
    p_delete.add_argument("project", help="Project key to delete")
    p_delete.set_defaults(func=cmd_delete)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(argv)
    return int(args.func(args))
