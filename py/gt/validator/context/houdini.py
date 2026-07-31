"""SideFX Houdini :class:`ValidationContext` implementation.

Collects asset metadata via the Houdini Python API (``hou``).
Only usable when running inside Houdini.

"""

from __future__ import annotations

import logging
import os

from .base import AssetMetadata, ValidationContext

logger = logging.getLogger(__name__)


def _has_houdini() -> bool:
    """Return True if ``hou`` is importable."""
    try:
        import hou  # noqa: F401
        return True
    except ImportError:
        return False


class HoudiniContext(ValidationContext):
    """Validation context for SideFX Houdini environments.

    Collects asset metadata using ``hou`` calls and file-system inspection.
    Falls back to filesystem-only collection when the Houdini API is
    unavailable.

    Args:
        directory: Optional content directory prefix to scope enumeration.
            Defaults to ``""`` (all referenced assets).

    """

    def __init__(self, directory: str = "") -> None:
        """Initialize the Houdini context with an optional content directory prefix.

        Args:
            directory: Optional content directory prefix to scope enumeration.
                Defaults to ``""`` (all referenced assets).

        """
        self.directory = directory
        self._available = _has_houdini()

    # ── ValidationContext interface ─────────────────────────────────────── #

    def isAvailable(self) -> bool:
        """Return ``True`` only when running inside Houdini."""
        return self._available

    def collect(self, asset_path: str) -> AssetMetadata:
        """Collect metadata for a single Houdini asset path.

        Args:
            asset_path: Filesystem or scene-relative path of the asset.

        Returns:
            A populated :class:`AssetMetadata` instance.  ``asset_class`` is
            set to the node type name when available, otherwise empty.

        """
        name = os.path.basename(asset_path)
        _, ext = os.path.splitext(name)
        size = 0
        if os.path.isfile(asset_path):
            size = os.path.getsize(asset_path)

        asset_class = ""
        if self._available:
            try:
                import hou  # type: ignore[import]

                node = hou.node(asset_path)
                if node is not None:
                    asset_class = str(node.type().name())
            except Exception as exc:  # noqa: BLE001 - Houdini API safety
                logger.debug("hou.node failed for '%s': %s", asset_path, exc)

        return AssetMetadata(
            path=asset_path,
            name=name,
            extension=ext.lower(),
            size_bytes=size,
            asset_class=asset_class,
            properties={},
        )

    def __repr__(self) -> str:
        """Return a string representation of the Houdini context."""
        return f"HoudiniContext(available={self._available})"
