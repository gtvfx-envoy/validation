"""AnimSequence validation rules.

Rules:
    AnimSequenceFrameCountRule: Checks animation sequences for excessive frame counts.
    AnimSequenceDurationLimitRule: Validates animation duration doesn't exceed thresholds.

"""

from __future__ import annotations

import logging

from gt.runtime import HostType

from ..env import loadUnrealAsset
from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult

logger = logging.getLogger(__name__)


@registry.register
class AnimSequenceFrameCountRule(AbstractRule):
    """Checks animation sequences for excessive frame counts.

    Excessive frame counts indicate unnecessarily long animations — this rule
    flags them for review to ensure they meet production requirements.

    Attributes:
        name: Rule identifier ``"anim_sequence_frame_count"``.
        category: Rule category ``"anim_sequence"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine host (HostType.UNREAL).

    """

    name = "anim_sequence_frame_count"
    category = "anim_sequence"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the frame count of the given AnimSequence asset.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the frame count is within limits.

        """
        try:
            asset = loadUnrealAsset(asset_path)
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")
        import unreal  # noqa: PLC0415 - deferred Unreal import

        if not isinstance(asset, unreal.AnimSequence):
            return self._makeSkipped(
                asset_path, f"Not an AnimSequence (got {type(asset).__name__})."
            )

        try:
            max_frames = self.config.get("max_anim_sequence_frame_count", 1800)

            # Access frame count via Unreal API
            num_frames = getattr(asset, "num_frames", None) or getattr(asset, "frames", None)
            if num_frames is None:
                try:
                    num_frames = asset.get_editor_property(
                        "num_frames"
                    ) or asset.get_editor_property("frame_count")
                except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
                    return self._makeSkipped(asset_path, f"Could not read frame count: {exc}")

            if num_frames is None or (isinstance(num_frames, int) and num_frames <= 0):
                # Fallback: estimate from animation length
                try:
                    anim_length = getattr(asset, "anim_length", 1.0)
                    fps = 30.0  # Default FPS
                    num_frames = max(1, int(round(anim_length * fps)))
                except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
                    return self._makeSkipped(asset_path, f"Could not estimate frame count: {exc}")

            if num_frames > max_frames:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=(
                        f"Animation sequence has {num_frames} frames — exceeds maximum of "
                        f"{max_frames}. This may indicate an unnecessarily long animation."
                    ),
                    asset_class="AnimSequence",
                    fix_hint=f"Trim the animation to reduce frame count to {max_frames} or fewer.",
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Animation sequence has {num_frames} frames — within limit of {max_frames}."
                ),
                asset_class="AnimSequence",
            )
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")


@registry.register
class AnimSequenceDurationLimitRule(AbstractRule):
    """Validates animation duration doesn't exceed thresholds.

    Animations exceeding 60 seconds may cause pipeline issues — this rule
    flags them for review to ensure they meet production requirements.

    Attributes:
        name: Rule identifier ``"anim_sequence_duration_limit"``.
        category: Rule category ``"anim_sequence"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine host (HostType.UNREAL).

    """

    name = "anim_sequence_duration_limit"
    category = "anim_sequence"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the duration of the given AnimSequence asset.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the animation duration is within limits.

        """
        try:
            asset = loadUnrealAsset(asset_path)
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")
        import unreal  # noqa: PLC0415 - deferred Unreal import

        if not isinstance(asset, unreal.AnimSequence):
            return self._makeSkipped(
                asset_path, f"Not an AnimSequence (got {type(asset).__name__})."
            )

        try:
            max_duration = self.config.get("max_anim_sequence_duration_seconds", 60.0)

            # Access animation duration via Unreal API
            anim_length = getattr(asset, "anim_length", None) or getattr(asset, "duration", None)
            if anim_length is None:
                try:
                    anim_length = asset.get_editor_property(
                        "anim_length"
                    ) or asset.get_editor_property("duration")
                except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
                    return self._makeSkipped(
                        asset_path, f"Could not read animation duration: {exc}"
                    )

            if anim_length is None or (isinstance(anim_length, float) and anim_length <= 0):
                # Fallback: estimate from frame count
                try:
                    num_frames = getattr(asset, "num_frames", 180)
                    fps = 30.0  # Default FPS
                    anim_length = max(0.1, num_frames / fps)
                except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
                    return self._makeSkipped(
                        asset_path, f"Could not estimate animation duration: {exc}"
                    )

            if anim_length > max_duration:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=(
                        f"Animation sequence has duration {anim_length:.1f}s — exceeds maximum of "
                        f"{max_duration}s. This may cause pipeline issues."
                    ),
                    asset_class="AnimSequence",
                    fix_hint=f"Trim or loop the animation to fit within {max_duration} seconds.",
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Animation sequence has duration {anim_length:.1f}s — within limit of "
                    f"{max_duration}s."
                ),
                asset_class="AnimSequence",
            )
        except Exception as exc:  # noqa: BLE001 - Unreal bridge safety
            return self._makeSkipped(asset_path, f"Validation error: {exc}")
