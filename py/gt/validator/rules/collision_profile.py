"""CollisionProfile validation rules.

Rules:
    CollisionProfileValidatorRule: Validates collision profile configuration for complexity issues.
    CollisionLODTransitionSmoothnessRule: Validates LOD transition smoothness between mesh levels.

"""

from __future__ import annotations

import logging

from gt.runtime import HostType

from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult

logger = logging.getLogger(__name__)


@registry.register
class CollisionProfileValidatorRule(AbstractRule):
    """Validates collision profile configuration for complexity issues.

    Collision profiles with excessive complexity can cause performance issues — this rule
    flags them for review to ensure they meet production requirements.

    Attributes:
        name: Rule identifier ``"collision_profile_validator"``.
        category: Rule category ``"collision_profile"``.
        severity: :attr:`Severity.ERROR`.
        context: Requires Unreal Engine host (HostType.UNREAL) — collision
            profile data is an Unreal-only asset concept.

    """

    name = "collision_profile_validator"
    category = "collision_profile"
    severity = Severity.ERROR
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate the collision profile configuration of the given asset.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether the collision profile is valid.

        """
        # Use context abstraction to collect metadata instead of direct Unreal API calls.
        try:
            meta = (
                self._validation_context.collect(asset_path)
                if self._validation_context is not None
                else None
            )
        except (AttributeError, TypeError):
            meta = None

        if meta is not None:
            max_complexity = self.config.get("max_collision_profile_complexity", 32)

            complexity = meta.properties.get("collision_profile_complexity", 0)

            if complexity > max_complexity:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message=(
                        f"Collision profile has complexity {complexity} — exceeds maximum of "
                        f"{max_complexity}. This may cause performance issues."
                    ),
                    asset_class="StaticMesh",
                    fix_hint=f"Simplify collision shape to reduce complexity to {max_complexity}.",
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Collision profile has complexity {complexity} — within limit of "
                    f"{max_complexity}."
                ),
                asset_class="StaticMesh",
            )

        # Fallback: if context cannot provide metadata, skip validation.
        return self._makeSkipped(
            asset_path,
            "Collision profile validation requires Unreal Engine host or filesystem access.",
        )


@registry.register
class CollisionLODTransitionSmoothnessRule(AbstractRule):
    """Verifies LOD transitions between mesh levels are smooth (no sudden scale jumps).

    Sudden scale jumps between LOD levels can cause visual artifacts — this rule
    flags them for review to ensure they meet production requirements.

    Attributes:
        name: Rule identifier ``"collision_lod_transition_smoothness"``.
        category: Rule category ``"collision_profile"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine host (HostType.UNREAL) — LOD
            transition data is an Unreal-only asset concept.

    """

    name = "collision_lod_transition_smoothness"
    category = "collision_profile"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate LOD transition smoothness for the given mesh asset.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether LOD transitions are smooth.

        """
        # Use context abstraction to collect metadata instead of direct Unreal API calls.
        try:
            meta = (
                self._validation_context.collect(asset_path)
                if self._validation_context is not None
                else None
            )
        except (AttributeError, TypeError):
            meta = None

        if meta is not None:
            max_scale_jump = self.config.get("max_lod_scale_jump", 0.5)

            lod_scales = meta.properties.get("lod_scales", [])

            if isinstance(lod_scales, list) and len(lod_scales) > 1:
                max_jump = 0.0
                for i in range(len(lod_scales) - 1):
                    jump = (
                        abs(lod_scales[i] - lod_scales[i + 1])
                        / (lod_scales[i] + lod_scales[i + 1])
                        * 2
                    )
                    max_jump = max(max_jump, jump)

                if max_jump > max_scale_jump:
                    return self._makeResult(
                        asset_path,
                        passed=False,
                        message=(
                            f"LOD transitions have a max scale jump of {max_jump:.3f} — exceeds "
                            f"limit of {max_scale_jump}. This may cause visual artifacts."
                        ),
                        asset_class="StaticMesh",
                        fix_hint=f"Adjust LOD scales to ensure no transition exceeds ratio of "
                                  f"{max_scale_jump}.",
                    )
                return self._makeResult(
                    asset_path,
                    passed=True,
                    message=(
                        f"LOD transitions have a max scale jump of {max_jump:.3f} — within limit "
                        f"of {max_scale_jump}."
                    ),
                    asset_class="StaticMesh",
                )

            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Only {len(lod_scales) if isinstance(lod_scales, list) else 1} LOD level(s) — "
                    f"no transitions to check."
                ),
                asset_class="StaticMesh",
            )

        # Fallback: if context cannot provide metadata, skip validation.
        return self._makeSkipped(
            asset_path,
            "LOD transition smoothness validation requires Unreal Engine host or "
            "filesystem access."
        )
