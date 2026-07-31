"""niagara.py — Validation rules for Unreal Niagara assets.

Rules:
    NiagaraFixedBoundsRule       — require fixed bounds on Niagara systems.
    NiagaraEmitterCountRule      — limit number of emitters per system.
    NiagaraSpawnRateLimitRule    — limit particle spawn rate.
    NiagaraGPUSimulationRule     — validate GPU simulation settings.

"""

from __future__ import annotations

from gt.runtime import HostType

from ..registry import registry
from .base import AbstractRule, Severity, ValidationResult


@registry.register
class NiagaraFixedBoundsRule(AbstractRule):
    """Validates that Niagara systems have fixed bounds set.

    Dynamic bounds force the engine to recompute bounds every frame, which
    is expensive for large particle systems.

    Attributes:
        name: Rule identifier ``"niagara_fixed_bounds"``.
        category: Rule category ``"niagara"``.
        severity: :attr:`Severity.ERROR`.
        context: Requires Unreal Engine host (HostType.UNREAL) — Niagara
            systems are an Unreal-only asset concept.

    """

    name = "niagara_fixed_bounds"
    category = "niagara"
    severity = Severity.ERROR
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate that fixed bounds are configured on the given Niagara system.

        Args:
            asset_path: Content-browser path of the asset to validate.

        Returns:
            A :class:`ValidationResult` indicating whether fixed bounds are set,
            or a passing result when the check is disabled via config.

        """
        if not self.isEnabled():
            return self._makeResult(
                asset_path,
                passed=True,
                message="Fixed bounds check disabled via config.",
                asset_class="NiagaraSystem",
            )

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
            fixed_bounds = meta.properties.get("fixed_bounds", False)

            if not fixed_bounds:
                return self._makeResult(
                    asset_path,
                    passed=False,
                    message="Niagara system does not have fixed bounds set.",
                    asset_class="NiagaraSystem",
                    fix_hint=(
                        "Enable 'Fixed Bounds' in the Niagara System editor and set "
                        "appropriate values to avoid per-frame bounds calculation."
                    ),
                )
            return self._makeResult(
                asset_path,
                passed=True,
                message="Niagara system has fixed bounds configured.",
                asset_class="NiagaraSystem",
            )

        # Fallback: if context cannot provide metadata, skip validation.
        return self._makeSkipped(
            asset_path,
            "Niagara fixed bounds validation requires Unreal Engine host or filesystem access."
        )


@registry.register
class NiagaraEmitterCountRule(AbstractRule):
    """Validates that Niagara systems do not exceed the emitter count limit.

    Excessive emitters per system degrade performance and increase memory
    usage.  The maximum is configurable via ``max_niagara_emitters`` in
    :mod:`gt.validator.config`.

    Attributes:
        name: Rule identifier ``"niagara_emitter_count"``.
        category: Rule category ``"niagara"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine host (HostType.UNREAL).

    """

    name = "niagara_emitter_count"
    category = "niagara"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate emitter count against the configured maximum.

        Args:
            asset_path: Content-browser path of the Niagara asset to validate.

        Returns:
            A :class:`ValidationResult` indicating pass, fail, or skip.

        """
        if not self.isEnabled():
            return self._makeResult(
                asset_path,
                passed=True,
                message="Emitter count check disabled via config.",
                asset_class="NiagaraSystem",
            )

        max_emitters = self.config.get("max_niagara_emitters", 8)

        try:
            meta = (
                self._validation_context.collect(asset_path)
                if self._validation_context is not None
                else None
            )
        except (AttributeError, TypeError):
            meta = None

        if meta is None:
            return self._makeSkipped(
                asset_path,
                "Emitter count validation requires metadata not provided by the current context.",
            )

        emitter_count = meta.properties.get("emitter_count", 0)

        if emitter_count <= max_emitters:
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Niagara system has {emitter_count} emitter(s) "
                    f"(within limit of {max_emitters})."
                ),
                asset_class="NiagaraSystem",
            )

        return self._makeFailure(
            asset_path=asset_path,
            message=(
                f"Niagara system has {emitter_count} emitter(s), exceeding "
                f"the limit of {max_emitters}."
            ),
            fix_hint=(
                f"Reduce the number of emitters in this Niagara system to "
                f"{max_emitters} or fewer, or increase max_niagara_emitters "
                f"in config.py."
            ),
        )


@registry.register
class NiagaraSpawnRateLimitRule(AbstractRule):
    """Validates that particle spawn rates stay within acceptable bounds.

    Extremely high spawn rates can cause frame drops and memory pressure.
    The maximum is configurable via ``max_niagara_spawn_rate`` in
    :mod:`gt.validator.config`.

    Attributes:
        name: Rule identifier ``"niagara_spawn_rate_limit"``.
        category: Rule category ``"niagara"``.
        severity: :attr:`Severity.WARNING`.
        context: Requires Unreal Engine host (HostType.UNREAL).

    """

    name = "niagara_spawn_rate_limit"
    category = "niagara"
    severity = Severity.WARNING
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate spawn rate against the configured maximum.

        Args:
            asset_path: Content-browser path of the Niagara asset to validate.

        Returns:
            A :class:`ValidationResult` indicating pass, fail, or skip.

        """
        if not self.isEnabled():
            return self._makeResult(
                asset_path,
                passed=True,
                message="Spawn rate check disabled via config.",
                asset_class="NiagaraSystem",
            )

        max_rate = self.config.get("max_niagara_spawn_rate", 10000)

        try:
            meta = (
                self._validation_context.collect(asset_path)
                if self._validation_context is not None
                else None
            )
        except (AttributeError, TypeError):
            meta = None

        if meta is None:
            return self._makeSkipped(
                asset_path,
                "Spawn rate validation requires metadata not provided by the current context.",
            )

        spawn_rate = meta.properties.get("spawn_rate", 0)

        if spawn_rate <= max_rate:
            return self._makeResult(
                asset_path,
                passed=True,
                message=(
                    f"Niagara spawn rate {spawn_rate} is within limit of "
                    f"{max_rate}."
                ),
                asset_class="NiagaraSystem",
            )

        return self._makeFailure(
            asset_path=asset_path,
            message=(
                f"Niagara spawn rate {spawn_rate} exceeds the limit of "
                f"{max_rate} particles/second."
            ),
            fix_hint=(
                f"Reduce the spawn rate in this Niagara system to "
                f"{max_rate} or fewer, or increase max_niagara_spawn_rate "
                f"in config.py."
            ),
        )


@registry.register
class NiagaraGPUSimulationRule(AbstractRule):
    """Validates GPU simulation settings on Niagara systems.

    GPU simulation can improve performance but may not be supported on all
    target platforms.  The requirement is configurable via
    ``allow_gpu_simulation`` in :mod:`gt.validator.config`.

    Attributes:
        name: Rule identifier ``"niagara_gpu_simulation"``.
        category: Rule category ``"niagara"``.
        severity: :attr:`Severity.INFO`.
        context: Requires Unreal Engine host (HostType.UNREAL).

    """

    name = "niagara_gpu_simulation"
    category = "niagara"
    severity = Severity.INFO
    context = HostType.UNREAL

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate GPU simulation settings.

        Args:
            asset_path: Content-browser path of the Niagara asset to validate.

        Returns:
            A :class:`ValidationResult` indicating pass, fail, or skip.

        """
        if not self.isEnabled():
            return self._makeResult(
                asset_path,
                passed=True,
                message="GPU simulation check disabled via config.",
                asset_class="NiagaraSystem",
            )

        allow_gpu = self.config.get("allow_gpu_simulation", True)

        try:
            meta = (
                self._validation_context.collect(asset_path)
                if self._validation_context is not None
                else None
            )
        except (AttributeError, TypeError):
            meta = None

        if meta is None:
            return self._makeSkipped(
                asset_path,
                "GPU simulation validation requires metadata not provided by the current context.",
            )

        uses_gpu = meta.properties.get("uses_gpu_simulation", False)

        if allow_gpu and uses_gpu:
            return self._makeResult(
                asset_path,
                passed=True,
                message="Niagara system uses GPU simulation (allowed).",
                asset_class="NiagaraSystem",
            )

        if not allow_gpu and uses_gpu:
            return self._makeFailure(
                asset_path=asset_path,
                message=(
                    "Niagara system uses GPU simulation, which is disabled "
                    "by config (allow_gpu_simulation=False)."
                ),
                fix_hint=(
                    "Switch to CPU simulation in the Niagara System editor, "
                    "or set allow_gpu_simulation=True in config.py."
                ),
            )

        return self._makeResult(
            asset_path,
            passed=True,
            message="Niagara system uses CPU simulation.",
            asset_class="NiagaraSystem",
        )
