from types import MappingProxyType
import pytest
import json
import os
import subprocess
import tempfile
import shutil
import pathlib
from chessheat.cp_target_labels import (
    derive_root_pair_labels_v6,
    TargetLabelMaterializerV6,
    LabelMaterializationExpectations,
    FROZEN_JULY_2026_LABEL_EXPECTATIONS,
    _validate_failure_record,
    _validate_source_success,
    _validate_target_success
)
from chessheat.attribution import compare_scores
from chessheat.models import Score
from chessheat.experiment import ExperimentResult
from scripts.run_cp_target_label_derivation import check_approved_sha

def test_compare_scores_truth_table():
    w = "white"
    def check(s1, s2, expected):
        assert compare_scores(s1, s2) == expected
        
    check(Score(type="cp", value=50, perspective=w), Score(type="cp", value=20, perspective=w), 1)
    check(Score(type="cp", value=20, perspective=w), Score(type="cp", value=50, perspective=w), -1)
    check(Score(type="cp", value=50, perspective=w), Score(type="cp", value=50, perspective=w), 0)
    check(Score(type="mate", value=1, perspective=w), Score(type="mate", value=3, perspective=w), 1)
    check(Score(type="mate", value=3, perspective=w), Score(type="mate", value=1, perspective=w), -1)
    check(Score(type="mate", value=-5, perspective=w), Score(type="mate", value=-1, perspective=w), 1)
    check(Score(type="mate", value=-1, perspective=w), Score(type="mate", value=-5, perspective=w), -1)
    check(Score(type="mate", value=2, perspective=w), Score(type="mate", value=2, perspective=w), 0)
    check(Score(type="mate", value=-2, perspective=w), Score(type="mate", value=-2, perspective=w), 0)
    check(Score(type="mate", value=5, perspective=w), Score(type="cp", value=500, perspective=w), 1)
    check(Score(type="cp", value=500, perspective=w), Score(type="mate", value=5, perspective=w), -1)
    check(Score(type="mate", value=-5, perspective=w), Score(type="cp", value=-500, perspective=w), -1)
    check(Score(type="cp", value=-500, perspective=w), Score(type="mate", value=-5, perspective=w), 1)
    check(Score(type="mate", value=1, perspective=w), Score(type="mate", value=-1, perspective=w), 1)

def create_synthetic_root(m_id="root_1"):
    return {
        "root_identity": m_id,
        "root_record_digest": "dig_1",
        "sufficient_position": {
            "board_arrangement_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "side_to_move": "w",
            "castling_rights": "KQkq",
            "en_passant_square": None,
            "halfmove_clock": 0,
            "fullmove_number": 1,
            "history_available": False,
            "history_identity": "h_1",
            "variant": "standard"
        },
        "transposition_group": "group_1",
        "inclusion": "ADMITTED"
    }

def create_payload_dict(instrument, obs_list, role="SOURCE", override_nodes=False, c_order=None):
    import json
    import hashlib
    if c_order is None:
        c_order = [o["root_move_uci"] for o in obs_list]
    for o in obs_list:
        if "requested_nodes" not in o:
            o["requested_nodes"] = 50000 if role == "SOURCE" and not override_nodes else 250000
    data = {
        "canonical_acquisition_order": c_order,
        "comparison_perspective": "white",
        "instrument_id": instrument,
        "instrument_role": role,
        "observations": obs_list,
        "post_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374",
        "pre_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374",
        "producer_uci_name": "Stockfish 18",
        "spec_digest": "spec1"
    }
    payload = json.dumps(data, sort_keys=True)
    art_digest = hashlib.sha256(f"spec1:{payload}".encode("utf-8")).hexdigest()
    return {"spec_digest": "spec1", "data_payload": payload, "artifact_digest": art_digest}

def create_obs(i, uci, stype, sval, persp="white"):
    return {
        "canonical_acquisition_index": i,
        "isolation_sequence_index": i,
        "perspective": persp,
        "root_move_uci": uci,
        "score_type": stype,
        "score_value": sval
    }

def create_record(schema, payload_or_err, status="SUCCESS"):
    rec = {
        "schema": schema,
        "root_identity": "root_1",
        "root_record_digest": "dig_1",
        "status": status
    }
    if status == "SUCCESS":
        rec["experiment_result"] = payload_or_err
    else:
        rec["error_type"] = "ERR"
        rec["error_message"] = "MSG"
    return rec

def test_canonical_m1_m2_unordered_generation_and_mate_exclusion():
    s_obs = [
        create_obs(0, "a2a3", "cp", 10),
        create_obs(1, "b2b3", "cp", 20),
        create_obs(2, "c2c3", "mate", 1)
    ]
    t_obs = [
        create_obs(0, "a2a3", "cp", 5),
        create_obs(1, "b2b3", "cp", -5),
        create_obs(2, "c2c3", "mate", -1)
    ]
    
    root = create_synthetic_root()
    s_payload = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    t_payload = create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")
    
    out = derive_root_pair_labels_v6(
        root,
        create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload),
        create_record("CP_TARGET_ACQUISITION_RESULT_V2", t_payload),
        "m_sha", "s_sha", "t_sha", "seal_sha", "appr"
    )
    
    assert out["source_cp_move_count"] == 2
    assert out["source_pair_count"] == 1
    assert len(out["pairs"]) == 1
    
    pair = out["pairs"][0]
    assert pair["m1_uci"] == "a2a3"
    assert pair["m2_uci"] == "b2b3"
    assert pair["target_label"] == "FIRST_BETTER"
    
    def check_boundary(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ["target_cp", "target_score", "target_pv", "target_nodes", "nodes", "target_mate_distance"]:
                    pytest.fail(f"Found forbidden key {k}")
                if "target" in k.lower() and k not in ["target_label", "target_non_evaluable_reason", "target_evaluable_pair_count", "target_non_evaluable_pair_count", "target_status", "target_raw_sha256", "target_seal_v2_sha256"]:
                    pytest.fail(f"Found suspicious target key {k}")
                check_boundary(v)
        elif isinstance(obj, list):
            for item in obj:
                check_boundary(item)
    check_boundary(out)

def test_target_invariance():
    s_obs = [create_obs(0, "a2a3", "cp", 10), create_obs(1, "b2b3", "cp", 20)]
    t_obs_1 = [create_obs(0, "a2a3", "cp", 5), create_obs(1, "b2b3", "cp", -5)]
    t_obs_2 = [create_obs(0, "a2a3", "cp", -50), create_obs(1, "b2b3", "cp", 50)]
    
    root = create_synthetic_root()
    s_payload = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    
    out1 = derive_root_pair_labels_v6(root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs_1, "TARGET")), "m", "s", "t", "seal", "appr")
    out2 = derive_root_pair_labels_v6(root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs_2, "TARGET")), "m", "s", "t", "seal", "appr")
    
    assert out1["source_cp_move_count"] == out2["source_cp_move_count"]
    assert out1["pairs"][0]["pair_id"] == out2["pairs"][0]["pair_id"]
    assert out1["pairs"][0]["target_label"] == "FIRST_BETTER"
    assert out2["pairs"][0]["target_label"] == "SECOND_BETTER"
    assert out1["partition"] == out2["partition"]
    assert out1["pairs"][0]["source_cp_m1"] == out2["pairs"][0]["source_cp_m1"]

def test_target_failure_invariance():
    s_obs = [create_obs(0, "a2a3", "cp", 10), create_obs(1, "b2b3", "cp", 20)]
    t_obs_1 = [create_obs(0, "a2a3", "cp", 5), create_obs(1, "b2b3", "cp", -5)]
    
    root = create_synthetic_root()
    s_payload = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    
    out1 = derive_root_pair_labels_v6(root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs_1, "TARGET")), "m", "s", "t", "seal", "appr")
    out2 = derive_root_pair_labels_v6(root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload), create_record("CP_TARGET_ACQUISITION_RESULT_V2", None, "FAILURE"), "m", "s", "t", "seal", "appr")
    
    assert out1["pairs"][0]["pair_id"] == out2["pairs"][0]["pair_id"]
    assert out2["pairs"][0]["target_label"] is None
    assert out2["pairs"][0]["target_non_evaluable_reason"] == "TARGET_ACQUISITION_FAILURE"

def test_hostile_inputs():
    import json
    import hashlib
    root = create_synthetic_root()
    s_obs = [create_obs(0, "a2a3", "cp", 10)]
    t_obs = [create_obs(0, "a2a3", "cp", 10)]

    def run_derive(s_rec, t_rec):
        derive_root_pair_labels_v6(root, s_rec, t_rec, "m", "s", "t", "seal", "appr")

    # 1. wrong SOURCE outer schema
    with pytest.raises(ValueError, match="wrong SOURCE outer schema"):
        run_derive(create_record("WRONG", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))
    
    # 2. wrong TARGET outer schema
    with pytest.raises(ValueError, match="wrong TARGET outer schema"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")), create_record("WRONG", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 3. invalid SOURCE status
    with pytest.raises(ValueError, match="invalid SOURCE status"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE"), status="UNORDERED"), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 4. invalid TARGET status
    with pytest.raises(ValueError, match="invalid TARGET status"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET"), status="UNORDERED"))

    # 5. SUCCESS missing ExperimentResult
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE"))
    del rec["experiment_result"]
    with pytest.raises(ValueError, match="SUCCESS missing ExperimentResult"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 6. FAILURE containing ExperimentResult
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", None, status="FAILURE")
    rec["experiment_result"] = {"a": 1}
    with pytest.raises(ValueError, match="FAILURE containing experiment_result"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 7. FAILURE missing error_type
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", None, status="FAILURE")
    del rec["error_type"]
    with pytest.raises(ValueError, match="FAILURE missing error_type"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 8. FAILURE missing error_message
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", None, status="FAILURE")
    del rec["error_message"]
    with pytest.raises(ValueError, match="FAILURE missing error_message"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 9. non-string error_type
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", None, status="FAILURE")
    rec["error_type"] = 123
    with pytest.raises(ValueError, match="FAILURE missing error_type"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 10. empty error_type
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", None, status="FAILURE")
    rec["error_type"] = ""
    with pytest.raises(ValueError, match="FAILURE missing error_type"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 11. non-string error_message
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", None, status="FAILURE")
    rec["error_message"] = 123
    with pytest.raises(ValueError, match="FAILURE missing error_message"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 12. empty error_message
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", None, status="FAILURE")
    rec["error_message"] = ""
    with pytest.raises(ValueError, match="FAILURE missing error_message"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 13. malformed ExperimentResult
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE"))
    del rec["experiment_result"]["data_payload"]
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 14. stale artifact_digest
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE"))
    rec["experiment_result"]["artifact_digest"] = "stale"
    with pytest.raises(ValidationError, match="artifact_digest mismatch"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 15. missing inner spec_digest
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE"))
    data = json.loads(rec["experiment_result"]["data_payload"])
    del data["spec_digest"]
    rec["experiment_result"]["data_payload"] = json.dumps(data, sort_keys=True)
    rec["experiment_result"]["artifact_digest"] = hashlib.sha256(f"spec1:{rec['experiment_result']['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="inner spec_digest"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 16. wrong inner spec_digest
    rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE"))
    data = json.loads(rec["experiment_result"]["data_payload"])
    data["spec_digest"] = "wrong"
    rec["experiment_result"]["data_payload"] = json.dumps(data, sort_keys=True)
    rec["experiment_result"]["artifact_digest"] = hashlib.sha256(f"spec1:{rec['experiment_result']['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="inner spec_digest"):
        run_derive(rec, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 17. wrong SOURCE role
    with pytest.raises(ValueError, match="wrong SOURCE role"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "TARGET")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 18. wrong TARGET role
    with pytest.raises(ValueError, match="wrong TARGET role"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "SOURCE")))

    # 19. wrong SOURCE instrument
    with pytest.raises(ValueError, match="wrong SOURCE instrument"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("WRONG", s_obs, "SOURCE")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 20. wrong TARGET instrument
    with pytest.raises(ValueError, match="wrong TARGET instrument"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("WRONG", t_obs, "TARGET")))

    # 21. wrong producer
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["producer_uci_name"] = "wrong"
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong producer"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 22. wrong pre SHA
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["pre_spawn_sha256"] = "wrong"
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong pre SHA"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 23. wrong post SHA
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["post_spawn_sha256"] = "wrong"
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong post SHA"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 24. wrong comparison perspective
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["comparison_perspective"] = "black"
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong comparison perspective"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 25. canonical order missing
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    del data["canonical_acquisition_order"]
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="canonical order missing or wrong type"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 26. canonical order non-list
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["canonical_acquisition_order"] = 123
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="canonical order missing or wrong type"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 27. empty canonical order
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["canonical_acquisition_order"] = []
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="canonical order missing or wrong type"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 28. non-string UCI
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["canonical_acquisition_order"] = [123]
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="canonical order wrong type"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 29. duplicate UCI
    with pytest.raises(ValueError, match="duplicate canonical UCI"):
        bad_obs = [create_obs(0, "a2a3", "cp", 10), create_obs(1, "a2a3", "cp", 20)]
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", bad_obs, "SOURCE")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", bad_obs, "TARGET")))

    # 30. nonlexical order
    with pytest.raises(ValueError, match="nonlexical canonical order"):
        bad_lex = [create_obs(0, "b2b3", "cp", 10), create_obs(1, "a2a3", "cp", 20)]
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", bad_lex, "SOURCE")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", bad_lex, "TARGET")))

    # 31. wrong observation count
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["observations"] = []
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong observation count"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 32. malformed observation
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    del data["observations"][0]["root_move_uci"]
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong root_move_uci"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 33. wrong canonical index
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["observations"][0]["canonical_acquisition_index"] = 99
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong canonical index"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 34. wrong isolation index
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["observations"][0]["isolation_sequence_index"] = 99
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong isolation index"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 35. wrong root_move_uci
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["observations"][0]["root_move_uci"] = "h2h3"
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong root_move_uci"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 36. wrong SOURCE requested_nodes
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["observations"][0]["requested_nodes"] = 123
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="requested_nodes"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 37. wrong TARGET requested_nodes
    d = create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")
    data = json.loads(d["data_payload"])
    data["observations"][0]["requested_nodes"] = 123
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="requested_nodes"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", d))

    # 38. invalid score_type
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["observations"][0]["score_type"] = "invalid"
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="invalid score type"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 39. bool score_value
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["observations"][0]["score_value"] = True
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="noninteger score_value"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 40. noninteger score_value
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["observations"][0]["score_value"] = 1.5
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="noninteger score_value"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 41. wrong observation perspective
    d = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    data = json.loads(d["data_payload"])
    data["observations"][0]["perspective"] = "wrong"
    d["data_payload"] = json.dumps(data, sort_keys=True)
    d["artifact_digest"] = hashlib.sha256(f"spec1:{d['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong observation perspective"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", d), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 42. wrong root identity
    s = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE"))
    s["root_identity"] = "wrong"
    with pytest.raises(ValueError, match="wrong root identity"):
        run_derive(s, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 43. wrong root digest
    s = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE"))
    s["root_record_digest"] = "wrong"
    with pytest.raises(ValueError, match="wrong root digest"):
        run_derive(s, create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")))

    # 44. SOURCE/TARGET legal-universe mismatch
    with pytest.raises(ValueError, match="SOURCE/TARGET legal-universe mismatch"):
        run_derive(create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", [create_obs(0, "a2a3", "cp", 10)], "SOURCE")), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", [create_obs(0, "b2b3", "cp", 10)], "TARGET")))

    # 45. SOURCE failure + malformed TARGET SUCCESS
    s = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", None, status="FAILURE")
    s["error_type"] = "Engine"
    s["error_message"] = "msg"
    t = create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET"))
    # break target
    t_data = json.loads(t["experiment_result"]["data_payload"])
    t_data["producer_uci_name"] = "wrong"
    t["experiment_result"]["data_payload"] = json.dumps(t_data, sort_keys=True)
    t["experiment_result"]["artifact_digest"] = hashlib.sha256(f"spec1:{t['experiment_result']['data_payload']}".encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="wrong producer"):
        run_derive(s, t)


def test_approved_sha_gate_hostile(tmp_path, monkeypatch):
    from scripts.run_cp_target_label_derivation import check_approved_sha
    assert check_approved_sha(None) == False
    assert check_approved_sha("0000000000000000000000000000000000000000") == False
    assert check_approved_sha("short") == False
    
    # Mocking check_approved_sha internally tests git directly
    import subprocess
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    def run_cmd(cmd):
        return subprocess.run(cmd, cwd=repo_dir, shell=True, capture_output=True, text=True).stdout.strip()
        
    run_cmd("git init")
    
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "chessheat").mkdir()
    (repo_dir / "scripts").mkdir()
    (repo_dir / "artifacts").mkdir()
    (repo_dir / "artifacts" / "research").mkdir()
    (repo_dir / "requirements").mkdir()
    
    bound_files = [
        "artifacts/research/target_label_derivation_runtime_pin_v1.json",
        "requirements/target-label-runtime-v1.txt",
        "src/chessheat/cp_target_labels.py",
        "src/chessheat/attribution.py",
        "src/chessheat/models.py",
        "src/chessheat/protocol_freeze.py",
        "src/chessheat/experiment.py",
        "src/chessheat/cp_root_population.py",
        "scripts/run_cp_target_label_derivation.py"
    ]
    
    for f in bound_files:
        with open(repo_dir / f, "w") as fp:
            fp.write("content")
            
    run_cmd("git add .")
    run_cmd("git config user.email 'test@test.com'")
    run_cmd("git config user.name 'test'")
    run_cmd("git commit -m 'init'")
    
    head_sha = run_cmd("git rev-parse HEAD")
    blob_sha = run_cmd("git rev-parse HEAD:src/chessheat/cp_target_labels.py")
    tree_sha = run_cmd("git rev-parse HEAD^{tree}")
    
    monkeypatch.chdir(repo_dir)
    
    assert check_approved_sha(None) == False
    assert check_approved_sha("0000000000000000000000000000000000000000") == False
    assert check_approved_sha(blob_sha) == False
    assert check_approved_sha(tree_sha) == False
    assert check_approved_sha(head_sha.upper()) == False
    
    assert check_approved_sha(head_sha) == True
    
    # Staged drift
    with open(repo_dir / "src/chessheat/cp_target_labels.py", "w") as fp: fp.write("drift")
    run_cmd("git add .")
    assert check_approved_sha(head_sha) == False
    
    # Unstaged drift
    run_cmd("git reset --hard HEAD")
    with open(repo_dir / "src/chessheat/cp_target_labels.py", "w") as fp: fp.write("drift")
    assert check_approved_sha(head_sha) == False
    
    # Runtime pin drift
    run_cmd("git reset --hard HEAD")
    with open(repo_dir / "artifacts/research/target_label_derivation_runtime_pin_v1.json", "w") as fp: fp.write("drift")
    assert check_approved_sha(head_sha) == False
    
    # Runtime requirements drift
    run_cmd("git reset --hard HEAD")
    with open(repo_dir / "requirements/target-label-runtime-v1.txt", "w") as fp: fp.write("drift")
    assert check_approved_sha(head_sha) == False

    run_cmd("git reset --hard HEAD")
    # Audit only commit
    with open(repo_dir / "docs_dummy.md", "w") as fp: fp.write("audit")
    run_cmd("git add .")
    run_cmd("git commit -m 'audit'")
    assert check_approved_sha(head_sha) == True
    
    # Stale implementation commit
    with open(repo_dir / "src/chessheat/cp_target_labels.py", "w") as fp: fp.write("new impl")
    run_cmd("git add .")
    run_cmd("git commit -m 'new impl'")
    assert check_approved_sha(head_sha) == False


def test_roundtrip_and_determinism(tmp_path):
    import json
    import hashlib
    import zstandard as zstd
    import io
    
    m_path = tmp_path / "manifest.jsonl.zst"
    s_path = tmp_path / "source.jsonl"
    t_path = tmp_path / "target.jsonl"
    
    cctx = zstd.ZstdCompressor()
    root = create_synthetic_root()
    
    s_obs = [create_obs(0, "a2a3", "cp", 10), create_obs(1, "b2b3", "cp", 20)]
    t_obs = [create_obs(0, "a2a3", "cp", 5), create_obs(1, "b2b3", "cp", -5)]
    s_payload = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    t_payload = create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")
    s_rec = create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload)
    t_rec = create_record("CP_TARGET_ACQUISITION_RESULT_V2", t_payload)
    
    with open(m_path, "wb") as f:
        with cctx.stream_writer(f) as w:
            w.write((json.dumps(root) + "\n").encode("utf-8"))
            
    with open(s_path, "w") as f: f.write(json.dumps(s_rec) + "\n")
    with open(t_path, "w") as f: f.write(json.dumps(t_rec) + "\n")
    
    exp = LabelMaterializationExpectations(
        total_roots=1,
        pair_eligible_roots=1,
        zero_pair_roots=0,
        total_pairs=1,
        all_train=0,
        all_validation=0,
        all_test=1,
        eligible_train=0,
        eligible_validation=0,
        eligible_test=1
    )
    
    out1 = tmp_path / "out1.jsonl.zst"
    mat1 = TargetLabelMaterializerV6(str(m_path), str(s_path), str(t_path), str(out1), "m", "s", "t", "seal", "appr", exp)
    u_sha1 = mat1.run()
    
    out2 = tmp_path / "out2.jsonl.zst"
    mat2 = TargetLabelMaterializerV6(str(m_path), str(s_path), str(t_path), str(out2), "m", "s", "t", "seal", "appr", exp)
    u_sha2 = mat2.run()
    
    with open(out1, "rb") as f: c_bytes1 = f.read()
    with open(out2, "rb") as f: c_bytes2 = f.read()
    
    assert u_sha1 == u_sha2
    assert c_bytes1 == c_bytes2
    
    # Prove contents
    dctx = zstd.ZstdDecompressor()
    with open(out1, "rb") as f:
        decompressed_bytes = dctx.decompress(f.read(), max_output_size=1048576)
        
    assert hashlib.sha256(decompressed_bytes).hexdigest() == u_sha1


def test_deep_freeze_rejection():
    from chessheat.cp_target_labels import FROZEN_JULY_2026_LABEL_EXPECTATIONS
    import pytest
    with pytest.raises(Exception):
        FROZEN_JULY_2026_LABEL_EXPECTATIONS.all_train = 99999


def test_runtime_pin_hostile(tmp_path, monkeypatch):
    import json
    import os
    import sys
    import hashlib
    from chessheat.cp_target_labels import _verify_runtime_pin
    import pathlib
    
    # Create dummy environment files
    env_dir = tmp_path / "env"
    env_dir.mkdir()
    
    # We will use the REAL sys.version_info and REAL sys.executable, but we will mock the native extensions and RECORD 
    # so we don't depend on the real zstandard installation in a hostile test. Actually, _verify_runtime_pin 
    # opens sys.executable, so we just hash the real one for the base_pin.
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    with open(sys.executable, "rb") as f:
        real_exe_sha = hashlib.sha256(f.read()).hexdigest()
        
    import importlib.metadata
    class DummyFile:
        def __init__(self, name, content):
            self.name = name
            self.content = content
        def read_binary(self):
            return self.content
    def mock_files(pkg):
        if pkg == "zstandard":
            return [DummyFile("RECORD", b"dummy_record")]
        return []
    def mock_version(pkg):
        if pkg == "zstandard":
            return "0.25.0"
        return "0.0.0"
    monkeypatch.setattr(importlib.metadata, "files", mock_files)
    monkeypatch.setattr(importlib.metadata, "version", mock_version)
    dummy_rec_sha = hashlib.sha256(b"dummy_record").hexdigest()
    
    zstd_dir = env_dir / "zstd"
    zstd_dir.mkdir()
    so1 = env_dir / "backend.so"
    so1.write_bytes(b"so1")
    so1_sha = hashlib.sha256(b"so1").hexdigest()
    
    pin_file = env_dir / "pin.json"
    
    orig_path = pathlib.Path
    class MockPath:
        def __new__(cls, *args, **kwargs):
            val = str(args[0])
            if "target_label_derivation_runtime_pin_v1.json" in val:
                return orig_path(pin_file)
            elif "zstandard" in val and not val.endswith(".so"):
                return orig_path(zstd_dir)
            return orig_path(*args, **kwargs)
            
    monkeypatch.setattr(pathlib, "Path", MockPath)
    
    base_pin = {
        "schema": "CHESSHEAT_TARGET_LABEL_DERIVATION_RUNTIME_V1",
        "python_version": py_ver,
        "python_executable_sha256": real_exe_sha,
        "zstandard_version": "0.25.0",
        "zstandard_record_sha256": dummy_rec_sha,
        "zstandard_native_file_sha256": {
            "backend.so": so1_sha
        },
        "compression_level": 3,
        "compression_threads": 0,
        "write_checksum": True,
        "write_content_size": False,
        "write_dict_id": False,
        "scientific_artifact_identity": "UNCOMPRESSED_CANONICAL_JSONL_SHA256",
        "compressed_artifact_identity": "TRANSPORT_ONLY"
    }
    
    import pytest
    with pytest.raises(RuntimeError, match="Missing runtime pin artifact"):
        _verify_runtime_pin()
        
    pin_file.write_text(json.dumps(base_pin))
    _verify_runtime_pin()
    
    def test_mutation(key, bad_value, err_match):
        mutated = base_pin.copy()
        mutated[key] = bad_value
        pin_file.write_text(json.dumps(mutated))
        with pytest.raises(RuntimeError, match=err_match):
            _verify_runtime_pin()
            
    test_mutation("schema", "WRONG", "Invalid runtime pin schema")
    test_mutation("python_version", "3.9.0", "Python version mismatch")
    test_mutation("python_executable_sha256", "wrong", "Python executable SHA mismatch")
    test_mutation("zstandard_version", "0.24.0", "zstandard version mismatch")
    test_mutation("zstandard_record_sha256", "wrong", "zstandard RECORD SHA mismatch")
    test_mutation("compression_level", 4, "Invalid compression_level in pin")
    test_mutation("compression_threads", 1, "Invalid compression_threads in pin")
    test_mutation("write_checksum", False, "Invalid write_checksum in pin")
    test_mutation("write_content_size", True, "Invalid write_content_size in pin")
    test_mutation("write_dict_id", True, "Invalid write_dict_id in pin")
    test_mutation("scientific_artifact_identity", "WRONG", "Invalid scientific artifact identity in pin")
    
    mutated = base_pin.copy()
    mutated["zstandard_native_file_sha256"] = {"backend.so": "wrong"}
    pin_file.write_text(json.dumps(mutated))
    with pytest.raises(RuntimeError, match="Native extension backend.so SHA mismatch"):
        _verify_runtime_pin()
        
    mutated["zstandard_native_file_sha256"] = {"missing.so": "wrong"}
    pin_file.write_text(json.dumps(mutated))
    with pytest.raises(RuntimeError, match="Missing native extension missing.so"):
        _verify_runtime_pin()
