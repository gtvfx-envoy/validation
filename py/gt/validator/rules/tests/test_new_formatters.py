"""Tests for SARIF and JUnit XML formatters."""

import json
import unittest

from gt.validator.reporting.formatters import JUnitXMLFormatter, SARIFFormatter
from gt.validator.reporting.models import ValidationReport
from gt.validator.rules.base import Severity, ValidationResult


def _make_report() -> ValidationReport:
    """Create a sample ValidationReport for testing."""
    results = [
        ValidationResult(
            asset_path=r"C:\project\Game\Content\Meshes\SM_Player.uasset",
            rule_name="file_size",
            category="filesystem",
            severity=Severity.ERROR,
            message="File size 60.00 MB exceeds limit of 50 MB.",
            passed=False,
            fix_hint="Reduce file size or increase max_file_size_mb in config.",
        ),
        ValidationResult(
            asset_path=r"C:\project\Game\Content\Textures\T_Wall.png",
            rule_name="texture_dimension",
            category="texture",
            severity=Severity.WARNING,
            message="Texture dimension 8192x8192 exceeds maximum of 4096.",
            passed=False,
            fix_hint="Resize texture to 4096x4096 or smaller.",
        ),
        ValidationResult(
            asset_path=r"C:\project\Game\Content\Materials\M_Floor.uasset",
            rule_name="material_slot_count",
            category="material",
            severity=Severity.INFO,
            message="Material has 3 slots (within limit of 4).",
            passed=True,
        ),
    ]
    return ValidationReport(
        results=results,
        asset_count=3,
        rule_count=3,
        duration_ms=150.5,
        tool_version="1.0.0",
    )


class TestSARIFFormatter(unittest.TestCase):
    """Test SARIFFormatter output."""

    def test_format_returns_valid_json(self) -> None:
        formatter = SARIFFormatter()
        report = _make_report()
        output = formatter.format(report)
        data = json.loads(output)
        self.assertEqual(data["version"], "2.1.0")
        self.assertIn("$schema", data)

    def test_format_includes_results(self) -> None:
        formatter = SARIFFormatter()
        report = _make_report()
        output = formatter.format(report)
        data = json.loads(output)
        results = data["runs"][0]["results"]
        self.assertEqual(len(results), 2)  # Only failed results (passing excluded by default)

    def test_format_excludes_skipped_by_default(self) -> None:
        formatter = SARIFFormatter()
        report = _make_report()
        output = formatter.format(report)
        data = json.loads(output)
        results = data["runs"][0]["results"]
        for r in results:
            self.assertNotIn("skipped", r.get("level", ""))

    def test_format_includes_passing_when_requested(self) -> None:
        formatter = SARIFFormatter(show_passing=True)
        report = _make_report()
        output = formatter.format(report)
        data = json.loads(output)
        results = data["runs"][0]["results"]
        self.assertEqual(len(results), 3)

    def test_format_maps_severity_to_level(self) -> None:
        formatter = SARIFFormatter()
        report = _make_report()
        output = formatter.format(report)
        data = json.loads(output)
        results = data["runs"][0]["results"]
        levels = {r["ruleId"]: r["level"] for r in results}
        self.assertEqual(levels["file_size"], "error")
        self.assertEqual(levels["texture_dimension"], "warning")

    def test_format_includes_tool_info(self) -> None:
        formatter = SARIFFormatter()
        report = _make_report()
        output = formatter.format(report)
        data = json.loads(output)
        tool = data["runs"][0]["tool"]["driver"]
        self.assertEqual(tool["name"], "GT Asset Validator")
        self.assertEqual(tool["version"], "1.0.0")

    def test_format_sanitizes_windows_paths(self) -> None:
        formatter = SARIFFormatter()
        report = _make_report()
        output = formatter.format(report)
        data = json.loads(output)
        results = data["runs"][0]["results"]
        for r in results:
            uri = r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
            self.assertNotIn("\\", uri)


class TestJUnitXMLFormatter(unittest.TestCase):
    """Test JUnitXMLFormatter output."""

    def test_format_returns_xml_string(self) -> None:
        formatter = JUnitXMLFormatter()
        report = _make_report()
        output = formatter.format(report)
        self.assertTrue(output.startswith('<?xml version="1.0"'))
        self.assertIn("<testsuites tests=", output)
        self.assertIn("</testsuites>", output)

    def test_format_includes_test_suites(self) -> None:
        formatter = JUnitXMLFormatter()
        report = _make_report()
        output = formatter.format(report)
        self.assertIn('<testsuite name="filesystem"', output)
        self.assertIn('<testsuite name="texture"', output)
        self.assertIn('<testsuite name="material"', output)

    def test_format_includes_test_cases(self) -> None:
        formatter = JUnitXMLFormatter()
        report = _make_report()
        output = formatter.format(report)
        self.assertIn('classname="filesystem.file_size"', output)
        self.assertIn('classname="texture.texture_dimension"', output)

    def test_format_includes_failures(self) -> None:
        formatter = JUnitXMLFormatter()
        report = _make_report()
        output = formatter.format(report)
        self.assertIn("<failure", output)
        self.assertIn("File size 60.00 MB exceeds limit of 50 MB.", output)

    def test_format_excludes_passing_by_default(self) -> None:
        formatter = JUnitXMLFormatter()
        report = _make_report()
        output = formatter.format(report)
        self.assertNotIn('classname="material.material_slot_count"', output)

    def test_format_includes_passing_when_requested(self) -> None:
        formatter = JUnitXMLFormatter(show_passing=True)
        report = _make_report()
        output = formatter.format(report)
        self.assertIn('classname="material.material_slot_count"', output)

    def test_format_escapes_xml_special_chars(self) -> None:
        formatter = JUnitXMLFormatter()
        results = [
            ValidationResult(
                asset_path=r"C:\project\Game\Content\Test<A>.uasset",
                rule_name="test_rule",
                category="test",
                severity=Severity.ERROR,
                message="Error with <tags> & \"quotes\"",
                passed=False,
            ),
        ]
        report = ValidationReport(results=results)
        output = formatter.format(report)
        self.assertIn("&lt;tags&gt;", output)
        self.assertIn("&amp;", output)
        self.assertIn("&quot;", output)


if __name__ == "__main__":  # pragma: no cover - manual execution
    unittest.main()
