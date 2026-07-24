"""Comprehensive test suite for validation rules.

Tests production rule implementations directly, using ``FilesystemContext``
(or a small fake context that returns pre-built metadata) so no Unreal
Engine dependency is required. Rules that only make sense inside Unreal
(e.g. StaticMesh/Overdraw, which call ``loadUnrealAsset``) are verified to
degrade gracefully to a skipped result rather than crashing.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # goes to V:\repo\gtvfx-contrib\gt\validation
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from unittest.mock import patch

from gt.runtime import HostType

from gt.validator.config import Config  # type: ignore
from gt.validator.context.base import AssetMetadata, ValidationContext  # type: ignore
from gt.validator.context.filesystem import FilesystemContext  # type: ignore
from gt.validator.registry import registry as rule_registry  # type: ignore
from gt.validator.rules.bounding_box import (  # type: ignore
    BoundingBoxExtentRule,
    BoundingBoxOriginRule,
)
from gt.validator.rules.filesystem import FileSizeRule, ValidExtensionRule  # type: ignore
from gt.validator.rules.naming import (  # type: ignore
    FilenameLengthRule,
    NamingConventionRule,
    PrefixConventionRule,
)
from gt.validator.rules.overdraw import OverdrawHeuristicRule  # type: ignore
from gt.validator.rules.skeletal_mesh import SkeletalMeshLODCountRule  # type: ignore
from gt.validator.rules.static_mesh import (  # type: ignore
    StaticMeshLODCountRule,
    StaticMeshMaterialSlotRule,
)


class _FakeMetadataContext(ValidationContext):
    """Minimal ValidationContext stub returning one pre-built AssetMetadata.

    Lets tests exercise property-driven rule logic (e.g. LOD count, bounding
    box extents) without requiring a real Unreal Engine session.
    """

    def __init__(self, metadata: AssetMetadata) -> None:
        self._metadata = metadata

    def isAvailable(self) -> bool:
        """Return True; this stub is always usable in tests."""
        return True

    def collect(self, asset_path: str) -> AssetMetadata:
        """Return the pre-built metadata regardless of asset_path."""
        return self._metadata


class TestNamingConventionRule(unittest.TestCase):
    """Test NamingConventionRule."""

    def setUp(self) -> None:
        self.config = Config()
        self.context = FilesystemContext()

    def test_valid_naming(self) -> None:
        rule = NamingConventionRule(self.config, validation_context=self.context)
        result = rule.validate("SM_MyAsset.uasset")
        self.assertTrue(result.passed)

    def test_invalid_naming(self) -> None:
        rule = NamingConventionRule(self.config, validation_context=self.context)
        result = rule.validate("my_asset.uasset")
        self.assertFalse(result.passed)


class TestFileSizeRule(unittest.TestCase):
    """Test FileSizeRule."""

    def setUp(self) -> None:
        self.config = Config()
        self.context = FilesystemContext()

    def test_small_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"small file content")
            path = f.name
        try:
            rule = FileSizeRule(self.config, validation_context=self.context)
            result = rule.validate(path)
            self.assertTrue(result.passed)
        finally:
            os.unlink(path)

    def test_large_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"A" * (60 * 1024 * 1024))  # 60MB
            path = f.name
        try:
            rule = FileSizeRule(self.config, validation_context=self.context)
            result = rule.validate(path)
            self.assertFalse(result.passed)
        finally:
            os.unlink(path)


class TestValidExtensionRule(unittest.TestCase):
    """Test ValidExtensionRule."""

    def setUp(self) -> None:
        self.config = Config()
        self.context = FilesystemContext()

    def test_valid_extension(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".uasset") as f:
            path = f.name
        try:
            rule = ValidExtensionRule(self.config, validation_context=self.context)
            result = rule.validate(path)
            self.assertTrue(result.passed)
        finally:
            os.unlink(path)

    def test_invalid_extension(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xyz") as f:
            path = f.name
        try:
            rule = ValidExtensionRule(self.config, validation_context=self.context)
            result = rule.validate(path)
            self.assertFalse(result.passed)
        finally:
            os.unlink(path)


class TestPrefixConventionRule(unittest.TestCase):
    """Test PrefixConventionRule."""

    def setUp(self) -> None:
        self.config = Config()
        self.context = FilesystemContext()

    def test_valid_prefix(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, prefix="SM_", suffix=".uasset") as f:
            path = f.name
        try:
            rule = PrefixConventionRule(self.config, validation_context=self.context)
            result = rule.validate(path)
            self.assertTrue(result.passed)
        finally:
            os.unlink(path)

    def test_invalid_prefix(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, prefix="bad_", suffix=".uasset") as f:
            path = f.name
        try:
            rule = PrefixConventionRule(self.config, validation_context=self.context)
            result = rule.validate(path)
            self.assertFalse(result.passed)
        finally:
            os.unlink(path)


class TestFilenameLengthRule(unittest.TestCase):
    """Test FilenameLengthRule."""

    def setUp(self) -> None:
        self.config = Config()
        self.context = FilesystemContext()

    def test_valid_length(self) -> None:
        rule = FilenameLengthRule(self.config, validation_context=self.context)
        result = rule.validate("SM_MyAsset.uasset")
        self.assertTrue(result.passed)

    def test_long_filename(self) -> None:
        rule = FilenameLengthRule(self.config, validation_context=self.context)
        long_name = "A" * 70 + ".uasset"
        result = rule.validate(long_name)
        self.assertFalse(result.passed)


class TestBoundingBoxExtentRule(unittest.TestCase):
    """Test BoundingBoxExtentRule."""

    def setUp(self) -> None:
        self.config = Config()

    def test_within_limit(self) -> None:
        meta = AssetMetadata(
            path="/Game/MyMesh.uasset",
            properties={"bounds_extent_x": 10.0, "bounds_extent_y": 20.0, "bounds_extent_z": 15.0},
        )
        rule = BoundingBoxExtentRule(self.config, validation_context=_FakeMetadataContext(meta))
        result = rule.validate("/Game/MyMesh.uasset")
        self.assertTrue(result.passed)

    def test_exceeds_limit(self) -> None:
        meta = AssetMetadata(
            path="/Game/MyMesh.uasset",
            properties={"bounds_extent_x": 9999.0, "bounds_extent_y": 20.0, "bounds_extent_z": 15.0},
        )
        rule = BoundingBoxExtentRule(self.config, validation_context=_FakeMetadataContext(meta))
        result = rule.validate("/Game/MyMesh.uasset")
        self.assertFalse(result.passed)


class TestBoundingBoxOriginRule(unittest.TestCase):
    """Test BoundingBoxOriginRule."""

    def setUp(self) -> None:
        self.config = Config()

    def test_within_limit(self) -> None:
        meta = AssetMetadata(
            path="/Game/MyMesh.uasset",
            properties={"origin_x": 1.0, "origin_y": 1.0, "origin_z": 1.0},
        )
        rule = BoundingBoxOriginRule(self.config, validation_context=_FakeMetadataContext(meta))
        result = rule.validate("/Game/MyMesh.uasset")
        self.assertTrue(result.passed)


class TestSkeletalMeshLODCountRule(unittest.TestCase):
    """Test SkeletalMeshLODCountRule."""

    def setUp(self) -> None:
        self.config = Config()

    def test_valid_lod_count_within_range(self) -> None:
        meta = AssetMetadata(path="/Game/SK_Hero.uasset", properties={"lod_count": 3})
        rule = SkeletalMeshLODCountRule(self.config, validation_context=_FakeMetadataContext(meta))
        result = rule.validate("/Game/SK_Hero.uasset")
        self.assertTrue(result.passed)

    def test_lod_count_below_minimum(self) -> None:
        meta = AssetMetadata(path="/Game/SK_Hero.uasset", properties={"lod_count": 0})
        rule = SkeletalMeshLODCountRule(self.config, validation_context=_FakeMetadataContext(meta))
        result = rule.validate("/Game/SK_Hero.uasset")
        self.assertFalse(result.passed)


class TestStaticMeshLODCountRule(unittest.TestCase):
    """Test StaticMeshLODCountRule.

    StaticMesh rules load assets via the Unreal API; outside Unreal they must
    degrade gracefully to a skipped (not crashed, not failed) result.
    """

    def setUp(self) -> None:
        self.config = Config()
        self.context = FilesystemContext()

    def test_skips_outside_unreal(self) -> None:
        rule = StaticMeshLODCountRule(self.config, validation_context=self.context)
        result = rule.validate("/Game/MyMesh.uasset")
        self.assertTrue(result.passed)
        self.assertTrue(result.skipped)


class TestStaticMeshMaterialSlotRule(unittest.TestCase):
    """Test StaticMeshMaterialSlotRule (Unreal-only; skips outside Unreal)."""

    def setUp(self) -> None:
        self.config = Config()
        self.context = FilesystemContext()

    def test_skips_outside_unreal(self) -> None:
        rule = StaticMeshMaterialSlotRule(self.config, validation_context=self.context)
        result = rule.validate("/Game/MyMaterial.uasset")
        self.assertTrue(result.passed)
        self.assertTrue(result.skipped)


class TestOverdrawHeuristicRule(unittest.TestCase):
    """Test OverdrawHeuristicRule (Unreal-only; skips outside Unreal)."""

    def setUp(self) -> None:
        self.config = Config()
        self.context = FilesystemContext()

    def test_skips_outside_unreal(self) -> None:
        rule = OverdrawHeuristicRule(self.config, validation_context=self.context)
        result = rule.validate("/Game/MyMaterial.uasset")
        self.assertTrue(result.passed)
        self.assertTrue(result.skipped)


class TestValidationRunnerIntegration(unittest.TestCase):
    """Test ValidationRunner integration with real filesystem assets."""

    def setUp(self) -> None:
        rule_registry.clear()
        self.config = Config()
        self._host_patcher = patch(
            "gt.runtime.RuntimeDetector.getCurrentHost",
            return_value=HostType.STANDALONE,
        )
        self._host_patcher.start()

    def tearDown(self) -> None:
        """Stop the host-type monkeypatch."""
        self._host_patcher.stop()

    def test_runner_with_real_assets(self) -> None:
        from gt.validator.runner import ValidationRunner  # type: ignore

        with tempfile.NamedTemporaryFile(delete=False, suffix=".uasset") as f1:
            f1.write(b"small asset 1")
            path1 = f1.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".uasset") as f2:
            f2.write(b"A" * (60 * 1024 * 1024))  # 60MB file
            path2 = f2.name

        try:
            runner = ValidationRunner(self.config, max_workers=1)
            report = runner.validateAssets([path1, path2])

            self.assertGreater(len(report.results), 0)
            file_size_results = {
                r.asset_path: r for r in report.results if r.rule_name == "file_size"
            }
            self.assertTrue(file_size_results[path1].passed)
            self.assertFalse(file_size_results[path2].passed)
        finally:
            os.unlink(path1)
            os.unlink(path2)


if __name__ == "__main__":
    unittest.main()
