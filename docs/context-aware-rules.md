# Context-Aware Validation Rules

## Overview

The validation framework supports context-aware rules that automatically filter based on the current runtime environment (Unreal, Maya, Max, Houdini, Blender, Krita, or Standalone). Rules declare their supported host type(s) via a class-level `context` attribute, and the runner only instantiates matching rules for the detected host.

## Writing a Context-Aware Rule

### Single-Host Rule (Unreal-only)

```python
from gt.runtime import HostType
from .base import AbstractRule, Severity
from ..registry import registry


@registry.register
class MyUnrealRule(AbstractRule):
    """A rule that only runs inside Unreal Engine.

    The ``context`` class attribute tells the runner to skip this rule
    in standalone or other host environments.

    """

    name = "my_unreal_rule"
    category = "my_category"
    severity = Severity.ERROR
    context = HostType.UNREAL  # Only runs when host is Unreal

    def validate(self, asset_path: str) -> ValidationResult:
        # self._validation_context is guaranteed to be an UnrealContext here
        ...
```

### Multi-Host Rule (runs in multiple environments)

```python
from gt.runtime import HostType
from .base import AbstractRule, Severity
from ..registry import registry


@registry.register
class MyCrossHostRule(AbstractRule):
    """A rule that runs in both Unreal and Krita."""

    name = "my_cross_host_rule"
    category = "my_category"
    severity = Severity.WARNING
    context = (HostType.UNREAL, HostType.KRITA)  # Tuple of supported hosts

    def validate(self, asset_path: str) -> ValidationResult:
        ...
```

### Standalone-Only Rule

```python
from gt.runtime import HostType
from .base import AbstractRule, Severity
from ..registry import registry


@registry.register
class MyStandaloneRule(AbstractRule):
    """A rule that only runs in standalone Python."""

    name = "my_standalone_rule"
    category = "filesystem"
    severity = Severity.INFO
    context = HostType.STANDALONE

    def validate(self, asset_path: str) -> ValidationResult:
        ...
```

### No-Host Rule (runs everywhere)

If you omit the `context` attribute entirely, the rule runs in every host environment. This is useful for filesystem-level checks that don't depend on any host-specific API.

## How Context Filtering Works

The ``RuleRegistry`` filters rules by their declared context when the runner requests them:

```python
# Get all rules for a specific host
rules = registry.getRules(context=HostType.UNREAL)

# Get all rules (no filter)
all_rules = registry.getRules()
```

The ``ValidationRunner`` detects the current host via ``RuntimeDetector.getCurrentHost()`` and instantiates only matching rule classes. Rules whose `context` doesn't match the current host are silently skipped — they never run, so there's no need for try/except guards inside individual rules.

## HostType Enum

| Value | Description |
|---|---|
| `HostType.STANDALONE` | Standalone Python (no DCC application) |
| `HostType.UNREAL` | Unreal Engine |
| `HostType.MAYA` | Autodesk Maya |
| `HostType.MAX` | Autodesk 3ds Max |
| `HostType.HOUDINI` | SideFX Houdini |
| `HostType.BLENDER` | Blender |
| `HostType.KRITA` | Krita |

## Accessing Asset Metadata

Rules receive a ``ValidationContext`` instance injected by the runner. The context provides host-specific asset metadata through its ``collect()`` method:

```python
def validate(self, asset_path: str) -> ValidationResult:
    meta = self._validation_context.collect(asset_path)
    if meta is None:
        return self._makeSkipped(asset_path, "Metadata unavailable")
    
    # Access host-specific properties via meta.properties dict
    width = meta.properties.get("width")
    height = meta.properties.get("height")
    ...
```

The ``ValidationContext`` base class provides a default ``collect()`` that returns ``None``. Host-specific subclasses (``UnrealContext``, ``FilesystemContext``, etc.) override this to return meaningful metadata. Rules should always check for ``None`` and skip gracefully when metadata is unavailable.

## Registry API

### getRules()

```python
def getRules(
    category: str | None = None,
    severity=None,
    context=None,
) -> list[type]:
    """Return registered rule classes, optionally filtered.

    Args:
        category: If provided, only rules with this category are returned.
        severity: If provided, only rules with this severity are returned.
        context: If provided, only rules with this context (or multi-context
            rules that include it) are returned. Rules without an explicit
            ``context`` attribute match any filter.

    Returns:
        A list of rule classes matching the given filters.
    """
```

### getRulesWithContext()

Groups registered rules by their declared context for efficient lookup:

```python
groups = registry.getRulesWithContext()
# {HostType.UNREAL: [...], HostType.STANDALONE: [...], None: [...]}
```

## ValidationRunner

The ``ValidationRunner`` handles host detection and rule instantiation automatically:

```python
from gt.validator.runner import ValidationRunner
from gt.validator.config import Config

config = Config()
runner = ValidationRunner(config, max_workers=4)

# runner.rules contains only rules matching the current host
for rule in runner.rules:
    print(f"{rule.name} (enabled={rule.isEnabled()})")

report = runner.validateAssets(["/Game/MyAsset.uasset"])
```

## Testing Rules

### Unit Test with Mock Context

```python
import unittest
from unittest.mock import patch
from gt.runtime import HostType
from .base import AbstractRule, ValidationResult


class _FakeContext:
    """Minimal context mock for unit tests."""
    
    def collect(self, path):
        return None  # Skip when metadata unavailable


class TestMyRule(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config()
        self.context = _FakeContext()

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.UNREAL)
    def test_rule_runs_in_unreal(self, mock_host):
        rule = MyUnrealRule(self.config, validation_context=self.context)
        result = rule.validate("/Game/MyAsset.uasset")
        self.assertIsInstance(result, ValidationResult)
```

### Test Skipping Behavior

Rules that declare a host-specific context are automatically skipped when running in the wrong environment. You can verify this:

```python
def test_skips_outside_unreal(self) -> None:
    rule = MyUnrealRule(self.config, validation_context=self.context)
    self.assertFalse(rule.isEnabled())  # STANDALONE != UNREAL
```

## Output Formatters

The framework includes five output formatters:

| Format | Class | Extension | Use Case |
|---|---|---|---|
| Console | ``ConsoleFormatter`` | N/A (stdout) | Interactive terminal use with ANSI colors |
| JSON | ``JSONFormatter`` | `.json` | Machine-readable, dashboards, custom processing |
| HTML | ``HTMLFormatter`` | `.html` | Self-contained single-file report with CSS |
| SARIF | ``SARIFFormatter`` | `.sarif.json` | OASIS standard for CI/CD (GitHub, Azure DevOps) |
| JUnit XML | ``JUnitXMLFormatter`` | `.xml` | Jenkins, GitLab CI, GitHub Actions test reports |

Select a formatter via the `--format` CLI flag or the `VALIDATOR_FORMAT` environment variable:

```bash
en validate --directory /Game/ --format sarif --output-dir ./reports
```

## Troubleshooting

### Rule Not Running

1. Check that the rule has a ``context`` class attribute matching the current host.
2. Verify with ``en validate --list-rules`` to see which rules are active.
3. Rules without a ``context`` attribute run in all hosts — if this is unintended, add one.

### Metadata Unavailable

If ``self._validation_context.collect()`` returns ``None``, the rule should skip gracefully:

```python
meta = self._validation_context.collect(asset_path)
if meta is None:
    return self._makeSkipped(asset_path, "Metadata unavailable for this asset type")
```

### Context Not Set

If you get a ``TypeError`` about missing ``validation_context`` parameter, ensure the rule's ``__init__`` accepts it:

```python
def __init__(self, config: Config, validation_context=None) -> None:
    super().__init__(config)
    self._validation_context = validation_context or FilesystemContext()
```
