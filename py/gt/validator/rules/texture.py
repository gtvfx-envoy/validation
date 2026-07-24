"""Texture validation rules.

Rules:
    TextureDimensionRule: Validates texture dimensions are power-of-two and within the limit.
    TextureCompressionRule: Validates that textures use appropriate compression settings.
    TextureSampleRule: Validates MIP counts against configured sample limits.

"""

from __future__ import annotations

import logging

from gt.runtime import HostType

from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult

logger = logging.getLogger(__name__)


@registry.register
class TextureDimensionRule(AbstractRule):
    """Validates texture dimensions are power-of-two and within the limit.

    Attributes:
        name: Rule identifier ``"texture_dimension"``.
        category: Rule category ``"texture"``.
        severity: :attr:`Severity.ERROR`.
        context: Works on any host (STANDALONE) for basic dimension checks.

    """

    name = "texture_dimension"
    category = "texture"
    severity = Severity.ERROR
    context = HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the dimensions of the given texture asset.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the texture dimensions
            are power-of-two and within the configured maximum.

        """
        # Use context abstraction to collect metadata instead of direct Unreal API calls.
        try:
            meta = self._validation_context.collect(asset_path) if self._validation_context is not None else None
        except (AttributeError, TypeError):
            meta = None

        if meta is not None:
            # AssetMetadata has no width/height attributes — dimension data
            # (when a context provides it) lives in the `properties` dict,
            # same as bounds/LOD data elsewhere in this framework.
            width = meta.properties.get("width", 0)
            height = meta.properties.get("height", 0)

            if not width or not height:
                return self._makeSkipped(
                    asset_path,
                    "Texture dimension validation requires width/height metadata "
                    "not provided by the current context.",
                )

            max_dim: int = self.config.get("max_texture_dimension", 4096)

            def isPowerOfTwo(n: int) -> bool:
                return n > 0 and (n & (n - 1)) == 0

            if width > max_dim or height > max_dim:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=f"Dimensions {width}x{height} exceed max {max_dim}x{max_dim}.",
                    fix_hint=f"Resize texture to a power-of-two dimension <= {max_dim}px.",
                )
            if not isPowerOfTwo(width) or not isPowerOfTwo(height):
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=f"Dimensions {width}x{height} are not powers of two.",
                    fix_hint="Resize texture dimensions to powers of two (e.g., 512, 1024, 2048).",
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=f"Texture dimensions {width}x{height} are valid.",
            )

        # Fallback: if context cannot provide metadata, skip validation.
        return self._makeSkipped(
            asset_path,
            "Texture dimension validation requires Unreal Engine host or filesystem access."
        )


@registry.register
class TextureCompressionRule(AbstractRule):
    """Validates that textures use an appropriate compression setting.

    Normal maps must use ``TC_Normalmap`` compression.

    Attributes:
        name: Rule identifier ``"texture_compression"``.
        category: Rule category ``"texture"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine host (HostType.UNREAL).

    """

    name = "texture_compression"
    category = "texture"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the compression settings of the given texture asset.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the compression setting
            is appropriate for the detected texture type.

        """
        # Use context abstraction to collect metadata instead of direct Unreal API calls.
        try:
            meta = self._validation_context.collect(asset_path) if self._validation_context is not None else None
        except (AttributeError, TypeError):
            meta = None

        if meta is not None:
            path_str = str(asset_path)
            is_normal_map = (
                "_N." in path_str
                or "_Normal." in path_str
                or "_NRM." in path_str
                or "Normal" in path_str
            )

            # Check compression from metadata if available.
            compression = meta.properties.get("compression_settings")

            if is_normal_map and compression != "TC_Normalmap":
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=(
                        f"Normal map texture uses compression '{compression}' — "
                        f"should use TC_Normalmap."
                    ),
                    fix_hint=(
                        "Set Compression Settings to 'Normalmap (DXT5, BC5 "
                        "on DX11)' in the Texture Editor."
                    ),
                )

            return self._makeResult(
                asset_path,
                passed=True,
                message=f"Texture compression '{compression}' is acceptable.",
            )

        # Fallback: if context cannot provide metadata, skip validation.
        return self._makeSkipped(
            asset_path,
            "Texture compression validation requires Unreal Engine host or filesystem access."
        )


@registry.register
class TextureSampleRule(AbstractRule):
    """Validates MIP counts against configured sample limits.

    Attributes:
        name: Rule identifier ``"texture_samples"``.
        category: Rule category ``"texture"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine host (HostType.UNREAL).

    """

    name = "texture_samples"
    category = "texture"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the MIP/sample count of the given texture.

        Args:
            asset_path: Content-browser path of the Texture2D to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the sample/MIP
            count is within the configured limit.

        """
        # Use context abstraction to collect metadata instead of direct Unreal API calls.
        try:
            meta = self._validation_context.collect(asset_path) if self._validation_context is not None else None
        except (AttributeError, TypeError):
            meta = None

        if meta is not None:
            max_samples = self.config.get("max_texture_samples", 16)

            # Get MIP count from metadata or estimate from resolution.
            num_mips = meta.properties.get("mip_count")

            if num_mips is None or (isinstance(num_mips, int) and num_mips <= 0):
                # Estimate from resolution. `width` lives in `properties` (no
                # `.width` attribute exists on AssetMetadata). `min(x)` on a
                # single non-iterable int previously raised TypeError — the
                # min() wrapper was a no-op bug and has been removed.
                width = meta.properties.get("width", 0)
                if not width:
                    return self._makeSkipped(
                        asset_path,
                        "Texture MIP count validation requires mip_count or "
                        "width metadata not provided by the current context.",
                    )
                max_dim = self.config.get("max_texture_dimension", 4096)
                estimated_mips = max(1, int((width / max_dim).bit_length())) + 1
                num_mips = estimated_mips

            if num_mips > max_samples:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=(
                        f"Texture has {num_mips} sample(s) — exceeds limit of {max_samples}."
                    ),
                    fix_hint=f"Reduce MIP levels to {max_samples} or fewer.",
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Texture has {num_mips} sample(s) — within limit of {max_samples}."
                ),
            )

        # Fallback: if context cannot provide metadata, skip validation.
        return self._makeSkipped(
            asset_path,
            "Texture MIP count validation requires Unreal Engine host or filesystem access."
        )
