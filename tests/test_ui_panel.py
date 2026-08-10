from __future__ import annotations

import pytest
from nicegui import ui

pytestmark = pytest.mark.nicegui_main_file("tests/_panel_main.py")


@pytest.mark.anyio
async def test_create_user_with_empty_name_shows_error(user):
    await user.open("/panel")
    user.find("Create user").click()
    await user.should_see("Name required.")
    await user.should_not_see("Test user created")


@pytest.mark.anyio
async def test_create_user_shows_password_dialog_once(user):
    await user.open("/panel")
    user.find(ui.input).type("Alice")
    user.find("Create user").click()
    await user.should_see("Test user created", retries=10)
    with user:
        valued = [e for e in user.find(ui.input).elements if e.value]
        assert len(valued) == 1, "expected exactly the password input to have a value"
        assert len(valued[0].value) == 16, "expected a 16-char token_urlsafe password"
    await user.should_see("Alice")
