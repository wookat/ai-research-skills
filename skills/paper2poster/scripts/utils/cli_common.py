"""Tiny helpers shared by every poster CLI entry point.

Two things that were copy-pasted across ``slack`` / ``polish`` /
``preflight`` / ``verify-final`` / ``render_poster``:

1. ``eprint`` -- print to stderr. Every CLI needs it; there is no reason
   for five byte-identical definitions.
2. ``import_playwright`` -- the lazy Playwright import with a friendly
   install hint. Playwright is only needed by the Chromium-driven
   commands (``slack`` / ``polish`` / ``render_poster``), so it stays a
   function-level import: the pure-static commands (``preflight``) and
   ``--help`` must work without it installed.
"""
from __future__ import annotations

import sys
from typing import Any


def eprint(*args: Any, **kw: Any) -> None:
    """``print`` to stderr."""
    print(*args, file=sys.stderr, **kw)


def import_playwright():
    """Import Playwright's sync API behind a friendly install hint.

    Returns ``(sync_playwright, PWTimeoutError)`` on success, or ``None``
    after printing the install instructions to stderr -- callers turn a
    ``None`` into ``return 2`` (their "environment not set up" exit code).
    """
    try:
        from playwright.sync_api import sync_playwright
        from playwright.sync_api import TimeoutError as PWTimeoutError
    except ImportError:
        eprint("ERROR: playwright not installed. Run:")
        eprint("  python -m pip install playwright")
        eprint("  python -m playwright install chromium")
        return None
    return sync_playwright, PWTimeoutError
