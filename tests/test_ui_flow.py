from __future__ import annotations

import asyncio

import pytest
from nicegui import ui

pytestmark = pytest.mark.nicegui_main_file("tests/_app_main.py")


async def _login(user, name, password):
    await user.open("/")
    await user.should_see("Log in as a project owner or test user.")
    with user:
        inputs = sorted(user.find(ui.input).elements, key=lambda e: e.id)
        inputs[0].value = name
        inputs[1].value = password
    user.find(kind=ui.button, content="Log in").click()
    await asyncio.sleep(0.4)


@pytest.mark.anyio
async def test_test_user_full_flow(user):
    # admin creates test user Alice
    await _login(user, "yannis", "dev")
    await user.should_see("Test users")
    user.find("Test users").click()
    await user.should_see("Create user")
    with user:
        name_input = max(user.find(ui.input).elements, key=lambda e: e.id)
        name_input.value = "Alice"
    user.find("Create user").click()
    await asyncio.sleep(0.4)
    with user:
        pw_inputs = [e for e in user.find(ui.input).elements if len(e.value or "") == 16]
        assert len(pw_inputs) == 1, "expected the credentials dialog password input"
        alice_pw = pw_inputs[0].value
    user.find("Done").click()
    await asyncio.sleep(0.4)
    await user.should_see("Alice")

    # admin logs out, test user logs in
    user.find("Logout").click()
    await asyncio.sleep(0.4)
    await _login(user, "Alice", alice_pw)
    await user.should_see("Create your project")
    with user:
        next(iter(user.find(ui.textarea).elements)).value = "Price\nLocation"
    user.find("Create project").click()
    await asyncio.sleep(0.4)
    await user.should_see("Vote & add options")

    # test user opens their voting link, adds an option and votes
    user.find("Vote & add options").click()
    await asyncio.sleep(0.4)
    await user.should_see("Add an option")
    with user:
        inputs = sorted(user.find(ui.input).elements, key=lambda e: e.id)
        inputs[0].value = "Cafe A"
    user.find("Add option").click()
    await asyncio.sleep(0.4)
    await user.should_see("Cafe A")
    user.find("Save my vote").click()
    await asyncio.sleep(0.4)

    # a test user sees an obvious way back to their project
    await user.should_see("My project")
    await user.should_not_see("See rankings")
    user.find("My project").click()
    await asyncio.sleep(0.4)
    await user.should_see("Vote & add options")

    # ...and can go back to voting to add more options
    user.find("Vote & add options").click()
    await asyncio.sleep(0.4)
    await user.should_see("Add an option")
    with user:
        inputs = sorted(user.find(ui.input).elements, key=lambda e: e.id)
        inputs[0].value = "Cafe B"
    user.find("Add option").click()
    await asyncio.sleep(0.4)
    await user.should_see("Cafe B")
