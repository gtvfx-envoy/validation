"""Unified CLI entry-point for the asset validation framework.

Supports environment variable overrides for every flag (useful in CI)::

    VALIDATOR_FORMAT=json
    VALIDATOR_OUTPUT_DIR=/artifacts
    VALIDATOR_MAX_WORKERS=4

Unreal auto-dispatch — when ``--directory`` is a virtual Unreal path
(``/Game/...``) and the CLI is running in standalone Python, it automatically
spawns ``UnrealEditor-Cmd.exe`` and re-runs the same command inside the Editor::

    VALIDATOR_UNREAL_CMD=C:/UE5/Engine/Binaries/Win64/UnrealEditor-Cmd.exe
    VALIDATOR_UNREAL_PROJECT=C:/Projects/MyGame/MyGame.uproject

    python run_validator.py --directory /Game/ --format html

Exit codes:
    0 — all checks passed (or only warnings/infos)
    1 — at least one ERROR-severity failure
    2 — configuration error or invalid arguments

"""

from __future__ import annotations

import argparse
import os
import sys

from .config import Config
from .env import HAS_UNREAL
from .reporting.formatters import (
    ConsoleFormatter,
    HTMLFormatter,
    JSONFormatter,
    JUnitXMLFormatter,
    SARIFFormatter,
)
from .reporting.models import ValidationReport
from .rules.base import Severity
from .runner import ValidationRunner

_VERSION = "1.0.0"

_FORMATTERS = {
    "console": ConsoleFormatter,
    "json": JSONFormatter,
    "html": HTMLFormatter,
    "sarif": SARIFFormatter,
    "junit": JUnitXMLFormatter,
}


def _isVirtualPath(path: str) -> bool:
    """Return True if *path* looks like an Unreal virtual content-browser path.

    Args:
        path: The directory path string to test.

    Returns:
        ``True`` for paths beginning with ``/Game``, ``/Engine``, or ``/All``.

    """
    return path.startswith(("/Game", "/Engine", "/All"))


def _needsUnrealDispatch(directory: str | None) -> bool:
    """Return True when this run should be dispatched to UnrealEditor-Cmd.exe.

    Dispatch is required when:
    - We are **not** already inside Unreal (``HAS_UNREAL`` is ``False``)
    - AND the target directory is a virtual Unreal path (``/Game/...``)
      OR ``VALIDATOR_UNREAL_PROJECT`` is set (explicit opt-in).

    Args:
        directory: The ``--directory`` value, or ``None``.

    Returns:
        ``True`` if the run must be dispatched to ``UnrealEditor-Cmd.exe``.

    """
    if HAS_UNREAL:
        return False  # already inside Unreal; run directly
    if not directory:
        return False
    return _isVirtualPath(directory) or bool(os.environ.get("VALIDATOR_UNREAL_PROJECT"))


def _resolveArgvPaths(argv: list[str]) -> list[str]:
    """Resolve relative filesystem paths in *argv* to absolute paths.

    When the CLI dispatches to ``UnrealEditor-Cmd.exe``, the Editor's working
    directory may differ from the caller's.  Paths for ``--output-dir`` and
    ``--config`` must be absolute before being forwarded.

    Args:
        argv: The raw argument list (e.g. ``sys.argv[1:]``).

    Returns:
        A copy of *argv* with ``--output-dir`` and ``--config`` values
        replaced by their absolute equivalents when they are relative paths.

    """
    from pathlib import Path

    result = list(argv)
    _path_flags = {"--output-dir", "-o", "--config", "-c"}
    i = 0
    while i < len(result):
        if result[i] in _path_flags and i + 1 < len(result):
            candidate = result[i + 1]
            if not _isVirtualPath(candidate) and not os.path.isabs(candidate):
                result[i + 1] = str(Path(candidate).resolve())
        i += 1
    return result


def _dispatchToUnreal(argv: list[str]) -> int:
    """Spawn UnrealEditor-Cmd.exe and re-run the validator inside Unreal.

    Reads two env vars that must be set before calling:

    - ``VALIDATOR_UNREAL_CMD``     — path to ``UnrealEditor-Cmd.exe``
    - ``VALIDATOR_UNREAL_PROJECT`` — path to the ``.uproject`` file

    All ``VALIDATOR_*`` env vars present in the environment are forwarded to
    the subprocess automatically.  ``VALIDATOR_MAX_WORKERS`` defaults to
    ``"1"`` (serial) to keep the Unreal Python API thread-safe.

    Args:
        argv: The original argument list (already path-resolved).  Serialised
            as JSON into ``VALIDATOR_DISPATCH_ARGV`` so that
            ``validator/entry_points/_dispatch.py`` can forward them to
            ``cli.main()`` inside the Editor.

    Returns:
        The exit code returned by ``UnrealEditor-Cmd.exe``.

    """
    import json
    import subprocess
    from pathlib import Path

    unreal_cmd = os.environ.get("VALIDATOR_UNREAL_CMD")
    uproject = os.environ.get("VALIDATOR_UNREAL_PROJECT")

    if not unreal_cmd:
        print(
            "[CLI] ERROR: --directory is a virtual Unreal path but "
            "VALIDATOR_UNREAL_CMD is not set.\n"
            "       Set it to the absolute path of UnrealEditor-Cmd.exe.",
            file=sys.stderr,
        )
        return 2
    if not Path(unreal_cmd).is_file():
        print(
            f"[CLI] ERROR: VALIDATOR_UNREAL_CMD does not exist: {unreal_cmd}\n"
            "       Update run_with_overrides.ps1 with the correct path to "
            "UnrealEditor-Cmd.exe on this machine.",
            file=sys.stderr,
        )
        return 2
    if not uproject:
        print(
            "[CLI] ERROR: VALIDATOR_UNREAL_PROJECT is not set.\n"
            "       Set it to the absolute path of your .uproject file.",
            file=sys.stderr,
        )
        return 2
    if not Path(uproject).is_file():
        print(
            f"[CLI] ERROR: VALIDATOR_UNREAL_PROJECT does not exist: {uproject}\n"
            "       Update run_with_overrides.ps1 with the correct path to "
            "your .uproject file.",
            file=sys.stderr,
        )
        return 2

    dispatch_script = Path(__file__).parent / "entry_points" / "_dispatch.py"
    if not dispatch_script.exists():
        print(
            f"[CLI] ERROR: Dispatch script not found: {dispatch_script}\n"
            "       The validator package may be incomplete.",
            file=sys.stderr,
        )
        return 2

    env = os.environ.copy()
    env["VALIDATOR_DISPATCH_ARGV"] = json.dumps(argv)
    # Two levels up from cli.py (.../py/gt/validator/cli.py) is .../py — the
    # namespace-package root that must be on sys.path for `gt.validator` to
    # resolve inside the Unreal Editor's Python interpreter.
    env["VALIDATOR_SESSION_DIR"] = str(Path(__file__).parents[2])
    env.setdefault("VALIDATOR_MAX_WORKERS", "1")  # Unreal thread safety default

    print("[CLI] Dispatching to Unreal Editor...")
    print(f"[CLI]   Unreal cmd : {unreal_cmd}")
    print(f"[CLI]   Project    : {uproject}")
    print(f"[CLI]   Script     : {dispatch_script}")

    result = subprocess.run(
        [unreal_cmd, str(uproject), f"-ExecutePythonScript={dispatch_script}"],
        env=env,
    )
    return result.returncode


def _dryRun(args: argparse.Namespace) -> int:
    """Discover rules and validate config without running any validation.

    Prints a summary of what *would* run (rule count, directory asset count,
    config validity) then exits.  Virtual Unreal paths are noted but not
    walked on disk.

    Args:
        args: Parsed CLI arguments (env defaults not yet applied).

    Returns:
        ``0`` if all pre-flight checks pass, ``2`` if the config is invalid.

    """
    from .registry import registry

    print("[Dry Run] Discovering rules...")
    registry.discover()
    all_rules = registry.listRules()
    severity_filter = Severity(args.severity) if args.severity else None
    filtered = registry.getRules(category=args.category, severity=severity_filter)

    print(f"[Dry Run] Total registered rules : {len(all_rules)}")
    print(f"[Dry Run] Rules that would run   : {len(filtered)}")
    if args.category:
        print(f"[Dry Run] Category filter        : {args.category}")
    if args.severity:
        print(f"[Dry Run] Severity filter        : {args.severity}")

    if args.directory:
        if _isVirtualPath(args.directory):
            print(f"[Dry Run] Virtual path (Unreal)  : {args.directory}")
        elif os.path.isdir(args.directory):
            count = sum(len(files) for _, _, files in os.walk(args.directory))
            print(f"[Dry Run] Assets found           : {count} (in '{args.directory}')")
        else:
            print(f"[Dry Run] WARNING: --directory '{args.directory}' does not exist.")

    config_path = args.config or os.environ.get("VALIDATOR_CONFIG_PATH")
    print("[Dry Run] Config validation...")
    try:
        Config(config_path=config_path)
        print("[Dry Run] Config OK.")
    except (ValueError, OSError) as exc:
        print(f"[Dry Run] Config ERROR: {exc}")
        return 2
    return 0


def buildParser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    Returns:
        A configured :class:`argparse.ArgumentParser` instance.

    """
    parser = argparse.ArgumentParser(
        prog="validator",
        description="Asset Validation Framework — Production-hardened pipeline tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
environment variable overrides (all optional):
  VALIDATOR_CONFIG_PATH     — path to JSON config file
  VALIDATOR_FORMAT          — output format: console | json | html | sarif | junit
  VALIDATOR_OUTPUT_DIR      — directory to write report file
  VALIDATOR_LOG_LEVEL       — logging verbosity: DEBUG | INFO | WARNING | ERROR
  VALIDATOR_MAX_WORKERS     — number of parallel worker threads (1 = serial)
  VALIDATOR_DEBUG           — set to 1 to print full tracebacks on errors

unreal auto-dispatch (set once in your shell profile):
  VALIDATOR_UNREAL_CMD      — path to UnrealEditor-Cmd.exe
  VALIDATOR_UNREAL_PROJECT  — path to the .uproject file
  When --directory is a /Game/... path and these vars are set, the CLI
  automatically dispatches to UnrealEditor-Cmd.exe and re-runs inside the Editor.

exit codes:
  0   all checks passed (or only warnings/infos)
  1   at least one ERROR-severity failure
  2   configuration or argument error

""",
    )
    parser.add_argument(
        "--directory",
        "-d",
        metavar="PATH",
        required=False,
        help="Root directory to validate (recursively).",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=None,
        metavar="FILE",
        help="Path to a JSON config file.",
    )
    parser.add_argument(
        "--format",
        "-f",
            choices=["console", "json", "html", "sarif", "junit"],
        default=None,
        help="Output format (default: console, or VALIDATOR_FORMAT env var).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        metavar="DIR",
        help="Directory to write report file (console writes to stdout).",
    )
    parser.add_argument(
        "--category",
        default=None,
        metavar="NAME",
        help="Only run rules in this category.",
    )
    parser.add_argument(
        "--severity",
        default=None,
        choices=["ERROR", "WARNING", "INFO"],
        help="Only run rules at this exact severity.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        metavar="N",
        help="Number of parallel worker threads (1 = serial, safe in Unreal).",
    )
    parser.add_argument(
        "--show-passing",
        action="store_true",
        default=False,
        help="Include passing results in report output.",
    )
    parser.add_argument(
        "--filter-severity",
        default=None,
        choices=["ERROR", "WARNING", "INFO"],
        dest="filterSeverity",
        help="Only SHOW results at this severity (does not affect which rules run).",
    )
    parser.add_argument(
        "--filter-category",
        default=None,
        metavar="NAME",
        dest="filterCategory",
        help="Only SHOW results in this category (does not affect which rules run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dryRun",
        help="Discover rules and validate config without running validation.",
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        dest="listRules",
        help="List all registered rules and exit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Asset Validation Framework {_VERSION}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the validation CLI and return an exit code.

    Args:
        argv: Argument list to parse.  When ``None``, ``sys.argv[1:]`` is
            used.  Normalised to a list early so the dispatch path can
            forward it unmodified.

    Returns:
        ``0`` if all checks passed, ``1`` if any ERROR-severity rule failed,
        ``2`` if there was a configuration or argument error.

    """
    import logging

    # ConsoleFormatter and --list-rules output use box-drawing and status
    # glyphs (━, ✓, ✗, ↷, …). On Windows, stdout/stderr are not guaranteed to
    # be UTF-8 (e.g. legacy cp1252 console codepage, or a pipe/redirect with
    # no encoding hint) — encoding those glyphs then raises
    # UnicodeEncodeError ("'charmap' codec can't encode character..."),
    # which the broad except below reports as a generic CLI error. Force
    # UTF-8 with a safe fallback so report output never crashes the CLI
    # regardless of the host console's codepage.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # Non-reconfigurable stream (e.g. captured in tests) — ignore.

    # Normalise early so _dispatchToUnreal can forward the real argv.
    if argv is None:
        argv = sys.argv[1:]

    parser = buildParser()
    args = parser.parse_args(argv)

    # Pre-flight commands run locally without loading config or launching Unreal.
    if args.listRules:
        from .registry import registry

        registry.discover()
        rules = registry.listRules()
        if not rules:
            print("No rules registered.")
        else:
            print(f"{'NAME':<35} {'CATEGORY':<20} {'SEVERITY'}")
            print("-" * 65)
            for name, cls in sorted(rules.items()):
                print(f"{name:<35} {cls.category:<20} {cls.severity.value}")
        return 0

    if args.dryRun:
        return _dryRun(args)

    # Unreal auto-dispatch — must happen before config load and validation.
    if _needsUnrealDispatch(args.directory):
        return _dispatchToUnreal(_resolveArgvPaths(argv))

    config_path = args.config or os.environ.get("VALIDATOR_CONFIG_PATH")
    try:
        config = Config(config_path=config_path)
    except ValueError as exc:
        print(f"[CLI] ERROR: {exc}", file=sys.stderr)
        return 2

    log_level = (
        os.environ.get("VALIDATOR_LOG_LEVEL") or config.get("log_level", "WARNING")
    ).upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.WARNING))

    if not args.directory:
        parser.error("--directory is required unless --list-rules or --dry-run is specified.")
        return 2

    fmt = (
        args.format or os.environ.get("VALIDATOR_FORMAT") or config.get("report_format", "console")
    )
    output_dir = args.output_dir or os.environ.get("VALIDATOR_OUTPUT_DIR")
    severity_filter = Severity(args.severity) if args.severity else None
    max_workers = args.max_workers

    runner = ValidationRunner(
        config,
        category=args.category,
        severity=severity_filter,
        max_workers=max_workers,
    )

    try:
        report: ValidationReport = runner.runAndReport(args.directory)
        if getattr(runner, "last_run_cancelled", False):
            print("[CLI] Validation cancelled by user. Partial report shown below.")

        # Apply display-level filters — does not affect which rules ran.
        display_results = list(report.results)
        if args.filterSeverity:
            filter_sev = Severity(args.filterSeverity)
            display_results = [r for r in display_results if r.severity == filter_sev]
        if args.filterCategory:
            display_results = [r for r in display_results if r.category == args.filterCategory]
        display_report = ValidationReport(
            results=display_results,
            asset_count=report.asset_count,
            rule_count=report.rule_count,
            duration_ms=report.duration_ms,
            tool_version=report.tool_version,
        )

        formatter_cls = _FORMATTERS.get(fmt, ConsoleFormatter)
        formatter = formatter_cls(
            show_passing=args.show_passing or config.get("show_passing", False)
        )
        output_text = formatter.format(display_report)

        if output_dir and fmt != "console":
            os.makedirs(output_dir, exist_ok=True)
            ext = {
                "json": ".json",
                "html": ".html",
                "sarif": ".sarif.json",
                "junit": ".xml",
            }.get(fmt, ".txt")
            from datetime import datetime

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join(output_dir, f"validation_report_{ts}{ext}")
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(output_text)
            print(f"[CLI] Report written to: {out_path}")
        else:
            print(output_text)

        # Always evaluate errors from the full (unfiltered) report.
        if report.hasErrors():
            return 1
        return 0

    except KeyboardInterrupt:
        print("\n[CLI] Interrupted.")
        return 2
    except Exception as exc:  # noqa: BLE001 — broad catch at CLI boundary prevents silent crashes
        print(f"[CLI] ERROR: {exc}", file=sys.stderr)
        if os.environ.get("VALIDATOR_DEBUG"):
            import traceback

            traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
