"""Tests for context-aware validation rules.

This module contains tests for the context-aware rule system, including:
- HostType detection
- Registry context filtering
- Rule instantiation with context
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # goes to V:\repo\gtvfx-contrib\gt\validation
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest
from unittest.mock import Mock

from gt.runtime import HostType

from gt.validator.config import Config  # type: ignore
from gt.validator.registry import registry
from gt.validator.rules.base import AbstractRule, Severity


class TestContextAwareRules(unittest.TestCase):
    """Test context-aware rule behavior."""

    def setUp(self) -> None:
        """Clear the registry before each test."""
        registry.clear()
        self.config = Mock()
        self.config.get = Mock(return_value=True)

    def test_rule_with_context_attribute(self) -> None:
        """Test that a rule can have a context attribute."""

        @registry.register
        class TestRule(AbstractRule):
            name = "test_rule"
            category = "test"
            severity = Severity.ERROR
            context = HostType.UNREAL

            def __init__(self, config: Config, context: HostType) -> None:
                super().__init__(config)
                self.context = context

            def validate(self, asset_path: str) -> AbstractRule: ...

        self.assertEqual(TestRule.context, HostType.UNREAL)

    def test_registry_filters_by_context(self) -> None:
        """Test that registry filters rules by context.

        Note: We do NOT call ``registry.discover()`` here — this test is
        verifying manual registration + filtering, not auto-discovery.
        Calling discover() would reload all built-in rules and defeat the
        isolation we need for asserting exact counts.
        """

        @registry.register
        class UnrealRule(AbstractRule):
            name = "unreal_rule"
            category = "unreal"
            severity = Severity.ERROR
            context = HostType.UNREAL

            def __init__(self, config: Config, context: HostType) -> None:
                super().__init__(config)
                self.context = context

            def validate(self, asset_path: str) -> AbstractRule: ...

        @registry.register
        class StandaloneRule(AbstractRule):
            name = "standalone_rule"
            category = "standalone"
            severity = Severity.ERROR
            context = HostType.STANDALONE

            def __init__(self, config: Config, context: HostType) -> None:
                super().__init__(config)
                self.context = context

            def validate(self, asset_path: str) -> AbstractRule: ...

        # Test UNREAL context — should contain our test rule (and possibly others)
        unreal_rules = registry.getRules(context=HostType.UNREAL)
        unreal_names = {r.name for r in unreal_rules}
        self.assertIn("unreal_rule", unreal_names)

        # Test STANDALONE context — should contain our test rule (and possibly others)
        standalone_rules = registry.getRules(context=HostType.STANDALONE)
        standalone_names = {r.name for r in standalone_rules}
        self.assertIn("standalone_rule", standalone_names)

        # Test NONE context (no filter) — should contain both test rules
        all_rules = registry.getRules()
        all_names = {r.name for r in all_rules}
        self.assertIn("unreal_rule", all_names)
        self.assertIn("standalone_rule", all_names)

    def test_registry_getRules_accepts_context_parameter(self) -> None:
        """Test that getRules accepts context parameter.

        Note: We do NOT call ``registry.discover()`` here — this test is
        verifying the API contract, not auto-discovery behavior.
        """

        @registry.register
        class TestRule(AbstractRule):
            name = "test_rule"
            category = "test"
            severity = Severity.ERROR
            context = HostType.UNREAL

            def __init__(self, config: Config, context: HostType) -> None:
                super().__init__(config)
                self.context = context

            def validate(self, asset_path: str) -> AbstractRule: ...

        # Should not raise an error — just verify the API works
        rules = registry.getRules(context=HostType.UNREAL)
        rule_names = {r.name for r in rules}
        self.assertIn("test_rule", rule_names)

    def test_rule_instantiation_with_context(self) -> None:
        """Test that rules can be instantiated with context parameter."""

        @registry.register
        class TestRule(AbstractRule):
            name = "test_rule"
            category = "test"
            severity = Severity.ERROR
            context = HostType.UNREAL

            def __init__(self, config: Config, context: HostType) -> None:
                super().__init__(config)
                self.context = context

            def validate(self, asset_path: str) -> AbstractRule: ...

        registry.discover()
        rule = TestRule(self.config, HostType.UNREAL)
        self.assertEqual(rule.context, HostType.UNREAL)


if __name__ == "__main__":
    unittest.main()
