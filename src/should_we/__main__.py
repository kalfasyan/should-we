from __future__ import annotations

import sys

from should_we.cli import main

if len(sys.argv) > 1:
    raise SystemExit(main())
