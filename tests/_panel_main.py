import os
import tempfile

from nicegui import ui

os.environ["SHOULD_WE_DATA"] = tempfile.mkdtemp(prefix="should-we-panel-test-")

from should_we.ui import test_users_panel  # noqa: E402


@ui.page("/panel")
def root():
    test_users_panel()


ui.run(storage_secret="x")
