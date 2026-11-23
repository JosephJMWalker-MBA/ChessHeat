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
    parser.add_argument("--lineage", default="V6_HISTORICAL", choices=["V6_HISTORICAL", "V7_REPLICATION_1"], help="Data lineage to train on")
    parser.add_argument("--cache", help="Path to canonical cache")
    parser.add_argument("--cache-sha", help="Expected cache SHA")
    parser.add_argument("--result-dir", help="Directory for sealed worker results")
    parser.add_argument("--manifest-path", help="Path for operational completion manifest")
    parser.add_argument("--watchdog-timeout", type=float, default=None, help="Watchdog timeout in seconds per worker job")
    args = parser.parse_args()

    approved_sha = os.environ.get("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA")
    if not approved_sha:
        print("Missing CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", file=sys.stderr)
        sys.exit(1)

    if args.mode == "train":
        if args.lineage == "V7_REPLICATION_1":
            cache_path = args.cache or "artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v7_rep1.jsonl"
            cache_sha = args.cache_sha or "1b148d07c1cad975b5d21233cd7b384493a61a666cdec06b4e733b82379afba3"
            result_dir = args.result_dir or "artifacts/research/cp_representation_efficiency_training_v7_rep1/worker_results"
        elif args.lineage == "V6_HISTORICAL":
            cache_path = args.cache or "artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v6.jsonl"
            cache_sha = args.cache_sha or "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2"
            result_dir = args.result_dir or "artifacts/research/cp_representation_efficiency_training_v1/worker_results"
        else:
            print(f"Unknown lineage: {args.lineage}", file=sys.stderr)
            sys.exit(1)

        kwargs = {
            "approved_sha": approved_sha,
            "cache_path": cache_path,
            "cache_sha": cache_sha,
            "result_dir": result_dir,
            "lineage": args.lineage,
        }
        if args.manifest_path is not None:
            kwargs["manifest_path"] = args.manifest_path
        if args.watchdog_timeout is not None:
            kwargs["watchdog_timeout"] = args.watchdog_timeout

        run_training_parent(**kwargs)
    else:
        verify_approved_sha_gate(approved_sha)
        check_analysis_authorization()
        print("SCIENTIFIC_ANALYSIS_PIPELINE_REMAINING_REAUDIT_TARGET")
        sys.exit(0)

if __name__ == "__main__":
    main()
