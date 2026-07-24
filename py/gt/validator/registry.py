"""Rule registry: auto-discovery and decorator-based registration.

Provides a global registry that rules can register themselves with using the
``@registry.register`` decorator.  The registry supports auto-discovery of
rules from the rules subpackage.

Usage::

    from validator.registry import registry

    @registry.register
    class MyRule(AbstractRule):
        name = "my_rule"
        ...

"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import pkgutil
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RuleRegistry:
    """Singleton registry for AbstractRule subclasses.

    State is stored as **class attributes** so that repeated calls to
    ``RuleRegistry()`` — which Python always routes through ``__init__``
    after ``__new__`` — can never reset an already-populated registry.

    Lifecycle inside a running process:
        1. ``import validator.registry`` → singleton created (empty).
        2. ``runner.discover()`` called → rule modules imported.
        3. Each module-level ``@registry.register`` fires → rules added.
        4. ``runner.get_rules(...)`` returns the filtered class list.
        5. Runner instantiates each class with the shared Config.

    This is the **plugin pattern**: the core framework knows nothing about
    specific rules; rules know about the framework (registry) and register
    themselves.  New rules are dropped in without touching existing code.

    """

    _instance: RuleRegistry | None = None
    _rules: dict[str, type] = {}
    _discovered: bool = False

    def __new__(cls) -> RuleRegistry:
        """Create or return the singleton RuleRegistry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, cls: type) -> type:
        """Class decorator — registers a rule class.

        Reads ``name``, ``category``, and ``severity`` directly from the class.
        The class is the single source of truth for its metadata; the decorator
        simply announces it to the registry.

        """
        name = getattr(cls, "name", None) or cls.__name__
        if not getattr(cls, "category", ""):
            raise ValueError(
                f"Rule class {cls.__name__} must declare a non-empty "
                f"`category` class attribute before being registered."
            )
        if name in self._rules:
            logger.warning(
                "[Registry] Rule '%s' already registered — overwriting with %s.",
                name,
                cls.__name__,
            )
        self._rules[name] = cls
        logger.debug("[Registry] Registered rule '%s' (%s).", name, cls.__name__)
        return cls

    def discover(self) -> None:
        """Auto-discover and import all rule modules from configured paths.

        Always imports the built-in ``rules`` subpackage first. If the
        ``ENVOY_VALIDATION_RULES`` environment variable is also set (one or
        more paths separated by ``os.pathsep``), rule modules from each of
        those paths are discovered *in addition to* the built-ins — studio
        overlays extend the rule set, they never replace it. A missing or
        misconfigured entry logs a warning and is skipped rather than
        silently reducing the active rule set to zero.

        Triggers module-level ``@registry.register`` decorators, populating
        the registry without requiring explicit imports.  Subsequent calls are
        no-ops (discovery runs at most once per process).

        """
        if self._discovered:
            return
        type(self)._discovered = True

        # Always load the built-in rules package first. ENVOY_VALIDATION_RULES
        # (below) is additive — it contributes extra, studio-specific rule
        # paths on top of the built-ins, it never replaces them. Silently
        # discovering zero rules just because a studio overlay path is
        # missing/misconfigured would be a dangerous, hard-to-notice failure
        # mode for a validation tool.
        from . import rules as rules_pkg

        self._discover_from_package(rules_pkg)

        # Check for ENVOY_VALIDATION_RULES environment variable
        env_paths = os.environ.get("ENVOY_VALIDATION_RULES")
        if env_paths:
            # Split by os.pathsep to get multiple paths
            paths = [p for p in env_paths.split(os.pathsep) if p]
            logger.info("[Registry] Discovering rules from %d configured path(s)", len(paths))

            for path in paths:
                if not os.path.isdir(path):
                    logger.warning(
                        "[Registry] ENVOY_VALIDATION_RULES entry does not exist "
                        "or is not a directory — skipping: '%s'",
                        path,
                    )
                    continue
                self._discover_from_path(path)
        else:
            logger.debug("[Registry] ENVOY_VALIDATION_RULES not set; built-in rules only.")

    def _discover_from_path(self, path: str) -> None:
        """Discover and import rule modules from a specific path.

        Args:
            path: Filesystem path containing rule modules.

        """
        try:
            for _finder, module_name, _is_pkg in pkgutil.iter_modules([path]):
                if module_name == "base":
                    continue
                # Import the module dynamically
                module_path = os.path.join(path, module_name + ".py")
                if not os.path.exists(module_path):
                    logger.warning("[Registry] Module file not found at '%s'", module_path)
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        logger.debug("[Registry] Discovered module: %s", module.__name__)
                except ImportError as exc:
                    logger.warning(
                        "[Registry] Could not import module from '%s': %s", module_path, exc
                    )
        except Exception as exc:
            logger.warning("[Registry] Error discovering modules from path '%s': %s", path, exc)

    def _discover_from_package(self, package) -> None:
        """Discover and import rule modules from a package.

        Args:
            package: Python package object containing rule modules.

        """
        for _finder, module_name, _is_pkg in pkgutil.iter_modules(package.__path__):
            if module_name == "base":
                continue
            full_name = f"{package.__name__}.{module_name}"
            try:
                if full_name in sys.modules:
                    # Plain importlib.import_module() is a no-op for an
                    # already-cached module — Python does not re-run a
                    # module's top-level code on repeat imports, so its
                    # `@registry.register` decorators would not fire again.
                    # Without this, calling clear() after any built-in rule
                    # module has already been imported once (e.g. by a test
                    # importing a rule class directly) would permanently
                    # empty the registry for the rest of the process, since
                    # discover() could never re-populate it. Reload forces
                    # the module body (and its decorators) to run again.
                    importlib.reload(sys.modules[full_name])
                else:
                    importlib.import_module(full_name)
                logger.debug("[Registry] Discovered module: %s", full_name)
            except ImportError as exc:
                logger.warning("[Registry] Could not import '%s': %s", full_name, exc)

    def getRules(
        self,
        category: str | None = None,
        severity=None,
        context=None,
    ) -> list[type]:
        """Return registered rule classes, optionally filtered.

        Args:
            category: If provided, only rules with this category are returned.
            severity: If provided, only rules with this severity are returned.
            context: If provided, only rules with this context or multi-context
                rules that include this context are returned. Rules with no explicit
                context (None) match any filter.

        Returns:
            A list of rule classes matching the given filters.

        """
        rules = list(self._rules.values())
        if category:
            cat_lower = category.lower()
            rules = [r for r in rules if r.category.lower() == cat_lower]
        if severity is not None:
            rules = [r for r in rules if r.severity == severity]
        if context is not None:
            # Filter by the rule's declared context. A rule with no explicit
            # context (None) matches any filter, since it's a catch-all rule.
            def context_matches(rule):
                rule_ctx = getattr(rule, 'context', None) or None
                if rule_ctx is None:
                    return True  # No context declared — match everything
                if isinstance(rule_ctx, (tuple, list)):
                    # Multi-context rule — check if any of the contexts matches
                    return context in rule_ctx
                else:
                    # Single context rule
                    return rule_ctx == context

            rules = [r for r in rules if context_matches(r)]
        return rules

    def getRulesWithContext(self) -> dict[object, list[type]]:
        """Return registered rule classes grouped by their declared context.

        Rules with no explicit context (None) are placed under the STANDALONE key,
        since they run everywhere.  Rules with multi-context support (tuple/list)
        are placed under each of their supported contexts.  This is useful for the
        runner to efficiently group rules before instantiation.

        Returns:
            A dict mapping HostType values to lists of rule classes.

        """
        from gt.runtime import HostType

        groups: dict[object, list[type]] = {None: []}
        for r in self._rules.values():
            ctx = getattr(r, 'context', None) or HostType.STANDALONE

            # Handle multi-context rules — add to each supported context
            if isinstance(ctx, (tuple, list)):
                for c in ctx:
                    groups.setdefault(c, []).append(r)
            else:
                groups.setdefault(ctx, []).append(r)
        return groups

    def listRules(self) -> dict[str, type]:
        """Return a copy of the rules dict {name: class}."""
        return dict(self._rules)

    def clear(self) -> None:
        """Clear all registered rules (useful in tests)."""
        self._rules.clear()
        type(self)._discovered = False

    def __len__(self) -> int:
        """Return the number of registered rules."""
        return len(self._rules)

    def __repr__(self) -> str:
        """Return a string representation of the rule registry."""
        return f"RuleRegistry(rules={list(self._rules.keys())})"


registry = RuleRegistry()
