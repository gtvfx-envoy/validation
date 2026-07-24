"""Filesystem-level asset validation rules.

Rules:
    FileSizeRule: Validates that assets do not exceed the configured file size limit.
    ValidExtensionRule: Validates that assets have an approved file extension.

"""

from __future__ import annotations

import os

from gt.runtime import HostType

from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult


@registry.register
class FileSizeRule(AbstractRule):
    """Validates that assets do not exceed the configured file size limit.

    Attributes:
        name: Rule identifier ``"file_size"``.
        category: Rule category ``"filesystem"``.
        severity: :attr:`Severity.ERROR`.
        context: Works on any host (STANDALONE).

    """

    name = "file_size"
    category = "filesystem"
    severity = Severity.ERROR
    context = HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the file size for the given asset.

        Args:
            asset_path: Filesystem path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the file size is within
            the configured limit.  Skipped for non-filesystem paths.

        """
        max_mb: float = self.config.get("max_file_size_mb", 50)

        # Use context to collect metadata instead of direct filesystem access.
        if not os.path.exists(asset_path):
            return self._makeSkipped(
                asset_path,
                "FileSizeRule skipped: not a filesystem path. "
                "File size is managed by Unreal when running inside the Editor.",
            )

        try:
            meta = self._validation_context.collect(asset_path) if self._validation_context is not None else None
        except (AttributeError, TypeError):
            return self._makeSkipped(
                asset_path,
                "FileSizeRule skipped: unable to collect metadata from context.",
            )

        size_mb = meta.sizeMb if meta else 0.0

        if size_mb > max_mb:
            return self._makeResult(
                asset_path,
                passed=False,
                message=f"File size {size_mb:.2f} MB exceeds limit of {max_mb} MB.",
                fix_hint=(
                    f"Reduce asset complexity or compress textures to bring "
                    f"file size below {max_mb} MB."
                ),
            )
        return self._makeResult(
            asset_path,
            passed=True,
            message=f"File size {size_mb:.2f} MB is within limit of {max_mb} MB.",
        )


@registry.register
class ValidExtensionRule(AbstractRule):
    """Validates that assets have an approved file extension.

    Attributes:
        name: Rule identifier ``"valid_extension"``.
        category: Rule category ``"filesystem"``.
        severity: :attr:`Severity.ERROR`.
        context: Works on any host (STANDALONE).

    """

    name = "valid_extension"
    category = "filesystem"
    severity = Severity.ERROR
    context = HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the file extension for the given asset.

        Args:
            asset_path: Filesystem path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the extension is in the
            approved list.  Skipped for non-filesystem paths.

        """
        # Use context to collect metadata instead of direct filesystem access.
        if not os.path.exists(asset_path):
            return self._makeSkipped(
                asset_path,
                "ValidExtensionRule skipped: not a filesystem path. "
                "Asset type is available via AssetData.asset_class in Unreal.",
            )

        try:
            meta = self._validation_context.collect(asset_path) if self._validation_context is not None else None
        except (AttributeError, TypeError):
            return self._makeSkipped(
                asset_path,
                "ValidExtensionRule skipped: unable to collect metadata from context.",
            )

        ext = meta.extension if meta else ""

        valid_exts: list = self.config.get(
            "valid_extensions", [".uasset", ".fbx", ".png", ".tga", ".exr"]
        )

        if ext in valid_exts:
            return self._makeResult(
                asset_path,
                passed=True,
                message=f"Extension '{ext}' is in the approved list.",
            )
        return self._makeResult(
            asset_path,
            passed=False,
            message=f"Extension '{ext}' is not in approved list: {valid_exts}.",
            fix_hint=f"Convert or remove this file. Approved types: {', '.join(valid_exts)}.",
        )
