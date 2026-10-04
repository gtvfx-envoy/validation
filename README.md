# GT Validation

Extensive, application-agnostic asset validation framework — A comprehensive tool for validating digital assets against project standards and best practices. The validation rules are context-aware and can be isolated to a specific host application, but the framework itself is agnostic.

## Key Features

- **Rule-Based Validation** — Extensible rule system with context-aware checks
- **Application Agnostic** — Designed to work across multiple host applications with context-aware isolation
- **Configurable** — JSON-based configuration for custom validation rules
- **Reporting** — Structured reports with multiple output formats

## Quick Start

```python
from gt.validator import ValidationRunner, Config, ValidationReport

runner = ValidationRunner(Config())
report = runner.runAndReport("/path/to/assets")
print(report.summaryLine())
```

## Development and CI

Run `en python -m pytest py` in the Envoy development environment. The `dev`
extra includes pytest and pins Ruff to keep local and CI checks consistent.
Lint checks are read-only; apply fixes locally before pushing.

Debian CI uses the runner's cached Python 3.11.9. Tests run through the pinned
Envoy v0.6.2 native release with a temporary command environment that combines
this checkout, the `gt.globals` source Bundle (which provides `gt.runtime`), and
job-local development dependencies. It does not install `gt.globals` as a
Python project or depend on the runner's personal Envoy configuration.
CLI smoke tests create temporary sample assets rather than requiring external
content or workstation-specific paths.

## Documentation

| Topic | Description |
|---|---|
| [Home](https://gtvfx-contrib.github.io/gt-validation/) | Overview and getting started guide |
| [API Reference](https://gtvfx-contrib.github.io/gt-validation/reference/gt.validator/) | Complete Python API documentation |
| [Rules Module](https://gtvfx-contrib.github.io/gt-validation/reference/gt.validator.rules/) | Validation rule definitions and implementations |
| [Context Module](https://gtvfx-contrib.github.io/gt-validation/reference/gt.validator.context/) | Context-aware validation utilities |
| [Reporting Module](https://gtvfx-contrib.github.io/gt-validation/reference/gt.validator.reporting/) | Report generation and output formatting | |
