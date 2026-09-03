import os
import sys
import json
import hashlib
import subprocess

def run_job(process_id):
    script = """
import os
os.environ["CHESSHEAT_ML_RUNTIME_ID"] = "CHESSHEAT_ML_RUNTIME_V3"
os.environ["PYTHONHASHSEED"] = "0"
os.environ["PYTORCH_MPS_FAST_MATH"] = "0"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
os.environ["PYTORCH_MPS_PREFER_METAL"] = "0"

import chessheat.cp_representation_efficiency as cp
import hashlib
from chessheat.cp_target_labels import SourcePairFeatures

def make_root(rid, n_pairs):
    return {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
        "root_identity": rid,
        "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V6",
        "target_evaluator_version": "16.1",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "partition": "TRAIN",
        "sufficient_position": {
            "board_arrangement_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "side_to_move": "w",
            "castling_rights": "KQkq",
            "ep_square": None
        },
        "target_evaluable_pair_count": n_pairs,
        "target_non_evaluable_pair_count": 0,
        "source_pair_count": n_pairs,
        "pairs": [
            {
                "pair_id": hashlib.sha256(f"CHESSHEAT_TARGET_PAIR_V1|{rid}|a1{chr(97+i)}1|e7e5".encode()).hexdigest(),
                "m1_uci": f"a1{chr(97+i)}1", "m2_uci": "e7e5",
                "source_cp_m1": 100, "source_cp_m2": -50,
                "d_X": SourcePairFeatures(f"a1{chr(97+i)}1", 100, "e7e5", -50).d_x,
                "a_X": SourcePairFeatures(f"a1{chr(97+i)}1", 100, "e7e5", -50).a_x,
                "target_label": "FIRST_BETTER",
                "m1_heat": 0.5, "m2_heat": -0.5
            } for i in range(n_pairs)
        ]
    }

train = [make_root(f"CHESSHEAT_TARGET_ROOT_tr{i}", 1) for i in range(250)]
train.sort(key=lambda x: cp.canonical_budget_order(x["root_identity"]))
val = [make_root(f"CHESSHEAT_TARGET_ROOT_v{i}", 1) for i in range(2)]
test = [make_root(f"CHESSHEAT_TARGET_ROOT_t{i}", 1) for i in range(2)]

res = cp.run_training_job(
    condition="mu_D", nominal_budget=250, seed=1729,
    training_root_records=train, validation_root_records=val, test_root_records=test,
    nominal_root_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in train]),
    validation_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in val]),
    test_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in test])
)

out = {
    "condition": res["condition"],
    "nominal_budget": res["nominal_budget"],
    "seed": res["seed"],
    "nominal_root_population_digest": res["nominal_root_population_digest"],
    "effective_root_population_digest": res["effective_root_population_digest"],
    "validation_population_digest": res["validation_population_digest"],
    "test_population_digest": res["test_population_digest"],
    "epochs_completed": res["epochs_completed"],
    "best_epoch": res["best_epoch"],
    "validation_trace": res["validation_trace"],
    "canonical_model_state_sha": res["canonical_model_state_sha"],
    "test_root_ids": res["test_root_ids"],
    "test_root_losses": res["test_root_losses"]
}

import json
print(json.dumps(out))
"""
    env = os.environ.copy()
    env["CHESSHEAT_REPO_ROOT"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env["PYTHONPATH"] = "src:."
    p = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    if p.returncode != 0:
        print(f"Error in process {process_id}:", p.stderr)
        sys.exit(1)
    
    # We grep for lines starting with "{" to handle numpy warnings
    for line in p.stdout.splitlines():
        if line.startswith("{"):
            return json.loads(line)
    
    print(f"No JSON output from process {process_id}:", p.stdout)
    sys.exit(1)

out1 = run_job(1)
out2 = run_job(2)

def hash_obj(obj):
    b = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()

sha1 = hash_obj(out1)
sha2 = hash_obj(out2)

assert sha1 == sha2
assert out1 == out2

print(json.dumps({
    "run1": out1,
    "run2": out2,
    "sha1": sha1,
    "sha2": sha2,
    "exact_match": (out1 == out2 and sha1 == sha2)
}, indent=2))
