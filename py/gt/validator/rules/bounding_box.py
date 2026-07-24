"""Bounding box validation rules.

Rules:
    BoundingBoxExtentRule: Validates the world bounding box extent is within the limit.
    BoundingBoxOriginRule: Validates the pivot offset from the world origin is within the limit.

"""

from __future__ import annotations

from gt.runtime import HostType

from ..context.base import AssetMetadata
from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult


def _readMeshBoundsMetrics(metadata: AssetMetadata) -> tuple[float, float, float, float, float, float]:
    """Return mesh extents and center components from metadata.

    Args:
        metadata: AssetMetadata containing bounds information.

    Returns:
        Tuple in the form ``(extent_x, extent_y, extent_z, center_x, center_y, center_z)``.

    """
    # Extract bounds data from metadata properties.
    bounds_extent_x = metadata.properties.get("bounds_extent_x", 0)
    bounds_extent_y = metadata.properties.get("bounds_extent_y", 0)
    bounds_extent_z = metadata.properties.get("bounds_extent_z", 0)

    extent_x = abs(bounds_extent_x)
    extent_y = abs(bounds_extent_y)
    extent_z = abs(bounds_extent_z)

    origin_x = metadata.properties.get("origin_x", 0)
    origin_y = metadata.properties.get("origin_y", 0)
    origin_z = metadata.properties.get("origin_z", 0)

    return extent_x, extent_y, extent_z, origin_x, origin_y, origin_z


@registry.register
class BoundingBoxExtentRule(AbstractRule):
    """Validates that a mesh's bounding box extent does not exceed the limit.

    Attributes:
        name: Rule identifier ``"bounding_box_extent"``.
        category: Rule category ``"bounding_box"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine host (HostType.UNREAL) — bounding
            box extent data is an Unreal-only asset concept.

    """

    name = "bounding_box_extent"
    category = "bounding_box"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the bounding box extent of the given mesh asset.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the bounding box extent
            is within the configured limit.

        """
        # Use context abstraction to collect metadata instead of direct Unreal API calls.
        try:
            meta = self._validation_context.collect(asset_path) if self._validation_context is not None else None
        except (AttributeError, TypeError):
            meta = None

        if meta is not None:
            extent_x, extent_y, extent_z, _, _, _ = _readMeshBoundsMetrics(meta)
            max_component = max(extent_x, extent_y, extent_z)
            max_uu: float = self.config.get("max_bounds_extent_uu", 500.0)
            asset_class = meta.asset_class or ""

            if max_component > max_uu:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=(
                        f"Bounding box extent {max_component:.1f} UU exceeds limit {max_uu} UU "
                        f"(X={extent_x:.1f}, Y={extent_y:.1f}, Z={extent_z:.1f})."
                    ),
                    asset_class=asset_class,
                    fix_hint=(
                        "Check mesh scale — may have been imported with incorrect units (cm vs m)."
                    ),
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Bounding box extent {max_component:.1f} UU — within limit of {max_uu} UU."
                ),
                asset_class=asset_class,
            )

        # Fallback: if context cannot provide metadata, skip validation.
        return self._makeSkipped(
            asset_path,
            "Bounding box extent validation requires Unreal Engine host or filesystem access."
        )


@registry.register
class BoundingBoxOriginRule(AbstractRule):
    """Validates that the mesh pivot is close to the world origin.

    A pivot far from the origin causes floating-point precision issues in large worlds.

    Attributes:
        name: Rule identifier ``"bounding_box_origin"``.
        category: Rule category ``"bounding_box"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine host (HostType.UNREAL) — pivot
            offset data is an Unreal-only asset concept.

    """

    name = "bounding_box_origin"
    category = "bounding_box"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate that the mesh pivot is close to the world origin.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the mesh center
            is within the configured offset limit from the world origin.

        """
        # Use context abstraction to collect metadata instead of direct Unreal API calls.
        try:
            meta = self._validation_context.collect(asset_path) if self._validation_context is not None else None
        except (AttributeError, TypeError):
            meta = None

        if meta is not None:
            _, _, _, center_x, center_y, center_z = _readMeshBoundsMetrics(meta)
            offset = (center_x**2 + center_y**2 + center_z**2) ** 0.5
            max_offset: float = self.config.get("max_pivot_offset_uu", 10.0)
            asset_class = meta.asset_class or ""

            if offset > max_offset:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=(
                        f"Mesh center is {offset:.1f} UU from origin "
                        f"(X={center_x:.1f}, Y={center_y:.1f}, Z={center_z:.1f}) — "
                        f"limit is {max_offset} UU."
                    ),
                    asset_class=asset_class,
                    fix_hint=(
                        "Reset the pivot to world origin in your DCC tool before re-importing."
                    ),
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Mesh center is {offset:.1f} UU from origin — within limit of {max_offset} UU."
                ),
                asset_class=asset_class,
            )

        # Fallback: if context cannot provide metadata, skip validation.
        return self._makeSkipped(
            asset_path,
            "Bounding box origin validation requires Unreal Engine host or filesystem access."
        )
