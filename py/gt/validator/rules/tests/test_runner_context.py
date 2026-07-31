"""Tests for ValidationRunner context handling.

This module contains tests for the ValidationRunner's context handling.
Uses production rule classes via absolute imports.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent.parent  # goes to V:\repo\gtvfx-contrib\gt\validation
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest

from gt.runtime import HostType

from gt.validator.config import Config  # type: ignore
from gt.validator.context.filesystem import FilesystemContext
from gt.validator.registry import registry
from gt.validator.rules.base import AbstractRule, Severity
from gt.validator.runner import ValidationRunner


class TestValidationRunnerContext(unittest.TestCase):
    """Test ValidationRunner context handling.

    These tests monkeypatch ``RuntimeDetector.getCurrentHost`` to return a
    known value so the runner's context-filtering logic can be verified
    deterministically regardless of what host detection finds in the test
    environment (e.g. envoy may expose Krita/Unreal stubs that would
    otherwise confuse the detector).
    """

    def setUp(self) -> None:
        """Clear the registry and force STANDALONE host for each test."""
        registry.clear()
        self.config = Config()  # Use defaults instead of Mock for production rules
        self._host_patcher = patch(
            "gt.runtime.RuntimeDetector.getCurrentHost",
            return_value=HostType.STANDALONE,
        )
        self._host_patcher.start()

    def tearDown(self) -> None:
        """Stop the host-type monkeypatch."""
        self._host_patcher.stop()

    def test_runner_gets_current_context(self) -> None:
        """ValidationRunner auto-detects a ValidationContext when none is given."""
        runner = ValidationRunner(self.config)
        # No context was passed explicitly, so ContextFactory should have
        # selected FilesystemContext (the standalone default).
        self.assertIsInstance(runner.context, FilesystemContext)

    def test_runner_passes_context_to_rules(self) -> None:
        """ValidationRunner passes its context down to rule instances."""

        @registry.register
        class SampleStandaloneRule(AbstractRule):
            name = "sample_standalone_rule"
            category = "test"
            severity = Severity.ERROR
            context = HostType.STANDALONE

            def validate(self, asset_path: str):  # noqa: D102
                return self._makeResult(asset_path, passed=True, message="ok")

        registry.discover()
        runner = ValidationRunner(self.config)

        matching = [r for r in runner.rules if r.name == "sample_standalone_rule"]
        self.assertEqual(len(matching), 1)
        # The rule should have received the runner's own context instance.
        self.assertIs(matching[0]._validation_context, runner.context)

    def test_runner_filters_rules_by_context(self) -> None:
        """ValidationRunner only instantiates rules matching the current host."""

        @registry.register
        class SampleUnrealOnlyRule(AbstractRule):
            name = "sample_unreal_only_rule"
            category = "unreal"
            severity = Severity.ERROR
            context = HostType.UNREAL

            def validate(self, asset_path: str):  # noqa: D102
                return self._makeResult(asset_path, passed=True, message="ok")

        @registry.register
        class SampleStandaloneOnlyRule(AbstractRule):
            name = "sample_standalone_only_rule"
            category = "standalone"
            severity = Severity.ERROR
            context = HostType.STANDALONE

            def validate(self, asset_path: str):  # noqa: D102
                return self._makeResult(asset_path, passed=True, message="ok")

        registry.discover()
        runner = ValidationRunner(self.config)

        active_names = {r.name for r in runner.rules}
        # Only the STANDALONE-context rule should be active in this environment.
        self.assertIn("sample_standalone_only_rule", active_names)
        self.assertNotIn("sample_unreal_only_rule", active_names)


if __name__ == "__main__":
    unittest.main()
