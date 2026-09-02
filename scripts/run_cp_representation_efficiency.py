import os
import sys
import argparse
from chessheat.cp_representation_efficiency import (
    verify_approved_sha_gate,
    verify_training_evidence_preflight,
    DerivedCache,
    build_frozen_populations,
    build_job_specs,
    run_job_specs,
    run_scientific_analysis,
    check_real_training_authorization,
    check_analysis_authorization
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["train", "analyze"], required=True)
    args = parser.parse_args()

    approved_sha = os.environ.get("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA")
    if not approved_sha:
        print("Missing CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA")
        sys.exit(1)
        
    try:
        verify_approved_sha_gate(approved_sha)
    except ValueError as e:
        print(e)
        sys.exit(1)

    if args.mode == "train":
        try:
            check_real_training_authorization()
        except ValueError as e:
            print(e)
            sys.exit(1)
            
        print("Training execution")
        # verify_training_evidence_preflight
        # cache open
        # build populations
        # build 160 job specs
        # run scheduler
        # validate 160 results
        
    elif args.mode == "analyze":
        try:
            check_analysis_authorization()
        except ValueError as e:
            print(e)
            sys.exit(1)
        run_scientific_analysis([])

if __name__ == "__main__":
    main()
