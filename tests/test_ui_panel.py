from __future__ import annotations

import asyncio

import pytest
from nicegui import ui

pytestmark = pytest.mark.nicegui_main_file("tests/_panel_main.py")


def _open_dialogs(user):
    with user:
        return [d for d in user.find(ui.dialog).elements if d.value]


@pytest.mark.anyio
async def test_create_user_with_empty_name_shows_error(user):
    await user.open("/panel")
    user.find("Create user").click()
    await user.should_see("Name required.")
    assert not _open_dialogs(user)


@pytest.mark.anyio
async def test_create_user_shows_password_dialog_until_done(user):
    await user.open("/panel")
    user.find(ui.input).type("Alice")
    user.find("Create user").click()
    await asyncio.sleep(0.5)
    assert _open_dialogs(user), "credentials dialog should be open"
    with user:
        valued = [e for e in user.find(ui.input).elements if e.value]
        assert len(valued) == 1, "expected exactly the password input to have a value"
        assert len(valued[0].value) == 16, "expected a 16-char token_urlsafe password"
    user.find("Done").click()
    await asyncio.sleep(0.3)
    assert not _open_dialogs(user), "credentials dialog should be closed after Done"
    await user.should_see("Alice")
