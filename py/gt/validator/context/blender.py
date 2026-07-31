"""Blender :class:`ValidationContext` implementation.

Collects asset metadata via the Blender Python API (``bpy``).
Only usable when running inside Blender.

"""

from __future__ import annotations

import logging
import os

from .base import AssetMetadata, ValidationContext

logger = logging.getLogger(__name__)


def _has_blender() -> bool:
    """Return True if ``bpy`` is importable."""
    try:
        import bpy  # noqa: F401
        return True
    except ImportError:
        return False


class BlenderContext(ValidationContext):
    """Validation context for Blender environments.

    Collects asset metadata using ``bpy`` calls and file-system inspection.
    Falls back to filesystem-only collection when the Blender API is
    unavailable.

    Args:
        directory: Optional content directory prefix to scope enumeration.
            Defaults to ``""`` (all referenced assets).

    """

    def __init__(self, directory: str = "") -> None:
        """Initialize the Blender context with an optional content directory prefix.

        Args:
            directory: Optional content directory prefix to scope enumeration.
                Defaults to ``""`` (all referenced assets).

        """
        self.directory = directory
        self._available = _has_blender()

    # ── ValidationContext interface ─────────────────────────────────────── #

    def isAvailable(self) -> bool:
        """Return ``True`` only when running inside Blender."""
        return self._available

    def collect(self, asset_path: str) -> AssetMetadata:
        """Collect metadata for a single Blender asset path.

        Args:
            asset_path: Filesystem or scene-relative path of the asset.

        Returns:
            A populated :class:`AssetMetadata` instance.  ``asset_class`` is
            set to the object type name when available, otherwise empty.

        """
        name = os.path.basename(asset_path)
        _, ext = os.path.splitext(name)
        size = 0
        if os.path.isfile(asset_path):
            size = os.path.getsize(asset_path)

        asset_class = ""
        if self._available:
            try:
                import bpy  # type: ignore[import]

                obj = bpy.data.objects.get(os.path.basename(asset_path))
                if obj is not None:
                    asset_class = str(obj.type)
            except Exception as exc:  # noqa: BLE001 - Blender API safety
                logger.debug("bpy failed for '%s': %s", asset_path, exc)

        return AssetMetadata(
            path=asset_path,
            name=name,
            extension=ext.lower(),
            size_bytes=size,
            asset_class=asset_class,
            properties={},
        )

    def __repr__(self) -> str:
        """Return a string representation of the Blender context."""
        return f"BlenderContext(available={self._available})"
