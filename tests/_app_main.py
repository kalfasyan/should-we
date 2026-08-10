import os
import sys
import tempfile

os.environ["SHOULD_WE_ADMINS"] = '{"yannis": "dev"}'
os.environ["SHOULD_WE_STORAGE_SECRET"] = "test-secret"
os.environ["SHOULD_WE_DATA"] = tempfile.mkdtemp(prefix="should-we-app-test-")

# the nicegui test harness removes page routes between tests; force a fresh
# import so the pages get re-registered even if another test imported the
# module earlier (collection-time imports cache it in sys.modules)
sys.modules.pop("should_we", None)
sys.modules.pop("should_we.ui", None)

from nicegui import ui  # noqa: E402

import should_we.ui  # noqa: F401,E402  (registers all pages)

ui.run(storage_secret="test-secret", reload=False, session_middleware_kwargs={"https_only": False})
