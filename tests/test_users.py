from __future__ import annotations

import json
from dataclasses import replace

from should_we.config import (
    Feature,
    ScoringConfig,
    load_config,
    project_paths,
    save_config,
)
from should_we.ui import _login_role
from should_we.users import create_user, delete_user, load_users, verify_user


def _cfg() -> ScoringConfig:
    return ScoringConfig(
        project_name="t",
        features=[Feature(key="a", label="A")],
        evaluators=[],
    )


def test_create_verify_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    password, error = create_user("Alice")
    assert error is None
    assert password
    assert verify_user("Alice", password)
    assert not verify_user("Alice", "wrong-password")
    assert not verify_user("Eve", password)


def test_wrong_password_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    password, _ = create_user("Alice")
    assert not verify_user("Alice", f"x{password}")
    assert not verify_user("Alice", None)


def test_duplicate_name_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    create_user("Alice")
    _, error = create_user("Alice")
    assert error is not None


def test_key_collision_with_existing_project_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_cfg(), project="alice")
    _, error = create_user("Alice")
    assert error is not None


def test_key_collision_with_other_user_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    create_user("Alice Smith")
    _, error = create_user("alice_smith")
    assert error is not None


def test_delete_user_removes(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    create_user("Alice")
    delete_user("Alice")
    assert "Alice" not in load_users()
    assert not verify_user("Alice", "anything")


def test_users_file_roundtrip_and_600_perms(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    create_user("Alice")
    create_user("Bob")
    assert set(load_users()) == {"Alice", "Bob"}
    assert (tmp_path / ".users.json").stat().st_mode & 0o777 == 0o600


def test_config_owner_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(replace(_cfg(), owner="Alice"), project="alice")
    assert load_config("alice").owner == "Alice"


def test_old_config_without_owner_loads(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    save_config(_cfg(), project="alice")
    cfg_path, _ = project_paths("alice")
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    del raw["owner"]
    cfg_path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_config("alice").owner is None


def test_login_routing_prefers_admin_over_user(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOULD_WE_ADMINS", '{"Yannis": "adminpw"}')
    monkeypatch.setenv("SHOULD_WE_DATA", str(tmp_path))
    user_pw, _ = create_user("Yannis")
    assert _login_role("Yannis", "adminpw") == "admin"
    assert _login_role("Yannis", user_pw) == "user"
    assert _login_role("Yannis", "wrong") is None
    assert _login_role("Nobody", "x") is None
