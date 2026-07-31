# Sample Content Alignment

`sample_content/` provides repeatable content fixtures for demos, assignments,
and validation framework smoke checks.

## Pack Map

| Pack | Primary Sessions | Use | Default? |
|---|---|---|---|
| `filesystem_pack` | Sessions 03-06, Session 08 context adapter | Small clean/flawed Project Aurora tree for filesystem validation | Yes |
| `production_mock_pack` | Later scale/reference discussions | Larger Project Nebula tree for scale and production-noise discussion | No |

## Instructor Guidance

- Use `filesystem_pack` for live coding because it is small enough to explain.
- Use `production_mock_pack` only when the lesson is about scale, runtime, or production messiness.
- Prefer known flawed subsets over scanning huge trees during live instruction.

## Fixture Policy

Every intentional failure should be explainable by filename, path, extension,
empty-file state, or mocked asset metadata. Avoid mystery failures that require
private tooling, bundled marketplace content, or large local asset dumps.
