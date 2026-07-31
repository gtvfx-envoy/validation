# Writing Validation Rules

This guide walks through creating a new validation rule for the GT Asset Validation framework. By the end, you will have a working rule that integrates with the registry, runs via the ``ValidationRunner``, and produces structured ``ValidationResult`` output.

## Prerequisites

- Familiarity with Python 3.10+
- Understanding of the [context-aware rules](context-aware-rules.md) system
- Access to the `gt.runtime` package (available when running via `en python`)

## Rule Anatomy

Every validation rule is a subclass of ``AbstractRule`` that:

1. Is decorated with ``@registry.register`` for auto-discovery.
2. Declares class-level metadata: ``name``, ``category``, ``severity``, and optionally ``context``.
3. Implements ``validate(asset_path) -> ValidationResult``.

```python
from gt.runtime import HostType
from .base import AbstractRule, Severity, ValidationResult
from ..registry import registry


@registry.register
class MyNewRule(AbstractRule):
    """One-line summary shown in --list-rules output.

    Longer description if needed.  Keep docstrings concise — they are
    displayed in CLI help and HTML reports.

    """

    name = "my_new_rule"
    category = "my_category"
    severity = Severity.ERROR
    context = HostType.UNREAL  # Omit for cross-host rules

    def validate(self, asset_path: str) -> ValidationResult:
        ...
```

## Step 1: Declare Rule Metadata

| Attribute | Type | Required | Description |
|---|---|---|---|
| ``name`` | ``str`` | Yes | Unique snake_case identifier (e.g. ``"texture_dimension"``). Must match across your module and any config references. |
| ``category`` | ``str`` | Yes | Logical grouping (e.g. ``"texture"``, ``"naming"``, ``"filesystem"``). Used for filtering and report organization. |
| ``severity`` | ``Severity`` | Yes | ``Severity.ERROR``, ``Severity.WARNING``, or ``Severity.INFO``. Determines pass/fail behavior and reporting color. |
| ``context`` | ``HostType \| tuple[HostType, ...] \| None`` | No | Host(s) this rule applies to. Omit for cross-host rules. Use a tuple for multi-host support (e.g. ``(HostType.UNREAL, HostType.KRITA)``). |

## Step 2: Implement the validate() Method

The ``validate()`` method receives an asset path and must return a ``ValidationResult``.

### Basic Pattern

```python
def validate(self, asset_path: str) -> ValidationResult:
    """Validate that textures use BC7 compression.

    Args:
        asset_path: Filesystem or content-browser path of the asset.

    Returns:
        A ValidationResult indicating pass/fail/skip.

    """
    meta = self._validation_context.collect(asset_path)
    if meta is None:
        return self._makeSkipped(
            asset_path, "Texture metadata unavailable"
        )

    compression = meta.properties.get("compression")
    if compression == "BC7":
        return ValidationResult(
            asset_path=asset_path,
            rule_name=self.name,
            category=self.category,
            severity=self.severity,
            message=f"Texture uses {compression} compression.",
            passed=True,
        )

    return self._makeFailure(
        asset_path=asset_path,
        message=f"Texture uses '{compression}' compression; BC7 required.",
        fix_hint="Re-export the texture with BC7 compression in your DCC tool.",
    )
```

### Using Helper Methods

``AbstractRule`` provides two convenience methods:

- ``_makeSkipped(asset_path, reason)`` — returns a skipped result.
- ``_makeFailure(asset_path, message, fix_hint="")`` — returns a failed result with the rule's declared severity.

For passing results, construct ``ValidationResult`` directly (there is no helper since passes are straightforward).

### Accessing Asset Metadata

Rules access host-specific asset metadata through ``self._validation_context.collect(asset_path)``. The context returns an ``AssetMetadata`` object (or ``None`` if the metadata is unavailable):

```python
meta = self._validation_context.collect(asset_path)
if meta is None:
    return self._makeSkipped(asset_path, "No metadata available")

# Access properties via the .properties dict
width = meta.properties.get("width")
height = meta.properties.get("height")
asset_class = meta.properties.get("asset_class", "")
```

The ``AssetMetadata`` object provides:

| Attribute | Type | Description |
|---|---|---|
| ``name`` | ``str`` | Asset name without extension (e.g. ``"SM_Player"``) |
| ``extension`` | ``str`` | File extension including the dot (e.g. ``".uasset"``) |
| ``properties`` | ``dict[str, Any]`` | Host-specific key-value metadata |

## Step 3: Handle Edge Cases

### Graceful Degradation

Always check for ``None`` metadata and skip gracefully. Never let a rule crash the entire validation run:

```python
meta = self._validation_context.collect(asset_path)
if meta is None:
    return self._makeSkipped(asset_path, "Metadata unavailable")
```

### Exception Safety

The runner wraps each rule's ``validate()`` in a try/except. If your rule raises an unexpected exception, the runner catches it and produces a failure result with the traceback logged. However, you should still handle known error conditions explicitly:

```python
try:
    # Host-specific API call that might fail
    asset = load_asset(asset_path)
except FileNotFoundError:
    return self._makeSkipped(asset_path, "Asset file not found")
except PermissionError:
    return self._makeFailure(
        asset_path, "Permission denied reading asset",
        fix_hint="Check file permissions and try again.",
    )
```

## Step 4: Add Configuration Support (Optional)

If your rule needs tunable parameters, add them to ``config.py``:

1. Add the key to ``DEFAULTS`` with a sensible default.
2. Add the key to ``CONFIG_SCHEMA`` with its expected type.
3. Access via ``self.config.get("my_key")`` in your rule.

```python
# In config.py
DEFAULTS = {
    ...
    "max_texture_dimensions": [4096, 4096],
}

CONFIG_SCHEMA = {
    ...
    "max_texture_dimensions": list,
}

# In your rule
def validate(self, asset_path: str) -> ValidationResult:
    max_dims = self.config.get("max_texture_dimensions", [4096, 4096])
    if width > max_dims[0] or height > max_dims[1]:
        return self._makeFailure(...)
```

## Step 5: Write Tests

Place tests in ``py/gt/validator/rules/tests/`` alongside existing test files. Use ``_FakeMetadataContext`` for unit tests that don't require a real host:

```python
import unittest
from unittest.mock import patch
from gt.runtime import HostType
from gt.validator.config import Config
from .base import ValidationResult


class _FakeMetadataContext:
    """Minimal context mock for unit tests."""
    
    def collect(self, path):
        return None  # Override in individual tests as needed


class TestMyNewRule(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config()
        self.context = _FakeMetadataContext()

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.UNREAL)
    def test_skips_without_metadata(self, mock_host):
        from .my_module import MyNewRule
        rule = MyNewRule(self.config, validation_context=self.context)
        result = rule.validate("/Game/MyAsset.uasset")
        self.assertTrue(result.skipped)

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.UNREAL)
    def test_passes_valid_asset(self, mock_host):
        from .my_module import MyNewRule
        
        class _GoodContext(_FakeMetadataContext):
            def collect(self, path):
                meta = AssetMetadata(name="SM_Test", extension=".uasset")
                meta.properties["compression"] = "BC7"
                return meta
        
        rule = MyNewRule(self.config, validation_context=_GoodContext())
        result = rule.validate("/Game/SM_Test.uasset")
        self.assertTrue(result.passed)
```

## Step 6: Verify Your Rule

### List Rules

Confirm your rule appears in the registry:

```bash
en validate --list-rules | grep my_new_rule
```

### Run Against Sample Assets

```bash
en validate --directory /Game/ --format console
```

### Run Tests

```bash
en python -m pytest py/gt/validator/rules/tests/test_my_module.py -v
```

> **Important**: Always run Python via ``en python`` (envoy dispatch). This ensures the correct environment is concatenated, providing access to ``gt.runtime``, ``gt.krita``, and other bundle dependencies. Running bare ``python`` will fail with import errors.

## Common Pitfalls

### Forgetting the Registry Decorator

Rules must be decorated with ``@registry.register``. Without it, auto-discovery won't find them:

```python
# BAD — rule won't be discovered
class MyRule(AbstractRule):
    ...

# GOOD — registered for auto-discovery
@registry.register
class MyRule(AbstractRule):
    ...
```

### Shadowing the Context Attribute

Never assign to ``self.context`` in ``__init__``. The runner injects the ``ValidationContext`` into ``self._validation_context``. Assigning to ``self.context`` would shadow the class-level ``HostType`` attribute and break context filtering:

```python
# BAD — shadows class attribute, breaks isEnabled()
def __init__(self, config, validation_context=None):
    super().__init__(config)
    self.context = validation_context  # WRONG!

# GOOD — uses underscore-prefixed instance attribute
def __init__(self, config, validation_context=None):
    super().__init__(config)
    self._validation_context = validation_context or FilesystemContext()
```

### Using Bare Python Instead of Envoy

Always dispatch through envoy:

```bash
# GOOD
en python -m pytest py/gt/validator/rules/tests/

# BAD — will fail with import errors
python -m pytest py/gt/validator/rules/tests/
```

## Example: Complete Rule

Here is a complete, production-ready rule:

```python
"""Texture dimension validation rules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gt.runtime import HostType
from .base import AbstractRule, Severity, ValidationResult
from ..registry import registry

if TYPE_CHECKING:
    from ..config import Config


@registry.register
class TextureDimensionRule(AbstractRule):
    """Check that texture dimensions do not exceed configured maximums.

    Reads ``width`` and ``height`` from the validation context metadata.
    Skips gracefully when metadata is unavailable (e.g. outside Unreal).

    """

    name = "texture_dimension"
    category = "texture"
    severity = Severity.ERROR
    context = HostType.UNREAL

    def __init__(self, config: "Config", validation_context=None) -> None:
        super().__init__(config)
        self._validation_context = validation_context or FilesystemContext()

    def validate(self, asset_path: str) -> ValidationResult:
        """Validate texture dimensions against configured maximums.

        Args:
            asset_path: Path of the texture asset to check.

        Returns:
            A ValidationResult indicating pass, fail, or skip.

        """
        meta = self._validation_context.collect(asset_path)
        if meta is None:
            return self._makeSkipped(
                asset_path,
                "Texture dimension validation requires width/height metadata "
                "not provided by the current context.",
            )

        max_dim = self.config.get("max_texture_dimension", 4096)
        width = meta.properties.get("width", 0)
        height = meta.properties.get("height", 0)

        if width <= max_dim and height <= max_dim:
            return ValidationResult(
                asset_path=asset_path,
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                message=f"Texture dimensions {width}x{height} are within limit of {max_dim}.",
                passed=True,
            )

        return self._makeFailure(
            asset_path=asset_path,
            message=(
                f"Texture dimension {width}x{height} exceeds maximum of "
                f"{max_dim}x{max_dim}."
            ),
            fix_hint=f"Resize texture to {max_dim}x{max_dim} or increase "
                     f"max_texture_dimension in config.",
        )
```

## Next Steps

- Review the [context-aware rules](context-aware-rules.md) documentation for details on host filtering.
- Explore existing rules in ``py/gt/validator/rules/`` for reference implementations.
- Check the [reporting formatters](https://gtvfx-contrib.github.io/gt-validation/reference/gt.validator.reporting/) documentation to understand how your rule's output appears in reports.
