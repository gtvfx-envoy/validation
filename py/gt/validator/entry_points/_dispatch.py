"""Internal dispatch entry-point — invoked by cli._dispatchToUnreal() via UnrealEditor-Cmd.exe.

This script is **not** intended for direct use.  When you run::

    python run_validator.py --directory /Game/ --format html

``cli.main()`` detects the virtual path, serialises the argument list into the
``VALIDATOR_DISPATCH_ARGV`` environment variable, and spawns::

    UnrealEditor-Cmd.exe project.uproject -ExecutePythonScript=_dispatch.py

This script then runs inside the Editor, restores the original argv, and calls
``cli.main()`` — giving you the exact same behaviour as the CLI, but with the
full Unreal Python API available for introspection rules.

Environment variables read:
    VALIDATOR_SESSION_DIR    — filesystem path to the `py` namespace-package
                               root, added to sys.path so `gt.validator`
                               resolves inside the Unreal Editor's Python.
    VALIDATOR_DISPATCH_ARGV  — JSON-encoded list of CLI arguments forwarded from
                               the parent process

"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

# ── Log file setup ────────────────────────────────────────────────────────── #
# Unreal closes immediately on exception.  Write all output to a log file so
# errors are visible after the window closes.
# Three levels up from _dispatch.py (.../py/gt/validator/entry_points/_dispatch.py)
# is .../py — the namespace-package root (matches cli.py's VALIDATOR_SESSION_DIR).
_session_dir_early = os.environ.get(
    "VALIDATOR_SESSION_DIR",
    str(Path(__file__).resolve().parents[3]),
)
_log_path = Path(_session_dir_early) / "artifacts" / "_dispatch.log"
_log_path.parent.mkdir(parents=True, exist_ok=True)


def _log(message: str) -> None:
    """Write *message* to stdout and the dispatch log file."""
    print(message, flush=True)
    with _log_path.open("a", encoding="utf-8") as _fh:
        _fh.write(message + "\n")


_log(f"[dispatch] Starting — log: {_log_path}")

try:
    # ── Path setup ────────────────────────────────────────────────────────── #
    # The parent cli.py sets VALIDATOR_SESSION_DIR to the `py` namespace-package
    # root so the correct gt.validator package is loaded regardless of Unreal's
    # working directory.
    _session_dir = os.environ.get(
        "VALIDATOR_SESSION_DIR",
        str(Path(__file__).resolve().parents[3]),
    )
    if _session_dir not in sys.path:
        sys.path.insert(0, _session_dir)
    _log(f"[dispatch] Session dir  : {_session_dir}")

    # ── Module cache cleanup ───────────────────────────────────────────────── #
    # Unreal's Python interpreter persists between script executions.  Purge any
    # previously loaded gt.validator package so this session's version loads
    # cleanly (gt.runtime is left alone — it does not change between runs).
    for _k in [k for k in sys.modules if k == "gt.validator" or k.startswith("gt.validator.")]:
        del sys.modules[_k]

    # ── Unreal guard ─────────────────────────────────────────────────────── #
    from gt.validator.env import HAS_UNREAL  # noqa: E402

    if not HAS_UNREAL:
        raise RuntimeError(
            "_dispatch.py must be executed via UnrealEditor-Cmd.exe.\n"
            "Run `python run_validator.py --directory /Game/` — "
            "the CLI dispatches automatically when VALIDATOR_UNREAL_CMD is set."
        )

    _log("[dispatch] Unreal environment detected.")

    # ── Restore original argv and delegate to cli.main() ─────────────────── #
    from gt.validator.cli import main  # noqa: E402

    _raw = os.environ.get("VALIDATOR_DISPATCH_ARGV")
    if _raw:
        _argv: list[str] = json.loads(_raw)
    else:
        # Fallback when launched manually (e.g. during debugging)
        _directory = os.environ.get("VALIDATOR_DIRECTORY", "/Game/")
        _argv = ["--directory", _directory]

    # Ensure serial execution — the Unreal Python API is not thread-safe.
    if "--max-workers" not in _argv:
        _argv = ["--max-workers", "1"] + _argv

    _log(f"[dispatch] argv: {_argv}")
    _exit_code = main(_argv)
    _log(f"[dispatch] Finished — exit code: {_exit_code}")
    sys.exit(_exit_code)

except SystemExit:
    raise  # let sys.exit() propagate normally

except Exception:
    _tb = traceback.format_exc()
    _log(f"[dispatch] UNHANDLED EXCEPTION:\n{_tb}")
    sys.exit(2)
