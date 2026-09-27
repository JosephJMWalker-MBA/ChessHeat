#!/usr/bin/env python3
"""Deterministic non-scientific job used to validate contributor-compute plumbing."""

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "CHESSHEAT_CONTRIBUTOR_REFERENCE_RESULT_V1"


def main():
    parser = argparse.ArgumentParser(description="ChessHeat contributor compute reference job")
    parser.add_argument("--work-unit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = {
        "schema": SCHEMA,
        "work_unit_id": args.work_unit,
        "reference_digest": hashlib.sha256(
            f"CHESSHEAT_CONTRIBUTOR_REFERENCE_V1|{args.work_unit}".encode("utf-8")
        ).hexdigest(),
        "scientific_admission": "NONE_REFERENCE_ONLY",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
