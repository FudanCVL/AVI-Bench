# AVI-Bench leaderboard data

This directory is the canonical source for the leaderboard shown on the project homepage.

- `data/results.json` contains the published entries.
- `templates/result-entry.json` is the contribution template.
- `validate_results.py` checks the public schema and score ranges.
- `assets/logos/` contains the locally curated provider marks.

The homepage reads `data/results.json` at runtime. Do not edit table rows directly in `docs/index.html`.
