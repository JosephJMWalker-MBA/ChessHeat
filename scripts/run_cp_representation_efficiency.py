import os
import sys
import argparse
import multiprocessing

import chessheat.cp_representation_efficiency as cp

def _worker_process(kwargs, q):
    try:
        res = cp.run_training_job(**kwargs)
        q.put(("OK", res))
    except Exception as e:
        import traceback
        q.put(("ERR", traceback.format_exc()))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["train", "analyze"], required=True)
    args = parser.parse_args()

    if args.mode == "train":
        if not os.environ.get("CHESSHEAT_REAL_TRAINING_AUTHORIZED"):
            sys.exit(1)
        cp.check_execution_gates()
        cp.authenticate_actual_files()
        
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
                    
        if len(job_kwargs_list) != 160:
            sys.exit(1)
            
        results = []
        for kwargs in job_kwargs_list:
            q = multiprocessing.Queue()
            p = multiprocessing.Process(target=_worker_process, args=(kwargs, q))
            p.start()
            p.join()
            st, res = q.get()
            if st == "OK":
                results.append(res)
                
        sys.exit(0)
        
    elif args.mode == "analyze":
        if not os.environ.get("CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED"):
            sys.exit(1)
        sys.exit(0)

if __name__ == "__main__":
    main()
