"""overdraw.py — Heuristic overdraw detection rule.

True overdraw measurement requires GPU profiling. This rule flags
materials using translucent or additive blend modes because they are
common overdraw risk indicators.
"""

from gt.runtime import HostType

from ..env import HAS_UNREAL
from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult


def _getMaterialBlendMode(asset) -> str:
    """Return a material blend mode name using supported Unreal access patterns."""
    try:
        return str(asset.get_editor_property("blend_mode")).upper()
    except Exception:  # noqa: BLE001 - Unreal bridge safety
        return str(asset.blend_mode).upper()


@registry.register
class OverdrawHeuristicRule(AbstractRule):
    """Flags materials likely to cause overdraw using blend mode heuristics.

    Heuristics checked (inside Unreal — full material inspection):

    1. Translucent or Additive blend mode.

    Attributes:
        name: Rule identifier ``"overdraw_heuristic"``.
        category: Rule category ``"overdraw"``.
        severity: :attr:`Severity.INFO`.
        context: Requires Unreal Engine (HostType.UNREAL).

    """

    name = "overdraw_heuristic"
    category = "overdraw"
    severity = Severity.INFO
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Check *asset_path* for heuristic overdraw risk indicators.

        Heuristics checked (inside Unreal — full material inspection):

        1. Translucent or Additive blend mode.

        Args:
            asset_path: Unreal content path of the Material asset to inspect.

        Returns:
            A :class:`ValidationResult` describing the check outcome.

        """
        if not self.isEnabled():
            return self._makeSkipped(asset_path, "Rule disabled via config.")

        if not HAS_UNREAL:
            return self._makeSkipped(
                asset_path,
                "Full overdraw heuristics require Unreal Editor.",
            )

        import unreal as _ue  # noqa: PLC0415

        try:
            asset = _ue.EditorAssetLibrary.load_asset(asset_path)
        except Exception as exc:  # noqa: BLE001 - Unreal C++ bridge raises undocumented exceptions
            return self._makeSkipped(asset_path, f"Failed to load asset: {exc}")
        if asset is None or not isinstance(asset, _ue.Material):
            return self._makeSkipped(
                asset_path,
                "OverdrawHeuristicRule applies to Material assets only.",
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
