from __future__ import annotations

from should_we.ui import _admins, _check_login, _results_allowed


def test_admins_parses_env_json(monkeypatch):
    monkeypatch.setenv("SHOULD_WE_ADMINS", '{"Alice": "pw1", "Bob": "pw2"}')
    assert _admins() == {"Alice": "pw1", "Bob": "pw2"}


def test_admins_empty_when_unset(monkeypatch):
    monkeypatch.delenv("SHOULD_WE_ADMINS", raising=False)
    assert _admins() == {}


def test_admins_empty_on_bad_json(monkeypatch):
    monkeypatch.setenv("SHOULD_WE_ADMINS", "not-json")
    assert _admins() == {}


def test_check_login(monkeypatch):
    monkeypatch.setenv("SHOULD_WE_ADMINS", '{"Alice": "pw1"}')
    assert _check_login("Alice", "pw1")
    assert not _check_login("Alice", "wrong")
    assert not _check_login("Eve", "pw1")
    assert not _check_login("Alice", "")


def test_check_login_empty_inputs_do_not_crash(monkeypatch):
    monkeypatch.setenv("SHOULD_WE_ADMINS", '{"Alice": "pw1"}')
    assert not _check_login(None, None)
    assert not _check_login("Alice", None)
    assert not _check_login(None, "pw1")


def test_results_allowed():
    assert _results_allowed("tok", "tok", is_admin=False)
    assert not _results_allowed("bad", "tok", is_admin=False)
    assert _results_allowed("", "tok", is_admin=True)
    assert not _results_allowed("", "", is_admin=False)
