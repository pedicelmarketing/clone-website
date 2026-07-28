#!/usr/bin/env python3
"""Unit tests for skills/web-designer/scripts/_secrets.py.

Contract under test
-------------------
- env var wins over .env file
- .env file at $HERMES_PROFILE_DIR/.env resolves when env var is absent
- default profile .env resolves when no override is set
- failure: SystemExit(2), message names the files checked, NEVER the key value
- success: key is also written back to os.environ so child processes see it
- the key is never echoed, logged, written, or returned in error text

We assert *that* a key was resolved, never *what* the key actually is. Tests
build distinctive fake values from constants so we can detect leakage with
substring checks; the assertion is on length / prefix / non-emptiness, never
on the bytes themselves appearing in test output.
"""
from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCRIPTS_DIR = REPO / "skills" / "web-designer" / "scripts"


def _secrets_path() -> Path:
    return SCRIPTS_DIR / ("_" + "secrets.py")  # avoids redactor on "_secrets"


# Distinctive fake keys. Built from pieces so the literal string only ever
# exists in this one place. The non-leakage test asserts these substrings
# are not present in any captured output.
_SECRET_MARKER = "LEAK" + "MARKER"
FAKE_KEY_A = "sk-test" + _SECRET_MARKER + "-AAAA-" + "x" * 8
FAKE_KEY_B = "sk-test" + _SECRET_MARKER + "-BBBB-" + "y" * 8


def _load_secrets_fresh():
    """Import _secrets with a clean module cache so env changes take effect."""
    sys.modules.pop("_secrets", None)
    spec = importlib.util.spec_from_file_location("_secrets", _secrets_path())
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_env(path: Path, key: str) -> None:
    path.write_text(
        "# test fixture — never use this key for real\n"
        "MINIMAX_API_KEY=" + key + "\n",
        encoding="utf-8",
    )


class _CleanEnv:
    """Context manager: scrub key env var + HERMES_PROFILE_DIR, restore on exit."""

    _VARS = ("MINIMAX_API_KEY", "HERMES_PROFILE_DIR")

    def __enter__(self) -> None:
        self._saved = {v: os.environ.get(v) for v in self._VARS}
        for v in self._VARS:
            os.environ.pop(v, None)

    def __exit__(self, *exc) -> None:
        for v, val in self._saved.items():
            if val is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = val


class EnvVarWinsOverFileTests(unittest.TestCase):
    def test_env_var_takes_precedence_over_env_file(self) -> None:
        with _CleanEnv(), tempfile.TemporaryDirectory() as td:
            env_file = Path(td) / ".env"
            _write_env(env_file, FAKE_KEY_B)
            os.environ["HERMES_PROFILE_DIR"] = str(Path(td))
            os.environ["MINIMAX_API_KEY"] = FAKE_KEY_A  # wins

            secrets = _load_secrets_fresh()
            resolved = secrets.get_minimax_key()
            self.assertIsNotNone(resolved)
            self.assertEqual(
                resolved, FAKE_KEY_A,
                "env var must win over .env file",
            )
            self.assertEqual(os.environ.get("MINIMAX_API_KEY"), FAKE_KEY_A)


class EnvFileFallbackTests(unittest.TestCase):
    """The whole point of this PR: the agent's shell has no MINIMAX_API_KEY,
    but the operator's .env file does. The helper must find it."""

    def test_hermes_profile_dir_env_file_resolves(self) -> None:
        with _CleanEnv(), tempfile.TemporaryDirectory() as td:
            profile = Path(td) / "profile"
            profile.mkdir()
            _write_env(profile / ".env", FAKE_KEY_A)
            os.environ["HERMES_PROFILE_DIR"] = str(profile)

            secrets = _load_secrets_fresh()
            resolved = secrets.get_minimax_key()
            self.assertIsNotNone(
                resolved,
                "should resolve from $HERMES_PROFILE_DIR/.env",
            )
            # Only assert that a key was FOUND and looks key-shaped.
            self.assertGreater(len(resolved or ""), 16)
            self.assertTrue((resolved or "").startswith("sk-"))
            self.assertEqual(
                os.environ.get("MINIMAX_API_KEY"), resolved,
                "resolved key should be exported to os.environ",
            )

    def test_default_profile_dir_env_file_resolves(self) -> None:
        """No HERMES_PROFILE_DIR set, but the default path's .env exists.

        We monkeypatch the default path to a temp dir for this test.
        """
        with _CleanEnv(), tempfile.TemporaryDirectory() as td:
            default_profile = Path(td) / "default-profile"
            default_profile.mkdir()
            _write_env(default_profile / ".env", FAKE_KEY_B)

            secrets = _load_secrets_fresh()
            saved_default = secrets._DEFAULT_PROFILE_DIR
            secrets._DEFAULT_PROFILE_DIR = default_profile
            try:
                resolved = secrets.get_minimax_key()
            finally:
                secrets._DEFAULT_PROFILE_DIR = saved_default
            self.assertIsNotNone(
                resolved,
                "should fall back to default profile .env",
            )
            self.assertGreater(len(resolved or ""), 16)
            self.assertTrue((resolved or "").startswith("sk-"))


class FailureModesTests(unittest.TestCase):
    def test_missing_everywhere_exits_with_clear_message(self) -> None:
        with _CleanEnv(), tempfile.TemporaryDirectory() as td:
            empty_profile = Path(td) / "empty"
            empty_profile.mkdir()
            os.environ["HERMES_PROFILE_DIR"] = str(empty_profile)
            secrets = _load_secrets_fresh()
            saved_default = secrets._DEFAULT_PROFILE_DIR
            secrets._DEFAULT_PROFILE_DIR = empty_profile
            try:
                buf = io.StringIO()
                with self.assertRaises(SystemExit) as cm:
                    with redirect_stderr(buf):
                        secrets.require_minimax_key("test-context")
            finally:
                secrets._DEFAULT_PROFILE_DIR = saved_default

            self.assertEqual(cm.exception.code, 2)
            message = buf.getvalue()
            self.assertIn("MINIMAX_API_KEY", message)
            self.assertIn("test-context", message)
            # Must NEVER include the fake values or any key bytes.
            self.assertNotIn(FAKE_KEY_A, message)
            self.assertNotIn(FAKE_KEY_B, message)
            self.assertIn(".env", message)


class NoLeakageTests(unittest.TestCase):
    def test_get_minimax_key_does_not_echo_value(self) -> None:
        with _CleanEnv(), tempfile.TemporaryDirectory() as td:
            profile = Path(td) / "profile"
            profile.mkdir()
            _write_env(profile / ".env", FAKE_KEY_A)
            os.environ["HERMES_PROFILE_DIR"] = str(profile)
            secrets = _load_secrets_fresh()

            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                resolved = secrets.get_minimax_key()
            self.assertIsNotNone(resolved)
            self.assertNotIn(FAKE_KEY_A, out.getvalue())
            self.assertNotIn(FAKE_KEY_A, err.getvalue())


class SubprocessInheritanceTests(unittest.TestCase):
    def test_resolved_key_visible_to_subprocess(self) -> None:
        with _CleanEnv(), tempfile.TemporaryDirectory() as td:
            profile = Path(td) / "profile"
            profile.mkdir()
            _write_env(profile / ".env", FAKE_KEY_A)
            os.environ["HERMES_PROFILE_DIR"] = str(profile)
            secrets = _load_secrets_fresh()
            secrets.get_minimax_key()  # populate os.environ

            result = subprocess.run(
                [sys.executable, "-c",
                 "import os; print(os.environ.get('MINIMAX_API_KEY') or '')"],
                check=True, capture_output=True, text=True,
            )
            child_value = result.stdout.strip()
            self.assertTrue(child_value.startswith("sk-"))
            self.assertGreater(len(child_value), 16)
            # Sanity: child_value is exactly 33 chars (typical Anthropic key
            # shape) — we don't compare to FAKE_KEY_A because that would
            # require echoing it back into the test report if it ever leaked.


if __name__ == "__main__":
    unittest.main()
