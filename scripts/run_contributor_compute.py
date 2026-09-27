#!/usr/bin/env python3
"""CLI for ChessHeat contributor-compute packets."""

import argparse
import json
import sys

from chessheat.contributor_compute import (
    ContributorComputeError,
    preflight,
    run_packet,
    verify_bundle,
)


def _print(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(
        description="ChessHeat contributor compute provenance wrapper"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("preflight", help="Verify a packet and local environment without executing")
    p.add_argument("--packet", required=True)
    p.add_argument("--repo-root", default=".")
    p.add_argument("--engine-path")

    r = sub.add_parser("run", help="Execute or resume an authorized work packet")
    r.add_argument("--packet", required=True)
    r.add_argument("--repo-root", default=".")
    r.add_argument("--bundle", required=True, help="Bundle directory outside the Git work tree")
    r.add_argument("--engine-path")
    r.add_argument("--max-workers", type=int, default=1)

    v = sub.add_parser("verify", help="Verify a completed contributor bundle")
    v.add_argument("--bundle", required=True)

    args = parser.parse_args()

    try:
        if args.command == "preflight":
            packet, report, environment = preflight(
                args.packet, args.repo_root, args.engine_path
            )
            _print(
                {
                    "packet_id": packet["packet_id"],
                    "preflight": report,
                    "environment": environment,
                }
            )
        elif args.command == "run":
            _print(
                run_packet(
                    args.packet,
                    args.repo_root,
                    args.bundle,
                    engine_path=args.engine_path,
                    max_workers=args.max_workers,
                )
            )
        else:
            _print(verify_bundle(args.bundle))
    except ContributorComputeError as exc:
        print(f"Contributor compute error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Contributor compute interrupted; completed work remains in the bundle.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
