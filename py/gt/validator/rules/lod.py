"""Level of Detail (LOD) validation rules.

Rules:
    LODCountRule: Validates the LOD count for StaticMesh and SkeletalMesh assets.
    LODScreenSizeRatioRule: Validates that LOD screen size thresholds decrease monotonically.

"""

from __future__ import annotations

from gt.runtime import HostType

from ..env import loadUnrealAsset
from ..errors import UnrealAPIError
from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult


def _getSkeletalMeshLodCount(asset, unreal_module) -> int:
    """Return SkeletalMesh LOD count using supported editor APIs.

    Args:
        asset: Loaded ``unreal.SkeletalMesh`` asset.
        unreal_module: Imported ``unreal`` module.

    Returns:
        LOD count for the skeletal mesh.

    Raises:
        RuntimeError: If no supported API can provide the LOD count.

    """
    if hasattr(unreal_module, "SkeletalMeshEditorSubsystem"):
        try:
            skeletal_mesh_editor = unreal_module.get_editor_subsystem(
                unreal_module.SkeletalMeshEditorSubsystem
            )
            if skeletal_mesh_editor is not None:
                return int(skeletal_mesh_editor.get_lod_count(asset))
        except Exception:  # noqa: BLE001 - Unreal bridge safety
            pass

    if hasattr(unreal_module, "EditorSkeletalMeshLibrary"):
        try:
            return int(unreal_module.EditorSkeletalMeshLibrary.get_lod_count(asset))
        except Exception:  # noqa: BLE001 - Unreal bridge safety
            pass

    try:
        lod_info = asset.get_editor_property("lod_info")
    except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
        raise RuntimeError("Could not read SkeletalMesh LOD data.") from exc

    if lod_info is None:
        raise RuntimeError("Could not read SkeletalMesh LOD data.")

    return len(lod_info)


@registry.register
class LODCountRule(AbstractRule):
    """Validates the LOD count for StaticMesh and SkeletalMesh assets.

    Attributes:
        name: Rule identifier ``"lod_count"``.
        category: Rule category ``"lod"``.
        severity: :attr:`Severity.ERROR`.
        context: Requires Unreal Engine (HostType.UNREAL).

    """

    name = "lod_count"
    category = "lod"
    severity = Severity.ERROR
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the LOD count of the given mesh asset.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the LOD count is within
            the configured minimum and maximum bounds.

        """
        try:
            asset = loadUnrealAsset(asset_path)
        except UnrealAPIError as exc:
            return self._makeSkipped(asset_path, str(exc))
        import unreal  # noqa: PLC0415 - deferred Unreal import

        if not isinstance(asset, (unreal.StaticMesh, unreal.SkeletalMesh)):
            return self._makeSkipped(
                asset_path,
                "LOD count check only applies to "
                f"StaticMesh/SkeletalMesh (got {type(asset).__name__}).",
            )

        try:
            if isinstance(asset, unreal.StaticMesh):
                lod_count = asset.get_num_lods()
            else:
                lod_count = _getSkeletalMeshLodCount(asset, unreal)
            min_lods: int = self.config.get("min_lod_count", 1)
            max_lods: int = self.config.get("max_lod_count", 8)
            asset_class = type(asset).__name__

            if lod_count < min_lods:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=f"{asset_class} has {lod_count} LOD(s) — minimum is {min_lods}.",
                    asset_class=asset_class,
                    fix_hint=f"Add at least {min_lods - lod_count} more LOD level(s).",
                )
            if lod_count > max_lods:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=f"{asset_class} has {lod_count} LOD(s) — maximum is {max_lods}.",
                    asset_class=asset_class,
                    fix_hint=f"Remove {lod_count - max_lods} LOD level(s).",
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=f"{asset_class} has {lod_count} LOD(s) — within [{min_lods}, {max_lods}].",
                asset_class=asset_class,
            )
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")


@registry.register
class LODScreenSizeRatioRule(AbstractRule):
    """Validates that LOD screen size thresholds decrease monotonically.

    Attributes:
        name: Rule identifier ``"lod_screen_size_ratio"``.
        category: Rule category ``"lod"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine (HostType.UNREAL).

    """

    name = "lod_screen_size_ratio"
    category = "lod"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate that LOD screen size thresholds decrease monotonically.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether screen size values
            decrease correctly across all LOD levels.

        """
        try:
            asset = loadUnrealAsset(asset_path)
        except UnrealAPIError as exc:
            return self._makeSkipped(asset_path, str(exc))
        import unreal  # noqa: PLC0415 - deferred Unreal import

        if not isinstance(asset, unreal.StaticMesh):
            return self._makeSkipped(
                asset_path,
                f"LOD screen size check only applies to StaticMesh (got {type(asset).__name__}).",
            )

        try:
            lod_count = asset.get_num_lods()
            if lod_count < 2:
                return self._makeResult(
                    asset_path,
                    passed=True,
                    message="Only one LOD — no screen size ratio to validate.",
                    asset_class="StaticMesh",
                )

            screen_sizes = []
            try:
                if hasattr(unreal, "StaticMeshEditorSubsystem"):
                    mesh_editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
                    if mesh_editor is not None:
                        screen_sizes = [
                            float(size) for size in mesh_editor.get_lod_screen_sizes(asset)
                        ]
                if not screen_sizes and hasattr(unreal, "EditorStaticMeshLibrary"):
                    screen_sizes = [
                        float(size)
                        for size in unreal.EditorStaticMeshLibrary.get_lod_screen_sizes(asset)
                    ]
            except Exception:  # noqa: BLE001 - Unreal bridge safety
                return self._makeSkipped(
                    asset_path,
                    "Could not read LOD screen sizes — may require resaving in Editor.",
                )
            if len(screen_sizes) < lod_count:
                return self._makeSkipped(
                    asset_path,
                    "Could not read LOD screen sizes for all LOD levels.",
                )
            screen_sizes = screen_sizes[:lod_count]

            self.config.get("min_lod_screen_size_ratio", 0.5)
            violations = []
            for i in range(1, len(screen_sizes)):
                prev = screen_sizes[i - 1]
                curr = screen_sizes[i]
                if prev <= 0:
                    continue
                # Screen sizes should be strictly decreasing
                if curr >= prev:
                    violations.append(
                        f"LOD{i - 1}({prev:.3f}) -> LOD{i}({curr:.3f}): not decreasing"
                    )

            if violations:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=(
                        f"LOD screen size thresholds not monotonically decreasing: {violations}."
                    ),
                    asset_class="StaticMesh",
                    fix_hint=(
                        "Adjust LOD screen size thresholds in the Static "
                        "Mesh Editor to decrease with each LOD."
                    ),
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=f"LOD screen size thresholds decrease correctly across {lod_count} LODs.",
                asset_class="StaticMesh",
            )
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")
