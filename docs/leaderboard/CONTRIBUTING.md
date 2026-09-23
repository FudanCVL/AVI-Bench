# Contributing leaderboard results

AVI-Bench uses a pull request workflow for public leaderboard updates. Contributors add a result record, provide a public source, and let the maintainers review the metadata before merging.

## Add a result

1. Copy `templates/result-entry.json` and append one object to `data/results.json`.
2. Use a unique stable `id`. Keep separate records for different model versions, benchmark releases, or evaluation runs.
3. Set `source.type` to `paper`, `participant`, or `maintainer`, and include a public HTTPS source URL.
4. Provide the model version's official release date as `model_release_date` (`YYYY-MM-DD`) and a public first-party announcement or model-repository link as `model_release_source_url`. Keep this separate from `evaluation_date`, which records when the benchmark evaluation occurred.
5. Report scores on a 0–100 scale. Use `null` when a source does not report a metric.
6. Set `coverage.status` to `full` only when all tasks in the benchmark release were evaluated. If sample counts are known, provide both counts.
7. Open a pull request against `FudanCVL/AVI-Bench`. Keep the change limited to the result record and related metadata.

The repository check runs `python3 docs/leaderboard/validate_results.py` on pull requests. A maintainer reviews the source, coverage, and completeness before merging. After merge, the GitHub Pages deployment publishes the updated homepage.

## Required information

- Display name, provider, exact model identifier, and benchmark release.
- Source type and a public source link.
- Official model release date and its source, task coverage, and evaluation date when available.
- Overall score and any reported stage, taxonomy, or task scores.

Provider logos are curated as local assets under `assets/logos/`. Contributors do not need to submit image URLs or binary assets.

A merged entry records a submitted result and its source; it does not claim an independent reproduction by the maintainers.

The homepage AVI-Index chart uses the `chart_benchmark_version` selected in `data/results.json`. It plots one point per model result with a release date and a Domain-Adaptive score, ordered by the actual release date. Keep the configured benchmark version fixed so a trend never mixes scores from different benchmark releases.
