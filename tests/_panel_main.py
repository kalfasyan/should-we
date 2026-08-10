import os
import sys
import tempfile

os.environ["SHOULD_WE_DATA"] = tempfile.mkdtemp(prefix="should-we-panel-test-")

sys.modules.pop("should_we", None)
sys.modules.pop("should_we.ui", None)

from nicegui import ui  # noqa: E402

import should_we.ui  # noqa: F401,E402  (registers all pages)


@ui.page("/panel")
def root():
    from should_we.ui import test_users_panel

    test_users_panel()


ui.run(storage_secret="x")
