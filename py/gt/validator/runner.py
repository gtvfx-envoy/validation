"""Orchestrates the asset validation pipeline.

Discovers and instantiates rules from the :class:`RuleRegistry`, then runs
them against assets in a directory.  Supports both serial mode (safe inside
Unreal Editor) and parallel mode via :class:`concurrent.futures.ThreadPoolExecutor`.
The number of worker threads is controlled by the ``max_workers`` constructor
argument or the ``VALIDATOR_MAX_WORKERS`` environment variable.

"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import time
from collections.abc import Callable, Iterator

from .allowlist import AllowlistManager
from .config import Config
from .context.base import ValidationContext
from .context_factory import ContextFactory
from .registry import registry
from .reporting.models import ValidationReport
from .rules.base import AbstractRule, Severity, ValidationResult

logger = logging.getLogger(__name__)


class ValidationRunner:
    """Orchestrates validation using rules sourced from the RuleRegistry.

    Discovers rules from the registry, instantiates them with the provided
    configuration, and runs them against assets in a directory — optionally
    using a thread pool for parallel processing.

    """

    def __init__(
        self,
        config: Config,
        category: str | None = None,
        severity: Severity | None = None,
        rules: list[type[AbstractRule]] | None = None,
        context: ValidationContext | None = None,
        allowlist: AllowlistManager | None = None,
        max_workers: int | None = None,
    ) -> None:
        """Initialise the runner with configuration and optional filters.

        Args:
            config: Layered Config object.
            category: Optional string filter — only rules in this category run.
            severity: Optional Severity filter.
            rules: Explicit list of rule classes — bypasses registry lookup.
            context: Optional ValidationContext instance to use for asset metadata.
                If ``None``, the runner auto-detects the appropriate context based
                on the current host type (Unreal or standalone) via ContextFactory.
            allowlist: Optional AllowlistManager instance.
            max_workers: Number of worker threads.  ``1`` = serial (safe in
                Unreal).  Default: ``VALIDATOR_MAX_WORKERS`` env var or CPU count.

        """
        self.config = config
        self.category = category
        self.severity = severity
        self.rules = rules or []
        self.context = context
        self.allowlist = allowlist

        # Set default max_workers if not provided
        if max_workers is None:
            max_workers = int(os.environ.get("VALIDATOR_MAX_WORKERS", "0"))
            if max_workers == 0:
                max_workers = os.cpu_count() or 4

        self.max_workers = max_workers

        # Discover and instantiate rules
        try:
            if rules:
                self.rules = [R(config) for R in rules]
            else:
                registry.discover()
                rule_classes = registry.getRules(category=category, severity=severity)
                if not rule_classes:
                    logger.warning(
                        "[ValidationRunner] No rules matched "
                        "(category=%r, severity=%r). Registered: %s",
                        category,
                        severity,
                        list(registry.listRules().keys()),
                    )
                # Auto-detect the appropriate context using ContextFactory.
                if self.context is None:
                    factory = ContextFactory.get_instance()
                    self.context = factory.get_context()

                # Filter rules by their declared context to match the current host.
                from gt.runtime import RuntimeDetector as _RuntimeDetector

                try:
                    current_host = _RuntimeDetector.getCurrentHost()
                except Exception:  # noqa: BLE001 - runtime may not be available
                    current_host = None

                if current_host is not None:
                    context_groups = registry.getRulesWithContext()
                    matching_rules = (
                        context_groups.get(current_host, [])
                        + context_groups.get(None, [])
                    )
                    # Deduplicate while preserving order
                    seen_names: set[str] = set()
                    filtered: list[type[AbstractRule]] = []
                    for r in matching_rules:
                        if r.name not in seen_names:
                            seen_names.add(r.name)
                            filtered.append(r)
                    rule_classes = filtered

                # Instantiate rules with the validation context object.
                ctx = self.context
                self.rules = [R(config, validation_context=ctx) for R in rule_classes]
        except Exception as e:
            logger.error(f"[ValidationRunner] Failed to initialize rules: {e}")
            raise

        self.last_run_cancelled = False

    def validateAsset(self, asset_path: str) -> list[ValidationResult]:
        """Run every active rule against a single asset path.

        Args:
            asset_path: Filesystem or content-browser path of the asset.

        Returns:
            A list of :class:`ValidationResult` objects, one per rule.

        """
        results: list[ValidationResult] = []

        # Check if asset is allowlisted
        if self.allowlist and self.allowlist.isAllowed(self.category or "", asset_path):
            logger.debug(f"[ValidationRunner] Asset {asset_path} is allowlisted")
            return [self._makeSkippedResult(asset_path, "Asset is allowlisted")]

        for rule in self.rules:
            if not rule.isEnabled():
                logger.debug(
                    "[ValidationRunner] Skipping disabled rule '%s' for asset '%s'.",
                    getattr(rule, "name", type(rule).__name__),
                    asset_path,
                )
                continue
            t0 = time.perf_counter()
            try:
                result = rule.validate(asset_path)
                result.duration_ms = (time.perf_counter() - t0) * 1000
            except Exception as exc:  # noqa: BLE001 - must isolate runtime rule failures
                duration_ms = (time.perf_counter() - t0) * 1000
                rule_name = getattr(rule, "name", "") or type(rule).__name__
                logger.exception(
                    "[ValidationRunner] Rule '%s' crashed for asset '%s'.",
                    rule_name,
                    asset_path,
                )
                result = self._makeRuleExecutionFailureResult(
                    rule=rule,
                    asset_path=asset_path,
                    exc=exc,
                    duration_ms=duration_ms,
                )
            results.append(result)
        return results

    def _makeRuleExecutionFailureResult(
        self,
        rule: AbstractRule,
        asset_path: str,
        exc: Exception,
        duration_ms: float,
    ) -> ValidationResult:
        """Create a failed result when a rule crashes at runtime.

        Args:
            rule: Rule instance that raised the runtime exception.
            asset_path: Asset being validated when the exception happened.
            exc: Runtime exception raised by the rule.
            duration_ms: Time elapsed before failure, in milliseconds.

        Returns:
            A failed :class:`ValidationResult` compatible with report formatters.

        """
        rule_name = getattr(rule, "name", "") or type(rule).__name__
        category = getattr(rule, "category", "") or "runtime"
        message = f"Rule runtime failure in '{rule_name}': {type(exc).__name__}: {exc}"
        return ValidationResult(
            asset_path=asset_path,
            rule_name=rule_name,
            category=category,
            severity=Severity.ERROR,
            message=message,
            passed=False,
            duration_ms=duration_ms,
            fix_hint="Inspect rule implementation and runner logs for traceback details.",
        )

    def _makeSkippedResult(self, asset_path: str, reason: str) -> ValidationResult:
        """Create a skipped result for an asset."""
        return ValidationResult(
            asset_path=asset_path,
            rule_name="",
            category="",
            severity=Severity.INFO,
            message=f"Asset skipped: {reason}",
            passed=True,
            skipped=True,
            duration_ms=0.0,
        )

    def validateAssets(self, asset_paths: list[str]) -> ValidationReport:
        """Validate an explicit list of asset paths and return an aggregated report.

        Useful when the caller already has a list of paths (e.g. the current
        selection in Unreal's Content Browser) rather than a directory to walk.

        Args:
            asset_paths: Explicit list of filesystem or content-browser paths.

        Returns:
            A :class:`ValidationReport` aggregating all rule results.

        """
        from . import __version__

        t0 = time.perf_counter()
        all_results: list[ValidationResult] = []

        # Process assets in parallel if max_workers > 1
        if self.max_workers > 1:
            try:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix="validator",
                ) as executor:
                    futures = {
                        executor.submit(self.validateAsset, path): path for path in asset_paths
                    }
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            all_results.extend(future.result())
                        except Exception as exc:  # noqa: BLE001 - thread boundary
                            asset_path = futures[future]
                            logger.error("[Runner] Error validating '%s': %s", asset_path, exc)
            except Exception as e:
                logger.error(f"[Runner] Failed to process assets in parallel: {e}")
                # Fall back to sequential processing
                for asset_path in asset_paths:
                    all_results.extend(self.validateAsset(asset_path))
        else:
            # Sequential processing
            for asset_path in asset_paths:
                all_results.extend(self.validateAsset(asset_path))

        duration = (time.perf_counter() - t0) * 1000
        return ValidationReport(
            results=all_results,
            asset_count=len(asset_paths),
            rule_count=len(self.rules),
            duration_ms=duration,
            tool_version=__version__,
        )

    def runAndReportFolders(
        self,
        folders: list[str],
        slow_task: object | None = None,
        should_cancel: Callable[[], bool] | None = None,
        advance_progress: Callable[[str], None] | None = None,
    ) -> ValidationReport:
        """Validate multiple folders and return a combined report.

        Accepts a list of content-browser or filesystem folder paths (e.g. the
        result of ``EditorUtilityLibrary.get_selected_path_view_folder_paths()``).
        Assets that appear under more than one folder are validated only once.

        Args:
            folders: List of filesystem or content-browser folder paths.
            slow_task: Optional Unreal-style slow task object with
                ``should_cancel()`` and ``enter_progress_frame()`` methods.
            should_cancel: Optional callback to check cancellation before each
                asset iteration.
            advance_progress: Optional callback invoked after each processed
                asset to advance external progress UIs.

        Returns:
            A :class:`ValidationReport` aggregating all rule results.

        """
        from . import __version__

        t0 = time.perf_counter()
        seen: set[str] = set()
        assets: list[str] = []

        # Collect unique assets from folders
        for folder in folders:
            try:
                for asset_path in self._iterAssets(folder):
                    if asset_path not in seen:
                        seen.add(asset_path)
                        assets.append(asset_path)
            except Exception as e:
                logger.error(f"[Runner] Failed to collect assets from {folder}: {e}")

        self.last_run_cancelled = False
        hooks_enabled = (
            slow_task is not None or should_cancel is not None or advance_progress is not None
        )

        def _is_cancelled() -> bool:
            if should_cancel is not None:
                return bool(should_cancel())
            if slow_task is None:
                return False
            should_cancel_method = getattr(slow_task, "should_cancel", None)
            if callable(should_cancel_method):
                return bool(should_cancel_method())
            return False

        def _advance_progress(asset_path: str) -> None:
            if advance_progress is not None:
                advance_progress(asset_path)
                return
            if slow_task is None:
                return
            progress_method = getattr(slow_task, "enter_progress_frame", None)
            if not callable(progress_method):
                return
            try:
                progress_method(1.0, asset_path)
            except TypeError:
                progress_method(1.0)

        # Process assets
        all_results: list[ValidationResult] = []
        processed_assets = 0

        if self.max_workers == 1 or hooks_enabled:
            for asset_path in assets:
                if _is_cancelled():
                    self.last_run_cancelled = True
                    break
                all_results.extend(self.validateAsset(asset_path))
                processed_assets += 1
                _advance_progress(asset_path)
        else:
            try:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix="validator",
                ) as executor:
                    futures = {executor.submit(self.validateAsset, path): path for path in assets}
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            all_results.extend(future.result())
                        except Exception as exc:  # noqa: BLE001 - thread boundary
                            asset_path = futures[future]
                            logger.error("[Runner] Error validating '%s': %s", asset_path, exc)
                processed_assets = len(assets)
            except Exception as e:
                logger.error(f"[Runner] Failed to process assets in parallel: {e}")
                # Fall back to sequential processing
                for asset_path in assets:
                    if _is_cancelled():
                        self.last_run_cancelled = True
                        break
                    all_results.extend(self.validateAsset(asset_path))
                    processed_assets += 1
                    _advance_progress(asset_path)

        if self.last_run_cancelled:
            logger.warning(
                "[ValidationRunner] Validation cancelled by user. "
                "Partial report generated (%s/%s assets processed).",
                processed_assets,
                len(assets),
            )

        duration = (time.perf_counter() - t0) * 1000
        return ValidationReport(
            results=all_results,
            asset_count=processed_assets,
            rule_count=len(self.rules),
            duration_ms=duration,
            tool_version=__version__,
        )

    def runAndReport(
        self,
        directory: str,
        slow_task: object | None = None,
        should_cancel: Callable[[], bool] | None = None,
        advance_progress: Callable[[str], None] | None = None,
    ) -> ValidationReport:
        """Validate a directory and return an aggregated report.

        Assets are validated concurrently using a thread pool.  The number of
        worker threads is controlled by ``max_workers`` (default: CPU count) or
        the ``VALIDATOR_MAX_WORKERS`` environment variable.

        Note on thread safety: each ``rule.validate()`` call is independent.
        Rules must not share mutable state.  The Unreal Python API is generally
        NOT thread-safe; parallel processing is most beneficial in standalone
        (filesystem-only) mode.  In Unreal, set ``max_workers=1``.

        Args:
            directory: Root filesystem path or Unreal content path to validate.
            slow_task: Optional Unreal-style slow task object with
                ``should_cancel()`` and ``enter_progress_frame()`` methods.
            should_cancel: Optional callback to check cancellation before each
                asset iteration.
            advance_progress: Optional callback invoked after each processed
                asset to advance external progress UIs.

        Returns:
            A :class:`ValidationReport` aggregating all rule results.

        """
        from . import __version__

        t0 = time.perf_counter()

        # Collect assets from directory
        try:
            assets = list(self._iterAssets(directory))
        except Exception as e:
            logger.error(f"[Runner] Failed to collect assets from {directory}: {e}")
            raise

        self.last_run_cancelled = False
        hooks_enabled = (
            slow_task is not None or should_cancel is not None or advance_progress is not None
        )

        def _is_cancelled() -> bool:
            if should_cancel is not None:
                return bool(should_cancel())
            if slow_task is None:
                return False
            should_cancel_method = getattr(slow_task, "should_cancel", None)
            if callable(should_cancel_method):
                return bool(should_cancel_method())
            return False

        def _advance_progress(asset_path: str) -> None:
            if advance_progress is not None:
                advance_progress(asset_path)
                return
            if slow_task is None:
                return
            progress_method = getattr(slow_task, "enter_progress_frame", None)
            if not callable(progress_method):
                return
            try:
                progress_method(1.0, asset_path)
            except TypeError:
                progress_method(1.0)

        # Process assets
        all_results: list[ValidationResult] = []
        processed_assets = 0

        if self.max_workers == 1 or hooks_enabled:
            for asset_path in assets:
                if _is_cancelled():
                    self.last_run_cancelled = True
                    break
                all_results.extend(self.validateAsset(asset_path))
                processed_assets += 1
                _advance_progress(asset_path)
        else:
            try:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix="validator",
                ) as executor:
                    futures = {executor.submit(self.validateAsset, path): path for path in assets}
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            all_results.extend(future.result())
                        except Exception as exc:  # noqa: BLE001 - thread boundary
                            asset_path = futures[future]
                            logger.error("[Runner] Error validating '%s': %s", asset_path, exc)
                processed_assets = len(assets)
            except Exception as e:
                logger.error(f"[Runner] Failed to process assets in parallel: {e}")
                # Fall back to sequential processing
                for asset_path in assets:
                    if _is_cancelled():
                        self.last_run_cancelled = True
                        break
                    all_results.extend(self.validateAsset(asset_path))
                    processed_assets += 1
                    _advance_progress(asset_path)

        if self.last_run_cancelled:
            logger.warning(
                "[ValidationRunner] Validation cancelled by user. "
                "Partial report generated (%s/%s assets processed).",
                processed_assets,
                len(assets),
            )

        duration = (time.perf_counter() - t0) * 1000
        return ValidationReport(
            results=all_results,
            asset_count=processed_assets,
            rule_count=len(self.rules),
            duration_ms=duration,
            tool_version=__version__,
        )

    def _iterAssets(self, directory: str) -> Iterator[str]:
        """Yield asset paths from a directory.

        Handles both real filesystem paths and Unreal virtual content paths
        (e.g. ``/Game/``).  When an Unreal path is given and Unreal is
        available, uses :class:`UnrealContext` to enumerate via
        ``EditorAssetLibrary``.  Unreal's Python API is single-threaded;
        set ``max_workers=1`` in the constructor when using this from inside
        the Editor.

        Args:
            directory: Root filesystem path or Unreal content path.

        Raises:
            ValueError: If directory is neither a valid filesystem directory
                nor a resolvable Unreal content path.

        """
        from .env import HAS_UNREAL

        if not os.path.isdir(directory) and directory.startswith('/'):
            if not HAS_UNREAL:
                raise ValueError(
                    f"'{directory}' is an Unreal content path but Unreal Engine "
                    f"is not available.  Run inside Unreal Editor, or supply a "
                    f"real filesystem directory."
                )
            import unreal as _ue

            for asset_path in _ue.EditorAssetLibrary.list_assets(
                directory, recursive=True, include_folder=False
            ):
                yield str(asset_path)
        else:
            if not os.path.isdir(directory):
                raise ValueError(f"Not a valid directory: '{directory}'")
            for root, _dirs, files in os.walk(directory):
                for filename in sorted(files):
                    yield os.path.join(root, filename)
