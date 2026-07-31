"""Krita :class:`ValidationContext` implementation.

Collects asset metadata via the Krita Python API (``krita``).
Only usable when running inside Krita.

"""

from __future__ import annotations

import logging
import os

from .base import AssetMetadata, ValidationContext

logger = logging.getLogger(__name__)


def _has_krita() -> bool:
    """Return True if ``krita`` is importable."""
    try:
        import krita  # noqa: F401
        return True
    except ImportError:
        return False


class KritaContext(ValidationContext):
    """Validation context for Krita environments.

    Collects asset metadata using ``krita`` calls and file-system inspection.
    Falls back to filesystem-only collection when the Krita API is unavailable.

    Args:
        directory: Optional content directory prefix to scope enumeration.
            Defaults to ``""`` (all referenced assets).

    """

    def __init__(self, directory: str = "") -> None:
        """Initialize the Krita context with an optional content directory prefix.

        Args:
            directory: Optional content directory prefix to scope enumeration.
                Defaults to ``""`` (all referenced assets).

        """
        self.directory = directory
        self._available = _has_krita()

    # ── ValidationContext interface ─────────────────────────────────────── #

    def isAvailable(self) -> bool:
        """Return ``True`` only when running inside Krita."""
        return self._available

    def collect(self, asset_path: str) -> AssetMetadata:
        """Collect metadata for a single Krita asset path.

        Args:
            asset_path: Filesystem or scene-relative path of the asset.

        Returns:
            A populated :class:`AssetMetadata` instance.  ``asset_class`` is
            set to the document type when available, otherwise empty.

        """
        name = os.path.basename(asset_path)
        _, ext = os.path.splitext(name)
        size = 0
        if os.path.isfile(asset_path):
            size = os.path.getsize(asset_path)

        asset_class = ""
        if self._available:
            try:
                import krita  # type: ignore[import]

                doc = krita.instance().activeDocument()
                if doc is not None and doc.fileName() == asset_path:
                    asset_class = "Document"
            except Exception as exc:  # noqa: BLE001 - Krita API safety
                logger.debug("krita failed for '%s': %s", asset_path, exc)

        return AssetMetadata(
            path=asset_path,
            name=name,
            extension=ext.lower(),
            size_bytes=size,
            asset_class=asset_class,
            properties={},
        )

    def __repr__(self) -> str:
        """Return a string representation of the Krita context."""
        return f"KritaContext(available={self._available})"
