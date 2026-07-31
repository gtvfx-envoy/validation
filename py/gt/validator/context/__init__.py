"""ValidationContext adapters for filesystem and host-specific environments.

Provides context implementations for:

- :class:`FilesystemContext` — standalone / CI mode (always available)
- :class:`UnrealContext` — Unreal Engine Editor
- :class:`MayaContext` — Autodesk Maya
- :class:`MaxContext` — Autodesk 3ds Max
- :class:`HoudiniContext` — SideFX Houdini
- :class:`BlenderContext` — Blender
- :class:`KritaContext` — Krita

"""

from .base import AssetMetadata, ValidationContext
from .blender import BlenderContext
from .filesystem import FilesystemContext
from .houdini import HoudiniContext
from .krita import KritaContext
from .max import MaxContext
from .maya import MayaContext
from .unreal import UnrealContext

__all__ = [
    "AssetMetadata",
    "BlenderContext",
    "FilesystemContext",
    "HoudiniContext",
    "KritaContext",
    "MaxContext",
    "MayaContext",
    "UnrealContext",
    "ValidationContext",
]
