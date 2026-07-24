"""audio.py — Validation rules for audio assets.

Rules:
    AudioFileSizeRule      — limit file size for audio files.
    AudioValidExtensionRule — validate audio file extensions.
    AudioFilenameLengthRule — check audio filename length.

These rules apply to common audio formats (.wav, .mp3, .ogg, .aiff) and
run in all host environments (no host-specific metadata required).

"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..context.filesystem import FilesystemContext
from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult

if TYPE_CHECKING:
    from ..config import Config


# Supported audio extensions mapped to their typical max file sizes (MB).
_AUDIO_EXTENSIONS: dict[str, int] = {
    ".wav": 200,
    ".mp3": 50,
    ".ogg": 50,
    ".aiff": 200,
    ".flac": 100,
}


def _is_audio_file(path: str) -> bool:
    """Return True if *path* has a recognized audio file extension.

    Args:
        path: Filesystem path to check.

    Returns:
        ``True`` if the file extension is in :data:`_AUDIO_EXTENSIONS`.

    """
    _, ext = os.path.splitext(path)
    return ext.lower() in _AUDIO_EXTENSIONS


@registry.register
class AudioFileSizeRule(AbstractRule):
    """Validate that audio files do not exceed size limits.

    Each supported audio format has a configured maximum file size (in MB).
    Exceeding the limit can cause memory issues during asset loading and
    increase package sizes unnecessarily.

    Attributes:
        name: Rule identifier ``"audio_file_size"``.
        category: Rule category ``"audio"``.
        severity: :attr:`Severity.ERROR`.
        context: No host requirement — runs in all environments.

    """

    name = "audio_file_size"
    category = "audio"
    severity = Severity.ERROR
    context = None  # type: ignore[assignment]  — no host restriction

    def __init__(self, config: Config, validation_context=None) -> None:
        """Initialize the AudioFileSizeRule.

        Args:
            config (Config): Configuration instance with audio file size limits.
            validation_context: Context for asset metadata collection. Defaults to
                FilesystemContext.

        """
        super().__init__(config)
        self._validation_context = validation_context or FilesystemContext()

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate audio file size against format-specific limits.

        Args:
            asset_path: Filesystem path of the audio file to check.

        Returns:
            A :class:`ValidationResult` indicating pass, fail, or skip.

        """
        if not _is_audio_file(asset_path):
            return self._makeSkipped(asset_path, "Not an audio file (skipping size check).")

        max_size_mb = _AUDIO_EXTENSIONS.get(os.path.splitext(asset_path)[1].lower(), 50)

        try:
            file_size_bytes = os.path.getsize(asset_path)
        except OSError as exc:
            return self._makeSkipped(asset_path, f"Cannot read file size: {exc}")

        file_size_mb = file_size_bytes / (1024 * 1024)

        if file_size_mb <= max_size_mb:
            return ValidationResult(
                asset_path=asset_path,
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                message=(
                    f"Audio file size {file_size_mb:.2f} MB is within limit "
                    f"of {max_size_mb} MB for {os.path.splitext(asset_path)[1]}."
                ),
                passed=True,
            )

        return self._makeResult(
            asset_path=asset_path,
            passed=False,
            message=(
                f"Audio file size {file_size_mb:.2f} MB exceeds limit of "
                f"{max_size_mb} MB for {os.path.splitext(asset_path)[1]}."
            ),
            fix_hint=(
                "Compress or trim the audio file. For .wav files, consider "
                "exporting as .mp3 or .ogg to reduce size."
            ),
        )


@registry.register
class AudioValidExtensionRule(AbstractRule):
    """Validate that audio files use approved extensions.

    Only recognized audio formats are allowed.  Unknown extensions may
    indicate misplaced or incorrectly exported files.

    Attributes:
        name: Rule identifier ``"audio_valid_extension"``.
        category: Rule category ``"audio"``.
        severity: :attr:`Severity.WARNING`.
        context: No host requirement — runs in all environments.

    """

    name = "audio_valid_extension"
    category = "audio"
    severity = Severity.WARNING
    context = None  # type: ignore[assignment]  — no host restriction

    def __init__(self, config: Config, validation_context=None) -> None:
        """Initialize the AudioValidExtensionRule.

        Args:
            config (Config): Configuration instance with audio file size limits.
            validation_context: Context for asset metadata collection. Defaults to
                FilesystemContext.

        """
        super().__init__(config)
        self._validation_context = validation_context or FilesystemContext()

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate that the audio file has an approved extension.

        Args:
            asset_path: Filesystem path of the audio file to check.

        Returns:
            A :class:`ValidationResult` indicating pass, fail, or skip.

        """
        if not _is_audio_file(asset_path):
            return self._makeSkipped(asset_path, "Not an audio file (skipping extension check).")

        ext = os.path.splitext(asset_path)[1].lower()
        approved = list(_AUDIO_EXTENSIONS.keys())

        if ext in approved:
            return ValidationResult(
                asset_path=asset_path,
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                message=f"Extension '{ext}' is in the approved audio format list.",
                passed=True,
            )

        return self._makeResult(
            asset_path=asset_path,
            passed=False,
            message=(
                f"Audio file extension '{ext}' is not in the approved list "
                f"({', '.join(sorted(approved))})."
            ),
            fix_hint="Re-export the audio file using one of the supported formats.",
        )


@registry.register
class AudioFilenameLengthRule(AbstractRule):
    """Validate that audio filenames do not exceed the maximum length.

    Long filenames can cause issues with certain DCC tools and operating
    systems.  The maximum is configurable via ``max_filename_length`` in
    :mod:`gt.validator.config`.

    Attributes:
        name: Rule identifier ``"audio_filename_length"``.
        category: Rule category ``"audio"``.
        severity: :attr:`Severity.WARNING`.
        context: No host requirement — runs in all environments.

    """

    name = "audio_filename_length"
    category = "audio"
    severity = Severity.WARNING
    context = None  # type: ignore[assignment]  — no host restriction

    def __init__(self, config: Config, validation_context=None) -> None:
        """Initialize the AudioFilenameLengthRule.

        Args:
            config (Config): Configuration instance with audio file size limits.
            validation_context: Context for asset metadata collection. Defaults to
                FilesystemContext.

        """
        super().__init__(config)
        self._validation_context = validation_context or FilesystemContext()

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate audio filename length against the configured maximum.

        Args:
            asset_path: Filesystem path of the audio file to check.

        Returns:
            A :class:`ValidationResult` indicating pass, fail, or skip.

        """
        if not _is_audio_file(asset_path):
            return self._makeSkipped(
                asset_path, "Not an audio file (skipping filename length check)."
            )

        max_length = self.config.get("max_filename_length", 64)
        filename = os.path.basename(asset_path)
        name_without_ext = os.path.splitext(filename)[0]
        name_length = len(name_without_ext)

        if name_length <= max_length:
            return ValidationResult(
                asset_path=asset_path,
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                message=(f"Audio filename length {name_length} is within limit of {max_length}."),
                passed=True,
            )

        return self._makeResult(
            asset_path=asset_path,
            passed=False,
            message=(
                f"Audio filename '{filename}' has {name_length} characters "
                f"(without extension), exceeding the limit of {max_length}."
            ),
            fix_hint="Shorten the audio file name to fit within the character limit.",
        )
