"""Material validation rules.

Rules:
    MaterialSlotCountRule: Validates that materials don't exceed configured slot count.
    MaterialComplexityRule: Flags materials using Translucent or Additive blend modes as overdraw risk indicators.
    MaxTranslucentMaterialsRule: Checks total count of translucent materials in a level against config limit.

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gt.runtime import HostType

from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult

if TYPE_CHECKING:
    from ..config import Config

logger = logging.getLogger(__name__)


def _getMaterialBlendMode(asset) -> str:
    """Return a material blend mode name using supported Unreal access patterns.

    Args:
        asset: An unreal.Material asset object.

    Returns:
        The blend mode string (e.g., "TRANSLUCENT", "ADDITIVE", "OPAQUE").

    """
    try:
        return str(asset.get_editor_property("blend_mode")).upper()
    except Exception:  # noqa: BLE001 - Unreal bridge safety
        return str(asset.blend_mode).upper()


@registry.register
class MaterialSlotCountRule(AbstractRule):
    """Validates that materials don't exceed configured slot count.

    Attributes:
        name: Rule identifier ``"material_slot_count"``.
        category: Rule category ``"material"``.
        severity: :attr:`Severity.WARNING`.

    """

    name = "material_slot_count"
    category = "material"
    severity = Severity.WARNING
    context = HostType.UNREAL  # Only runs in Unreal

    def __init__(self, config: Config, context: HostType | None = None) -> None:
        super().__init__(config)
        self.context = context or HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the material slot count for the given asset.

        Args:
            asset_path: Unreal content path of the Material asset to inspect.

        Returns:
            A :class:`ValidationResult` describing the check outcome.

        """
        try:
            import unreal as _ue  # noqa: PLC0415 - deferred to avoid top-level ImportError

            from ..env import loadUnrealAsset

            asset = loadUnrealAsset(asset_path)
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")

        if not isinstance(asset, _ue.Material):
            return self._makeSkipped(
                asset_path,
                f"MaterialSlotCountRule applies to Material assets only (got {type(asset).__name__}).",
            )

        try:
            max_slots = self.config.get("max_material_slots", 4)
            actual_slots = len(asset.material_dependencies) if hasattr(asset, "material_dependencies") else 0

            if actual_slots > max_slots:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=(
                        f"Material uses {actual_slots} material dependencies - exceeds limit of {max_slots}."
                    ),
                    fix_hint=f"Reduce the number of material references to {max_slots} or fewer.",
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Material uses {actual_slots} material dependencies - within limit of {max_slots}."
                ),
            )
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")


@registry.register
class MaterialComplexityRule(AbstractRule):
    """Flags materials likely to cause overdraw using blend mode heuristics.

    Heuristics checked (inside Unreal - full material inspection):

    1. Translucent or Additive blend mode.

    Attributes:
        name: Rule identifier ``"material_complexity"``.
        category: Rule category ``"material"``.
        severity: :attr:`Severity.INFO`.

    """

    name = "material_complexity"
    category = "material"
    severity = Severity.INFO
    context = HostType.UNREAL  # Only runs in Unreal

    def __init__(self, config: Config, context: HostType | None = None) -> None:
        super().__init__(config)
        self.context = context or HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        """Check *asset_path* for heuristic overdraw risk indicators.

        Heuristics checked (inside Unreal - full material inspection):

        1. Translucent or Additive blend mode.

        Args:
            asset_path: Unreal content path of the Material asset to inspect.

        Returns:
            A :class:`ValidationResult` describing the check outcome.

        """
        if not self.isEnabled():
            return self._makeSkipped(asset_path, "Rule disabled via config.")

        try:
            import unreal as _ue  # noqa: PLC0415 - deferred to avoid top-level ImportError

            from ..env import loadUnrealAsset

            asset = loadUnrealAsset(asset_path)
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")

        if not isinstance(asset, _ue.Material):
            return self._makeSkipped(
                asset_path,
                "MaterialComplexityRule applies to Material assets only.",
            )

        try:
            blend_mode = _getMaterialBlendMode(asset)
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(
                asset_path,
                f"Could not read material blend mode: {exc}",
            )

        is_translucent = "TRANSLUCENT" in blend_mode
        is_additive = "ADDITIVE" in blend_mode

        indicators = []
        if is_translucent:
            indicators.append("Translucent blend mode")
        if is_additive:
            indicators.append("Additive blend mode")

        if indicators:
            return self._makeResult(
                asset_path,
                passed=False,
                message=f"Overdraw risk indicators: {'; '.join(indicators)}.",
                fix_hint=(
                    "Profile with r.ShowFlag.ShaderComplexity 1 in the editor "
                    "to verify actual overdraw."
                ),
                asset_class="Material",
            )

        return self._makeResult(
            asset_path,
            passed=True,
            message="No overdraw risk indicators detected.",
            asset_class="Material",
        )


@registry.register
class MaxTranslucentMaterialsRule(AbstractRule):
    """Checks total count of translucent materials in a level against config limit.

    This rule validates at the package/level scope - it iterates through all
    assets in the given Unreal package path and counts how many use
    Translucent or Additive blend modes.  If the total exceeds the configured
    maximum, the result fails with the excess count reported.

    Attributes:
        name: Rule identifier ``"max_translucent_materials"``.
        category: Rule category ``"material"``.
        severity: :attr:`Severity.WARNING`.

    """

    name = "max_translucent_materials"
    category = "material"
    severity = Severity.WARNING
    context = HostType.UNREAL  # Only runs in Unreal

    def __init__(self, config: Config, context: HostType | None = None) -> None:
        super().__init__(config)
        self.context = context or HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the total translucent material count for a level/package.

        Args:
            asset_path: Unreal content path of the package (e.g., ``"/Game/MyLevel"``).

        Returns:
            A :class:`ValidationResult` describing whether the level stays within
            the configured maximum number of translucent materials.

        """
        if not self.isEnabled():
            return self._makeSkipped(asset_path, "Rule disabled via config.")

        try:
            import unreal as _ue  # noqa: PLC0415 - deferred to avoid top-level ImportError

            from ..env import loadUnrealAsset

            asset = loadUnrealAsset(asset_path)
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")

        if not isinstance(asset, _ue.Package):
            return self._makeSkipped(
                asset_path,
                "MaxTranslucentMaterialsRule applies to Package assets only.",
            )

        try:
            max_limit = self.config.get("max_translucent_materials", 2)
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Config error: {exc}")

        try:
            all_assets = _ue.EditorAssetLibrary.load_assets(asset_path)
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(
                asset_path,
                f"Failed to load package assets: {exc}",
            )

        translucent_count = 0
        for loaded_asset in all_assets:
            if not isinstance(loaded_asset, _ue.Material):
                continue
            try:
                blend_mode = _getMaterialBlendMode(loaded_asset)
            except Exception:  # noqa: BLE001 - Unreal bridge safety
                continue

            if "TRANSLUCENT" in blend_mode or "ADDITIVE" in blend_mode:
                translucent_count += 1

        if translucent_count > max_limit:
            return self._makeResult(
                asset_path,
                passed=False,
                message=(
                    f"{translucent_count} translucent materials found - exceeds limit of {max_limit}."
                ),
                fix_hint=(
                    f"Reduce the number of translucent/additive materials "
                    f"in this package to {max_limit} or fewer."
                ),
            )

        return self._makeResult(
            asset_path,
            passed=True,
            message=(
                f"{translucent_count} translucent materials found - within limit of {max_limit}."
            ),
        )
