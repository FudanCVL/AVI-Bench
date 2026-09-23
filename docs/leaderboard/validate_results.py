#!/usr/bin/env python3
"""Validate the public AVI-Bench leaderboard data file."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "data" / "results.json"
SOURCE_TYPES = {"paper", "participant", "maintainer"}
TOP_LEVEL_FIELDS = {
    "id",
    "model_name",
    "provider",
    "model_id",
    "benchmark_version",
    "source",
    "evaluation_date",
    "coverage",
    "scores",
    "submitter",
    "notes",
}


class ValidationError(ValueError):
    """Raised when leaderboard data fails its public schema checks."""


def require_text(record: dict, field: str, path: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{path}.{field} must be a non-empty string")
    return value.strip()


def validate_score_values(value, path: str) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValidationError(f"{path} contains an empty metric name")
            validate_score_values(child, f"{path}.{key}")
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{path} must be a number or null")
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValidationError(f"{path} must be between 0 and 100")


def validate_entry(entry, index: int) -> str:
    path = f"entries[{index}]"
    if not isinstance(entry, dict):
        raise ValidationError(f"{path} must be an object")

    unknown = set(entry) - TOP_LEVEL_FIELDS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValidationError(f"{path} has unsupported fields: {names}")

    record_id = require_text(entry, "id", path)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{1,99}", record_id):
        raise ValidationError(f"{path}.id must be a 2–100 character slug")

    for field in ("model_name", "provider", "model_id", "benchmark_version"):
        require_text(entry, field, path)

    source = entry.get("source")
    if not isinstance(source, dict):
        raise ValidationError(f"{path}.source must be an object")
    if set(source) != {"type", "url"}:
        raise ValidationError(f"{path}.source must contain only type and url")
    source_type = source.get("type")
    if not isinstance(source_type, str) or source_type not in SOURCE_TYPES:
        choices = ", ".join(sorted(SOURCE_TYPES))
        raise ValidationError(f"{path}.source.type must be one of: {choices}")
    source_url = require_text(source, "url", f"{path}.source")
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValidationError(f"{path}.source.url must be an https URL")

    evaluation_date = entry.get("evaluation_date")
    if evaluation_date is not None:
        if not isinstance(evaluation_date, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", evaluation_date
        ):
            raise ValidationError(f"{path}.evaluation_date must be YYYY-MM-DD or null")
        try:
            date.fromisoformat(evaluation_date)
        except ValueError as exc:
            raise ValidationError(
                f"{path}.evaluation_date must be YYYY-MM-DD or null"
            ) from exc

    coverage = entry.get("coverage")
    if not isinstance(coverage, dict):
        raise ValidationError(f"{path}.coverage must be an object")
    allowed_coverage = {
        "status", "tasks_completed", "tasks_total", "samples_completed", "samples_total"
    }
    if set(coverage) - allowed_coverage:
        raise ValidationError(f"{path}.coverage has unsupported fields")
    status = coverage.get("status")
    if not isinstance(status, str) or status not in {"full", "partial"}:
        raise ValidationError(f"{path}.coverage.status must be full or partial")
    for field in ("tasks_completed", "tasks_total"):
        count = coverage.get(field)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValidationError(f"{path}.coverage.{field} must be a non-negative integer")
    tasks_completed = coverage["tasks_completed"]
    tasks_total = coverage["tasks_total"]
    if tasks_total == 0 or tasks_completed > tasks_total:
        raise ValidationError(f"{path}.coverage task counts are inconsistent")
    if status == "full" and tasks_completed != tasks_total:
        raise ValidationError(f"{path} is full but does not cover every task")
    for field in ("samples_completed", "samples_total"):
        count = coverage.get(field)
        if count is not None and (
            isinstance(count, bool) or not isinstance(count, int) or count < 0
        ):
            raise ValidationError(
                f"{path}.coverage.{field} must be a non-negative integer or null"
            )
    completed_samples = coverage.get("samples_completed")
    total_samples = coverage.get("samples_total")
    if (completed_samples is None) != (total_samples is None):
        raise ValidationError(
            f"{path}.coverage must report both sample counts or neither"
        )
    if completed_samples is not None and total_samples is not None:
        if completed_samples > total_samples:
            raise ValidationError(f"{path}.coverage sample counts are inconsistent")
        if status == "full" and completed_samples != total_samples:
            raise ValidationError(f"{path} is full but sample coverage is incomplete")
    if status == "partial" and tasks_completed == tasks_total:
        if completed_samples is None or completed_samples == total_samples:
            raise ValidationError(f"{path} is partial but reports full coverage")

    scores = entry.get("scores")
    if not isinstance(scores, dict):
        raise ValidationError(f"{path}.scores must be an object")
    if set(scores) - {"overall", "stages", "taxonomy", "tasks"}:
        raise ValidationError(f"{path}.scores has unsupported fields")
    validate_score_values(scores, f"{path}.scores")

    notes = entry.get("notes")
    if notes is not None and (not isinstance(notes, str) or len(notes) > 1000):
        raise ValidationError(f"{path}.notes must be text of at most 1000 characters")
    submitter = entry.get("submitter")
    if submitter is not None and not isinstance(submitter, str):
        raise ValidationError(f"{path}.submitter must be text or null")
    return record_id


def validate_file(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON at line {exc.lineno}, column {exc.colno}") from exc

    if not isinstance(data, dict) or set(data) != {"schema_version", "entries"}:
        raise ValidationError("root must contain exactly schema_version and entries")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValidationError("schema_version must be 1")
    entries = data["entries"]
    if not isinstance(entries, list):
        raise ValidationError("entries must be an array")

    seen = set()
    for index, entry in enumerate(entries):
        record_id = validate_entry(entry, index)
        if record_id in seen:
            raise ValidationError(f"duplicate entry id: {record_id}")
        seen.add(record_id)
    return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()

    try:
        count = validate_file(args.path)
    except ValidationError as exc:
        print(f"Invalid leaderboard data: {exc}", file=sys.stderr)
        return 1
    print(f"Valid leaderboard data: {count} entr{'y' if count == 1 else 'ies'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
