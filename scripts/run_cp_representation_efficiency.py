import argparse
import sys
import os

from chessheat.cp_representation_efficiency import (
    verify_approved_sha_gate,
    check_analysis_authorization,
    run_training_parent
)

def main():
    parser = argparse.ArgumentParser(description="ChessHeat Downstream Runner")
    parser.add_argument("--mode", required=True, choices=["train", "analyze"])
    parser.add_argument("--cache", help="Path to canonical cache")
    parser.add_argument("--cache-sha", help="Expected cache SHA")
    args = parser.parse_args()

    approved_sha = os.environ.get("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA")
    if not approved_sha:
        print("Missing CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", file=sys.stderr)
        sys.exit(1)

    if args.mode == "train":
        if not args.cache or not args.cache_sha:
            print("Missing --cache or --cache-sha for train", file=sys.stderr)
            sys.exit(1)
        run_training_parent(approved_sha, args.cache, args.cache_sha)
    else:
        verify_approved_sha_gate(approved_sha)
        check_analysis_authorization()
        print("SCIENTIFIC_ANALYSIS_PIPELINE_REMAINING_REAUDIT_TARGET")
        sys.exit(0)

if __name__ == "__main__":
    main()
