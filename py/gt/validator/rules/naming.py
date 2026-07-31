"""Asset naming convention validation rules.

Rules:
    NamingConventionRule: Validates asset filenames match the configured naming pattern.
    PrefixConventionRule: Validates assets have the correct prefix for their extension.
    FilenameLengthRule: Validates asset filenames do not exceed the configured length.

"""

from __future__ import annotations

import os
import re

from gt.runtime import HostType

from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult


@registry.register
class NamingConventionRule(AbstractRule):
    """Validates that asset filenames match the configured naming pattern.

    Attributes:
        name: Rule identifier ``"naming_convention"``.
        category: Rule category ``"naming"``.
        severity: :attr:`Severity.ERROR`.
        context: Works on any host (STANDALONE).

    """

    name = "naming_convention"
    category = "naming"
    severity = Severity.ERROR
    context = HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the naming convention for the given asset.

        Args:
            asset_path: Filesystem path or Unreal content-browser path of the asset.

        Returns:
            A :class:`ValidationResult` indicating whether the asset name matches
            the configured pattern.

        """
        # Use context to collect metadata when available.
        try:
            meta = (
                self._validation_context.collect(asset_path)
                if self._validation_context is not None
                else None
            )
        except (AttributeError, TypeError):
            meta = None

        if meta is not None:
            stem = meta.name or os.path.basename(asset_path).split('.')[0]
        elif asset_path.startswith("/Game/") or (
            asset_path.startswith("/") and not os.path.exists(asset_path)
        ):
            # Unreal path — name is the last component (no extension)
            stem = asset_path.rstrip('/').split('/')[-1]
        else:
            filename = os.path.basename(asset_path)
            stem, _ = os.path.splitext(filename)

        pattern: str = self.config.get("naming_pattern", r"^[A-Z][a-zA-Z0-9_]+$")

        if re.match(pattern, stem):
            return self._makeResult(
                asset_path,
                passed=True,
                message=f"Filename '{stem}' matches naming convention.",
            )
        return self._makeResult(
            asset_path,
            passed=False,
            message=f"Filename '{stem}' does not match pattern '{pattern}'.",
            fix_hint=f"Rename to match: {pattern} (e.g., 'SM_MyAsset').",
        )


@registry.register
class PrefixConventionRule(AbstractRule):
    """Validates that assets have the correct prefix for their file extension.

    Attributes:
        name: Rule identifier ``"prefix_convention"``.
        category: Rule category ``"naming"``.
        severity: :attr:`Severity.ERROR`.
        context: Works on any host (STANDALONE).

    """

    name = "prefix_convention"
    category = "naming"
    severity = Severity.ERROR
    context = HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the prefix convention for the given asset.

        Args:
            asset_path: Filesystem path or Unreal content-browser path of the asset.

        Returns:
            A :class:`ValidationResult` indicating whether the file uses the correct
            prefix for its extension.

        """
        # Use context to collect metadata when available.
        try:
            meta = (
                self._validation_context.collect(asset_path)
                if self._validation_context is not None
                else None
            )
        except (AttributeError, TypeError):
            meta = None

        # Compute `filename` unconditionally (used in messages below,
        # regardless of which stem/ext branch runs) — previously this was
        # only assigned in the filesystem-fallback branch, causing an
        # UnboundLocalError whenever a context was supplied, which is the
        # normal case in production (ValidationRunner always injects one).
        filename = os.path.basename(asset_path)

        if meta is not None:
            stem = meta.name or ""
            ext = meta.extension.lower()
        elif asset_path.startswith("/Game/") or (
            asset_path.startswith("/") and not os.path.exists(asset_path)
        ):
            # Unreal path — name is the last component (no extension)
            stem = asset_path.rstrip('/').split('/')[-1]
            ext = ""
        else:
            stem, ext = os.path.splitext(filename)
            ext = ext.lower()

        # Only check prefix requirement if we have an extension (filesystem path)
        required_prefixes: dict = self.config.get("required_prefixes", {})
        for prefix, extensions in required_prefixes.items():
            if ext and ext in extensions:
                if not stem.startswith(prefix):
                    return self._makeResult(
                        asset_path,
                        passed=False,
                        message=(
                            f"File '{filename}' with extension '{ext}' "
                            f"must start with prefix '{prefix}'."
                        ),
                        fix_hint=f"Rename to '{prefix}{stem}{ext}'.",
                    )
                return self._makeResult(
                    asset_path,
                    passed=True,
                    message=f"File '{filename}' has correct prefix '{prefix}'.",
                )

        if meta is not None:
            # If we have metadata from context but no matching prefix rule, still pass
            if stem:
                return self._makeResult(
                    asset_path,
                    passed=True,
                    message=f"No prefix rule configured for extension '{ext}' — skipped.",
                )

        # For Unreal paths without metadata, validate name exists;
        # extension validation happens via ValidExtensionRule elsewhere.
        if stem:
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Asset name '{stem}' is valid (extension validation on Unreal path deferred)."
                ),
            )
        return self._makeResult(
            asset_path,
            passed=False,
            message=f"Unable to extract asset name from Unreal path: {asset_path}.",
            fix_hint="Ensure the path is a valid Unreal content path like '/Game/Assets/MyAsset'.",
        )


@registry.register
class FilenameLengthRule(AbstractRule):
    """Validates that asset filenames do not exceed the configured length limit.

    Attributes:
        name: Rule identifier ``"filename_length"``.
        category: Rule category ``"naming"``.
        severity: :attr:`Severity.WARNING`.
        context: Works on any host (STANDALONE).

    """

    name = "filename_length"
    category = "naming"
    severity = Severity.WARNING
    context = HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the filename length for the given asset.

        Args:
            asset_path: Filesystem or content-browser path of the asset.

        Returns:
            A :class:`ValidationResult` indicating whether the filename length
            is within the configured limit.

        """
        # Use context to collect metadata when available.
        try:
            meta = (
                self._validation_context.collect(asset_path)
                if self._validation_context is not None
                else None
            )
        except (AttributeError, TypeError):
            meta = None

        if meta is not None:
            # meta.name is a stem (no extension, matching UnrealContext's
            # contract) — reconstruct the full filename for a length check
            # that matches real on-disk filename length limits.
            filename = (meta.name or "") + (meta.extension or "")
        else:
            filename = os.path.basename(asset_path)

        max_len: int = self.config.get("max_filename_length", 64)

        if len(filename) > max_len:
            return self._makeResult(
                asset_path,
                passed=False,
                message=(
                    f"Filename '{filename}' is {len(filename)} characters "
                    f"— exceeds limit of {max_len}."
                ),
                fix_hint=f"Shorten the filename to {max_len} characters or fewer.",
            )
        return self._makeResult(
            asset_path,
            passed=True,
            message=f"Filename length {len(filename)} is within limit of {max_len}.",
        )
