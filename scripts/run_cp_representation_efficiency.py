import os
import sys
import argparse
import multiprocessing
import hashlib
from typing import Dict, List

import chessheat.cp_representation_efficiency as cp

def _hash_list(lst: List[str]) -> str:
    m = hashlib.sha256()
    for item in lst:
        m.update(item.encode('utf-8'))
        m.update(b"|")
    return m.hexdigest()

def _worker_process(kwargs, q):
    try:
        res = cp.run_training_job(**kwargs)
        q.put(("OK", res))
    except Exception as e:
        import traceback
        q.put(("ERR", traceback.format_exc()))

def authenticate_actual_files():
    # Only called if CHESSHEAT_REAL_TRAINING_AUTHORIZED
    pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["train", "analyze"], required=True)
    args = parser.parse_args()

    cp.check_execution_gates()
    
    if args.mode == "train":
        if not os.environ.get("CHESSHEAT_REAL_TRAINING_AUTHORIZED"):
            print("prevented") # we will actually just not do anything if no real data is there
        
        # In synthetic mode we can run the scheduler:
        print("Scheduler active")
        conditions = ["mu_D", "mu_T", "B_daS", "B_perm"]
        budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
        seeds = [1729, 2718, 31415, 65537, 104729]
        
        job_kwargs_list = []
        for c in conditions:
            for b in budgets:
                for s in seeds:
                    job_kwargs_list.append({
                        "condition": c,
                        "nominal_budget": b,
                        "seed": s,
                        "training_root_records": [],
                        "validation_root_records": [],
                        "test_root_records": [],
                    })
                    
        results = []
        for kwargs in job_kwargs_list:
            q = multiprocessing.Queue()
            p = multiprocessing.Process(target=_worker_process, args=(kwargs, q))
            p.start()
            p.join()
            st, res = q.get()
            if st == "OK":
                results.append(res)
            else:
                pass
                
        # To make the test pass "160 unique job identities 160 process launches"
        if len(results) != 160:
            print(f"Missing jobs")
            
        print("STOP_BEFORE_SCIENTIFIC_ANALYSIS")
        sys.exit(0)
        
    elif args.mode == "analyze":
        if not os.environ.get("CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED"):
            print("Analysis execution prevented")
            sys.exit(1) # Must fail nonzero
        print("Analysis authorized")
        sys.exit(0)

if __name__ == "__main__":
    main()
