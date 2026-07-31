"""Autodesk Maya :class:`ValidationContext` implementation.

Collects asset metadata via the Maya Python API (``maya.cmds``).
Only usable when running inside Maya.

"""

from __future__ import annotations

import logging
import os

from .base import AssetMetadata, ValidationContext

logger = logging.getLogger(__name__)


def _has_maya() -> bool:
    """Return True if ``maya.cmds`` is importable."""
    try:
        import maya  # noqa: F401
        import maya.cmds  # noqa: F401
        return True
    except ImportError:
        return False


class MayaContext(ValidationContext):
    """Validation context for Autodesk Maya environments.

    Collects asset metadata using ``maya.cmds`` calls such as
    :func:`cmds.fileInfo` and file-system inspection.  Falls back to
    filesystem-only collection when the Maya API is unavailable.

    Args:
        directory: Optional content directory prefix to scope enumeration.
            Defaults to ``""`` (all referenced assets).

    """

    def __init__(self, directory: str = "") -> None:
        """Initialize the Maya context with an optional content directory prefix.

        Args:
            directory: Optional content directory prefix to scope enumeration.
                Defaults to ``""`` (all referenced assets).

        """
        self.directory = directory
        self._available = _has_maya()

    # ── ValidationContext interface ─────────────────────────────────────── #

    def isAvailable(self) -> bool:
        """Return ``True`` only when running inside Maya."""
        return self._available

    def collect(self, asset_path: str) -> AssetMetadata:
        """Collect metadata for a single Maya asset path.

        Args:
            asset_path: Filesystem or scene-relative path of the asset.

        Returns:
            A populated :class:`AssetMetadata` instance.  ``asset_class`` is
            set to the Maya node type when available, otherwise empty.

        """
        name = os.path.basename(asset_path)
        _, ext = os.path.splitext(name)
        size = 0
        if os.path.isfile(asset_path):
            size = os.path.getsize(asset_path)

        asset_class = ""
        if self._available:
            try:
                import maya.cmds as cmds  # type: ignore[import]

                node_type = cmds.nodeType(asset_path, fullyQualifiedName=True)
                if node_type:
                    asset_class = str(node_type)
            except Exception as exc:  # noqa: BLE001 - Maya API safety
                logger.debug("maya.cmds.nodeType failed for '%s': %s", asset_path, exc)

        return AssetMetadata(
            path=asset_path,
            name=name,
            extension=ext.lower(),
            size_bytes=size,
            asset_class=asset_class,
            properties={},
        )

    def __repr__(self) -> str:
        """Return a string representation of the Maya context."""
        return f"MayaContext(available={self._available})"
