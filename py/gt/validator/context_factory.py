"""ContextFactory — singleton factory for pluggable ValidationContext selection.

Provides a simple way to select the correct :class:`ValidationContext` based on
the current host type, without hardcoding it in every caller.  New context types
just need to inherit from ``ValidationContext`` and register with the factory.

Usage::

    from gt.validator.context_factory import ContextFactory
    ctx = ContextFactory.get_context()  # returns FilesystemContext or UnrealContext
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

class ContextFactory:
    """Singleton factory that selects a :class:`ValidationContext` based on the current host.

    The factory maintains a registry of available context classes and returns
    the appropriate one for the running environment.  New contexts can be added
    by registering them with ``register()``.

    Attributes:
        _contexts: Dict mapping HostType values to context class constructors.
    """

    # Mapping from HostType values to context class constructors.
    _contexts: dict[str, type[object]] = {}

    # Singleton instance — only create once per process.
    _instance: ContextFactory | None = None

    def __new__(cls) -> ContextFactory:
        """Return the singleton ContextFactory instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> ContextFactory:
        """Return the singleton ContextFactory instance.

        Returns:
            The ContextFactory singleton, creating it on first call if needed.

        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful in tests)."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, host_type_value: str, context_cls: type[object]) -> None:
        """Register a context class for a given HostType value.

        Args:
            host_type_value: String representation of the HostType (e.g., ``"UNREAL"``).
            context_cls: The ValidationContext subclass to instantiate when this host is active.

        """
        self._contexts[host_type_value] = context_cls
        logger.debug(
            "[ContextFactory] Registered %s for host type '%s'.",
            context_cls.__name__, host_type_value,
        )

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def get_context(self) -> object:
        """Return the appropriate ValidationContext for the current runtime.

        Attempts to detect the current host via ``gt.runtime.HostType`` and
        returns a matching context instance.  Falls back to :class:`FilesystemContext`
        if no specific match is found (standalone behavior).

        Returns:
            An instantiated :class:`ValidationContext` subclass.

        """
        from gt.validator.context.filesystem import FilesystemContext

        try:
            from gt.runtime import getCurrentHost

            current = getCurrentHost()
            if current is not None and hasattr(current, "value"):
                ctx_cls = self._contexts.get(current.value)
                if ctx_cls is not None:
                    logger.debug(
                        "[ContextFactory] Selected %s for host '%s'.",
                        ctx_cls.__name__, current.value,
                    )
                    return ctx_cls()
        except ImportError:
            # gt.runtime not available — default to filesystem context.
            pass

        # Default fallback: FilesystemContext (standalone behavior).
        logger.debug(
            "[ContextFactory] No specific match found; using FilesystemContext.",
        )
        return FilesystemContext()

# Pre-register the built-in contexts so get_context() works immediately.
def _register_default_contexts(factory: ContextFactory) -> None:
    """Register the default context types with the factory."""
    from gt.validator.context.blender import BlenderContext
    from gt.validator.context.filesystem import FilesystemContext
    from gt.validator.context.houdini import HoudiniContext
    from gt.validator.context.krita import KritaContext
    from gt.validator.context.max import MaxContext
    from gt.validator.context.maya import MayaContext
    from gt.validator.context.unreal import UnrealContext

    factory.register("STANDALONE", FilesystemContext)
    factory.register("UNREAL", UnrealContext)
    factory.register("MAYA", MayaContext)
    factory.register("MAX", MaxContext)
    factory.register("HOUDINI", HoudiniContext)
    factory.register("BLENDER", BlenderContext)
    factory.register("KRITA", KritaContext)

# Register defaults when module is imported.
_factory = ContextFactory.get_instance()
_register_default_contexts(_factory)
