# Filesystem Pack Demo Manifest

## Session Use

- Session 03: first scanner and obvious filesystem failures.
- Session 04: config-driven policy and structured reporting.
- Session 05: same content under a framework-shaped implementation.
- Session 06: same content with plugin-style rule discovery.
- Session 08: context adapter classification examples.

## Clean Target

Use `clean_examples/project_aurora` to show the same validator can produce low
noise when content follows policy.

## Flawed Target

Use `flawed_examples/project_aurora` for live demonstrations.

## Recommended Callouts

| Fixture | Teaching Signal |
|---|---|
| `characters/Knight Final/geo/KnightBody.fbx` | Naming pattern violation |
| `characters/Knight Final/geo/chr_knight_sword_v001.max` | Forbidden extension |
| `characters/Knight Final/textures/empty_texture.png` | Empty file detection |
| `props/prp_lantern/geo/prp_lantern_final_final2.fbx` | Banned term and versioning problem |
| `environments/env_forest_clearing/temp/test_export.fbx` | Forbidden folder and banned term |
| `environments/env_forest_clearing/textures/.DS_Store` | Ignored hidden/system file policy |
| `vfx/vfx_magic_burst/docs/TODO.txt` | False-positive discussion |

## Instructor Rule

Do not scan `production_mock_pack` when teaching the first validator. The larger
pack is useful later, but it hides the teaching signal in volume.
