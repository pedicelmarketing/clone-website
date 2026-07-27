"""Shared secret resolution for the web-designer scripts.

Goal: let the agent run its own model calls without requiring the operator
to have ``MINIMAX_API_KEY`` exported in the shell. Resolved in order:

  1. ``os.environ["MINIMAX_API_KEY"]``  (already exported — wins)
  2. ``~/.hermes/profiles/site-cloner/.env``  (operator-managed, gitignored)
  3. ``$HERMES_PROFILE_DIR/.env``  (when the running profile is named,
     so the helper works under any Hermes profile, not just ``site-cloner``)

The key is NEVER printed, logged, echoed, written to disk, or returned in
an error message. The error only names the *files* that were checked.

Helpers
-------
``get_minimax_key()`` -> str | None
    Resolves and returns the key, or ``None`` if not found anywhere.
    Side effect: also exports the key into ``os.environ`` so downstream
    ``os.environ.get`` calls (in vendored libraries, in child processes
    the scripts may spawn) see the same value.

``require_minimax_key(context: str = "operation")`` -> str
    Same as above but raises ``SystemExit(2)`` with a clear, value-free
    message naming every file that was checked.

``_checked_paths_for_error()`` -> list[str]
    Internal — the list of files inspected, for the error message.

Format
------
``.env`` files use the standard ``KEY=VALUE`` form. Lines starting with ``#``
are comments; blank lines are ignored. Values may be optionally quoted with
single or double quotes, which are stripped. No shell expansion, no
multi-line values. This intentionally does NOT use ``dotenv`` from PyPI —
we want stdlib only and a zero-dependency contract.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional


# --- constants --------------------------------------------------------------

#: Env var name used by the vision API in design_pass.py and critique_pass.py.
ENV_VAR = "MINIMAX_API_KEY"

#: Default profile directory checked when ``HERMES_PROFILE_DIR`` is unset.
#: Mirrors the cross-profile layout used by Hermes itself. Built with an
#: absolute Path so we never accidentally expand ``~`` against a relative
#: ``HOME`` (which is what bit the first version of this helper).
_DEFAULT_PROFILE_DIR = Path("/home/openclaw/.hermes/profiles/site-cloner")


# --- internals --------------------------------------------------------------

def _parse_env_file(path: Path) -> Optional[str]:
    """Return the value for ``ENV_VAR`` in ``path`` or ``None``.

    Naive, intentionally simple parser — no shell semantics, no multi-line,
    no escapes beyond leading/trailing quote stripping. Comments (``#``) and
    blank lines are skipped.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        return None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() != ENV_VAR:
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        return value  # first match wins
    return None


def _checked_paths_for_error() -> List[Path]:
    """Return the list of .env files the resolver will check, in order.

    Order (first hit wins):
      1. ``$HERMES_PROFILE_DIR/.env`` if ``HERMES_PROFILE_DIR`` is set
         (the active Hermes profile directory — works for any profile).
      2. The default ``/home/openclaw/.hermes/profiles/site-cloner/.env``
         (always checked; on this host it carries the key).

    Both are kept in the list, even when ``HERMES_PROFILE_DIR`` matches the
    default, so the error message in :func:`require_minimax_key` is
    predictable.
    """
    paths: List[Path] = [_DEFAULT_PROFILE_DIR / ".env"]
    profile_dir = os.environ.get("HERMES_PROFILE_DIR")
    if profile_dir:
        candidate = Path(profile_dir).expanduser() / ".env"
        if candidate not in paths:
            paths.insert(0, candidate)
    return paths


# --- public API -------------------------------------------------------------

def get_minimax_key() -> Optional[str]:
    """Return the resolved ``MINIMAX_API_KEY`` or ``None``.

    Resolution order (first hit wins):

    1. ``os.environ[ENV_VAR]`` — already exported in the shell
    2. ``~/.hermes/profiles/site-cloner/.env`` — operator-managed
    3. ``$HERMES_PROFILE_DIR/.env`` — profile-aware fallback

    On success, the value is also exported into ``os.environ`` so child
    processes and ``os.environ.get`` callers see it consistently.
    """
    existing = os.environ.get(ENV_VAR)
    if existing:
        return existing

    for path in _checked_paths_for_error():
        value = _parse_env_file(path)
        if value:
            # Side effect: make the key visible to os.environ.get and to
            # child processes spawned by these scripts.
            os.environ[ENV_VAR] = value
            return value

    return None


def require_minimax_key(context: str = "this operation") -> str:
    """Like :func:`get_minimax_key` but exits with code 2 on failure.

    The error message names every file that was checked and the env var,
    but NEVER includes the key value (or any part of it).
    """
    key = get_minimax_key()
    if key:
        return key

    checked = "\n".join(f"  - {p}" for p in _checked_paths_for_error())
    # SystemExit(code) where code is an int => exit code is that int.
    # (If we passed a string, Python would treat it as the message and the
    # exit code would become 1, which would break callers that distinguish
    # "config error" from "real failure".)
    print(
        f"ERROR: {ENV_VAR} not found for {context}.\n"
        f"Checked (in order):\n{checked}\n"
        f"  - environment variable {ENV_VAR}\n"
        f"Set it in one of those locations and re-run.",
        file=sys.stderr,
    )
    raise SystemExit(2)
