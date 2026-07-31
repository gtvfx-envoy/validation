"""Autodesk 3ds Max :class:`ValidationContext` implementation.

Collects asset metadata via the 3ds Max Python API (``pymxs.runtime``).
Only usable when running inside 3ds Max.

"""

from __future__ import annotations

import logging
import os

from .base import AssetMetadata, ValidationContext

logger = logging.getLogger(__name__)


def _has_max() -> bool:
    """Return True if ``pymxs.runtime`` is importable."""
    try:
        import pymxs  # noqa: F401
        import pymxs.runtime  # noqa: F401
        return True
    except ImportError:
        return False


class MaxContext(ValidationContext):
    """Validation context for Autodesk 3ds Max environments.

    Collects asset metadata using ``pymxs.runtime`` calls and file-system
    inspection.  Falls back to filesystem-only collection when the 3ds Max
    API is unavailable.

    Args:
        directory: Optional content directory prefix to scope enumeration.
            Defaults to ``""`` (all referenced assets).

    """

    def __init__(self, directory: str = "") -> None:
        """Initialize the Max context with an optional content directory prefix.

        Args:
            directory: Optional content directory prefix to scope enumeration.
                Defaults to ``""`` (all referenced assets).

        """
        self.directory = directory
        self._available = _has_max()

    # ── ValidationContext interface ─────────────────────────────────────── #

    def isAvailable(self) -> bool:
        """Return ``True`` only when running inside 3ds Max."""
        return self._available

    def collect(self, asset_path: str) -> AssetMetadata:
        """Collect metadata for a single 3ds Max asset path.

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
                import pymxs.runtime as mxs  # type: ignore[import]

                node = mxs.getNodeByHandle(asset_path)
                if node is not None:
                    asset_class = str(node.classType.name)
            except Exception as exc:  # noqa: BLE001 - Max API safety
                logger.debug("pymxs.runtime failed for '%s': %s", asset_path, exc)

        return AssetMetadata(
            path=asset_path,
            name=name,
            extension=ext.lower(),
            size_bytes=size,
            asset_class=asset_class,
            properties={},
        )

    def __repr__(self) -> str:
        """Return a string representation of the Max context."""
        return f"MaxContext(available={self._available})"
