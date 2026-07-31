# Production Mock Pack

This pack creates a large filesystem-only mock game production tree for the course.

Purpose:
- provide a realistic directory structure for filesystem validators
- include mostly logical asset placement and naming
- inject a deliberate set of production-style failures for rule testing
- keep file contents unimportant so validators can focus on paths and names

The generator creates:
- one primary project tree: `project_nebula`
- a mostly clean published asset layout across common categories
- intentionally bad files and folders mixed into believable locations
- a little over 1,000 empty files

Primary validation targets:
- naming convention violations
- forbidden terms like `final`, `latest`, `temp`, `backup`, and `old`
- bad folder placement
- unexpected file extensions
- case inconsistency
- junk files such as `thumbs.db` and `.DS_Store`
- suspicious review or export drops

Regenerate with:

```powershell
python sample_content\production_mock_pack\tools\generate_production_mock_pack.py
```
