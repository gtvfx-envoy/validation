"""Portable end-to-end validation CLI tests through Envoy."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from functools import partial
from pathlib import Path

import pytest

__all__ = []

REPO_ROOT = Path(__file__).resolve().parents[5]
ValidationCommand = Callable[..., subprocess.CompletedProcess[str]]


def findEnvoyBinary() -> str:
    """Find the Envoy entry point on PATH."""
    envoy_path = shutil.which("envoy") or shutil.which("en")
    if envoy_path is None:
        raise FileNotFoundError("Envoy must be on PATH to run CLI smoke tests")
    launcher = Path(envoy_path)
    if launcher.suffix.lower() in {".bat", ".cmd"}:
        repository = launcher.parent.parent
        candidates = (
            launcher.with_name("envoy.exe"),
            repository / "rust" / "target" / "release" / "envoy.exe",
            repository / "rust" / "target" / "debug" / "envoy.exe",
        )
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    return envoy_path


def envoyCommand() -> list[str]:
    """Build an Envoy invocation using the isolated CI environment, if set."""
    command = [findEnvoyBinary()]
    commands_file = os.environ.get("ENVOY_COMMANDS_FILE")
    if commands_file:
        command.extend(["--ignore-config", "--inherit-env", "--commands-file", commands_file])
    return command


def runEnvoy(*args: str) -> subprocess.CompletedProcess[str]:
    """Run Envoy without a shell except for Windows batch launchers."""
    command = [*envoyCommand(), *args]
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    environment.pop("VALIDATOR_OUTPUT_DIR", None)
    environment.pop("VALIDATOR_UNREAL_PROJECT", None)
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        env=environment,
        cwd=REPO_ROOT,
        shell=os.name == "nt" and Path(command[0]).suffix.lower() in {".bat", ".cmd"},
        check=False,
    )


def _runValidate(sample_directory: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the validator against temporary sample assets."""
    return runEnvoy("validate", "--directory", str(sample_directory), *args)


@pytest.fixture(name="sample_directory")
def sampleDirectory(tmp_path: Path) -> Path:
    """Create filesystem-only assets in a path containing spaces."""
    sample_directory = tmp_path / "sample content"
    sample_directory.mkdir()
    (sample_directory / "SM_Test.fbx").write_bytes(b"sample mesh")
    return sample_directory


@pytest.fixture(name="validate")
def validationCommand(sample_directory: Path) -> ValidationCommand:
    """Bind the validator subprocess helper to this test's sample directory."""
    return partial(_runValidate, sample_directory)


def loadJSONReport(output_directory: Path) -> dict:
    """Read the single JSON report emitted by a CLI invocation."""
    reports = list(output_directory.glob("*.json"))
    assert len(reports) == 1
    return json.loads(reports[0].read_text(encoding="utf-8"))


@pytest.mark.cli_smoke
class TestCLISmokeIntegration:
    """End-to-end CLI smoke tests."""

    def testValidateRunsEndToEnd(self, validate: ValidationCommand) -> None:
        """Verify validation completes rather than failing during setup."""
        result = validate()
        assert result.returncode in {0, 1}, result.stderr
        assert "ASSET VALIDATION REPORT" in result.stdout

    def testConsoleFormatOutput(self, validate: ValidationCommand) -> None:
        """Verify console output contains a validation report."""
        result = validate("--format", "console")
        assert result.returncode in {0, 1}, result.stderr
        assert "ASSET VALIDATION REPORT" in result.stdout

    def testJSONFormatOutput(self, validate: ValidationCommand, tmp_path: Path) -> None:
        """Verify JSON output contains a report for the sample asset."""
        result = validate("--format", "json", "--output-dir", str(tmp_path))
        assert result.returncode in {0, 1}, result.stderr
        assert loadJSONReport(tmp_path)["summary"]["total_assets"] == 1

    def testListRulesFlag(self, validate: ValidationCommand) -> None:
        """Verify rule discovery succeeds."""
        result = validate("--list-rules")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip()

    def testInvalidDirectory(
        self,
        validate: ValidationCommand,
        sample_directory: Path,
    ) -> None:
        """Verify a nonexistent directory returns a configuration error."""
        result = validate("--directory", str(sample_directory / "missing"))
        assert result.returncode == 2
        assert "Not a valid directory" in result.stderr

    def testExitCode(self, validate: ValidationCommand, sample_directory: Path) -> None:
        """Verify validation errors return a failing exit code."""
        (sample_directory / "invalid.txt").write_text("invalid asset", encoding="utf-8")
        result = validate()
        assert result.returncode == 1, result.stderr


@pytest.mark.cli_smoke
class TestCLIFlags:
    """Test CLI flag combinations."""

    def testFormatFlagVariants(self, validate: ValidationCommand, tmp_path: Path) -> None:
        """Verify both supported smoke-test formats complete successfully."""
        for output_format in ("console", "json"):
            result = validate("--format", output_format, "--output-dir", str(tmp_path))
            assert result.returncode in {0, 1}, result.stderr
            assert result.stdout.strip()

    def testDirectoryOverride(
        self,
        validate: ValidationCommand,
        tmp_path: Path,
    ) -> None:
        """Verify an explicit directory overrides the sample directory."""
        directory = tmp_path / "other content"
        directory.mkdir()
        result = validate(
            "--directory", str(directory), "--format", "json", "--output-dir", str(tmp_path)
        )
        assert result.returncode in {0, 1}, result.stderr
        assert loadJSONReport(tmp_path)["summary"]["total_assets"] == 0


def testSimpleSubprocess() -> None:
    """Verify subprocess argument forwarding through Envoy."""
    result = runEnvoy("python", "-c", "print('hello')")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "hello"
