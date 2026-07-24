# GT Validation

Extensive, application-agnostic asset validation framework — A comprehensive tool for validating game assets against project standards and best practices. The validation rules are context-aware and can be isolated to a specific host application, but the framework itself is agnostic.

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

## Documentation

| Topic | Description |
|---|---|
| [Home](https://gtvfx-contrib.github.io/gt-validation/) | Overview and getting started guide |
| [API Reference](https://gtvfx-contrib.github.io/gt-validation/reference/gt.validator/) | Complete Python API documentation |
| [Rules Module](https://gtvfx-contrib.github.io/gt-validation/reference/gt.validator.rules/) | Validation rule definitions and implementations |
| [Context Module](https://gtvfx-contrib.github.io/gt-validation/reference/gt.validator.context/) | Context-aware validation utilities |
| [Reporting Module](https://gtvfx-contrib.github.io/gt-validation/reference/gt.validator.reporting/) | Report generation and output formatting |

## Installation

```bash
pip install gt-validation
```

## License

MIT License
