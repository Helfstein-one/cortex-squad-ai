#!/usr/bin/env python3
"""Deterministic mutation probe for injecting synthetic data anomalies."""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

VALID_MODES = ("nulls", "skew", "out-of-order", "schema-drift", "duplicates", "all")

DEFAULT_RECORDS: list[dict[str, Any]] = [
    {
        "id": "rec-1",
        "amount": 100.0,
        "event_ts": "2026-01-10T12:00:00Z",
        "status": "ok",
    },
    {
        "id": "rec-2",
        "amount": 250.0,
        "event_ts": "2026-01-11T12:00:00Z",
        "status": "ok",
    },
]


def _mutate_nulls(records: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    mutated = copy.deepcopy(records)
    if not mutated:
        return mutated
    target = mutated[rng.randrange(len(mutated))]
    keys = [k for k in target if not k.startswith("_")]
    if keys:
        chosen = keys[rng.randrange(len(keys))]
        target[chosen] = None
    else:
        target["_null_probe"] = None
    return mutated


def _mutate_skew(records: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    mutated = copy.deepcopy(records)
    if not mutated:
        return mutated
    hot_key = f"HOT_SKEW_KEY_{rng.randint(1, 99)}"
    hot_idx = rng.randrange(len(mutated))
    scale = rng.choice((100, 500, 1000, 5000))
    str_choice = rng.randrange(1000)
    num_choice = rng.randrange(1000)

    for idx, rec in enumerate(mutated):
        num_keys = [
            k for k, v in rec.items() if isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        str_keys = [k for k, v in rec.items() if isinstance(v, str)]
        if num_keys:
            chosen_num = num_keys[num_choice % len(num_keys)]
            rec[chosen_num] = rec[chosen_num] * scale if idx == hot_idx else -1
        if str_keys:
            chosen_str = str_keys[str_choice % len(str_keys)]
            rec[chosen_str] = hot_key
        if not num_keys and not str_keys:
            rec["_skew_partition_key"] = hot_key

    if len(mutated) == 1:
        extra = copy.deepcopy(mutated[0])
        num_keys = [
            k for k, v in extra.items() if isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        if num_keys:
            chosen_num = num_keys[num_choice % len(num_keys)]
            extra[chosen_num] = -1
        mutated.append(extra)
    return mutated


def _shift_iso_timestamp(value: str, hours_back: int) -> str | None:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        shifted = parsed - timedelta(hours=hours_back)
    except (ValueError, OverflowError):
        return None
    result = shifted.isoformat()
    return result.replace("+00:00", "Z") if value.endswith("Z") else result


def _mutate_out_of_order(
    records: list[dict[str, Any]], rng: random.Random
) -> list[dict[str, Any]]:
    mutated = copy.deepcopy(records)
    if not mutated:
        return mutated
    ts_shifted = False
    for rec in mutated:
        for key, value in list(rec.items()):
            if isinstance(value, str) and (
                "ts" in key.lower() or "date" in key.lower() or "time" in key.lower()
            ):
                shifted = _shift_iso_timestamp(value, hours_back=rng.randint(24, 240))
                if shifted is not None:
                    rec[key] = shifted
                    ts_shifted = True
    if not ts_shifted:
        late_idx = rng.randrange(len(mutated))
        mutated[late_idx]["_late_event_ts"] = f"1970-01-01T{rng.randint(0, 23):02d}:00:00Z"
    if len(mutated) > 1:
        before_shuffle = copy.deepcopy(mutated)
        rng.shuffle(mutated)
        if mutated == before_shuffle:
            mutated.reverse()
    return mutated


def _mutate_schema_drift(
    records: list[dict[str, Any]], rng: random.Random
) -> list[dict[str, Any]]:
    mutated = copy.deepcopy(records)
    if not mutated:
        return mutated
    target = mutated[rng.randrange(len(mutated))]
    keys = [k for k in target if not k.startswith("_")]
    if len(keys) > 1:
        drop_key = rng.choice(keys)
        del target[drop_key]
        remaining = [k for k in keys if k != drop_key]
    else:
        remaining = keys
    if remaining:
        coerce_key = rng.choice(remaining)
        expected_type = type(target.get(coerce_key)).__name__
        target[coerce_key] = {"corrupted_type": True, "expected": expected_type}
    target["_unexpected_drift_col"] = f"v2_schema_drift_{rng.randint(1, 99)}"
    return mutated


def _mutate_duplicates(
    records: list[dict[str, Any]], rng: random.Random
) -> list[dict[str, Any]]:
    mutated = copy.deepcopy(records)
    if not mutated:
        return mutated
    src_idx = rng.randrange(len(mutated))
    exact_dup = copy.deepcopy(mutated[src_idx])
    near_dup = copy.deepcopy(mutated[src_idx])
    near_dup["_replay_conflict"] = True
    near_dup["_replay_seq"] = rng.randint(1, 999)
    mutated.extend([exact_dup, near_dup])
    return mutated


def inject_mutations(
    records: list[dict[str, Any]],
    mode: str = "all",
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Deterministically inject synthetic anomalies into a list of record dictionaries."""
    if mode not in VALID_MODES:
        raise ValueError(f"Unsupported mutation mode '{mode}'. Expected one of: {VALID_MODES}")
    if not records:
        return []

    rng = random.Random(seed)
    handlers = {
        "nulls": _mutate_nulls,
        "skew": _mutate_skew,
        "out-of-order": _mutate_out_of_order,
        "schema-drift": _mutate_schema_drift,
        "duplicates": _mutate_duplicates,
    }
    if mode != "all":
        return handlers[mode](records, rng)

    combined: list[dict[str, Any]] = []
    null_part = _mutate_nulls(records, rng)
    combined.append(
        next((r for r, orig in zip(null_part, records, strict=False) if r != orig), null_part[0])
    )
    skew_part = _mutate_skew(records, rng)
    combined.append(
        next(
            (r for r in skew_part if "_skew_partition_key" in r),
            next(
                (r for r, orig in zip(skew_part, records, strict=False) if r != orig),
                skew_part[0],
            ),
        )
    )
    late_part = _mutate_out_of_order(records, rng)
    combined.append(
        next(
            (r for r in late_part if "_late_event_ts" in r),
            next((r for r in late_part if r not in records), late_part[0]),
        )
    )
    drift_part = _mutate_schema_drift(records, rng)
    combined.append(
        next((r for r in drift_part if "_unexpected_drift_col" in r), drift_part[-1])
    )
    dup_part = _mutate_duplicates(records, rng)
    combined.append(
        next((r for r in dup_part if r.get("_replay_conflict") is True), dup_part[-1])
    )
    combined.append(copy.deepcopy(records[0]))
    return combined


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic synthetic anomaly injector for Chaos QA probing."
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="all",
        help="Mutation class to inject (default: all).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic PRNG seed (default: 42).",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional JSON file of record objects (defaults to stdin or built-in sample).",
    )
    return parser


def _load_records(input_path: Path | None) -> list[dict[str, Any]]:
    raw = ""
    if input_path is not None:
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        raw = input_path.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()

    if not raw.strip():
        return copy.deepcopy(DEFAULT_RECORDS)

    parsed: Any = json.loads(raw)
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise ValueError("Input JSON must be a list of JSON objects.")
    return parsed


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint emitting mutated JSON records to stdout."""
    args = _build_parser().parse_args(argv)
    try:
        records = _load_records(args.input)
        mutated = inject_mutations(records, mode=args.mode, seed=args.seed)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(json.dumps(mutated, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
