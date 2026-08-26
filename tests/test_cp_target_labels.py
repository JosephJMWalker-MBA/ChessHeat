import pytest
import json
import os
import subprocess
import tempfile
import shutil
import pathlib
from chessheat.cp_target_labels import (
    derive_root_pair_labels_v3,
    TargetLabelMaterializerV3,
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
        "producer_uci_name": "Stockfish 18"
    }
    er = ExperimentResult.create("spec1", data)
    return er.model_dump()

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
    
    out = derive_root_pair_labels_v3(
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
    
    keys = set(pair.keys())
    assert "target_cp" not in keys
    assert "target_score" not in keys

def test_target_invariance():
    s_obs = [create_obs(0, "a2a3", "cp", 10), create_obs(1, "b2b3", "cp", 20)]
    t_obs_1 = [create_obs(0, "a2a3", "cp", 5), create_obs(1, "b2b3", "cp", -5)]
    t_obs_2 = [create_obs(0, "a2a3", "cp", -50), create_obs(1, "b2b3", "cp", 50)]
    
    root = create_synthetic_root()
    s_payload = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    
    out1 = derive_root_pair_labels_v3(root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs_1, "TARGET")), "m", "s", "t", "seal", "appr")
    out2 = derive_root_pair_labels_v3(root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs_2, "TARGET")), "m", "s", "t", "seal", "appr")
    
    assert out1["source_cp_move_count"] == out2["source_cp_move_count"]
    assert out1["pairs"][0]["pair_id"] == out2["pairs"][0]["pair_id"]
    assert out1["pairs"][0]["target_label"] == "FIRST_BETTER"
    assert out2["pairs"][0]["target_label"] == "SECOND_BETTER"

def test_target_failure_invariance():
    s_obs = [create_obs(0, "a2a3", "cp", 10), create_obs(1, "b2b3", "cp", 20)]
    t_obs_1 = [create_obs(0, "a2a3", "cp", 5), create_obs(1, "b2b3", "cp", -5)]
    
    root = create_synthetic_root()
    s_payload = create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")
    
    out1 = derive_root_pair_labels_v3(root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload), create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs_1, "TARGET")), "m", "s", "t", "seal", "appr")
    out2 = derive_root_pair_labels_v3(root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", s_payload), create_record("CP_TARGET_ACQUISITION_RESULT_V2", None, "FAILURE"), "m", "s", "t", "seal", "appr")
    
    assert out1["pairs"][0]["pair_id"] == out2["pairs"][0]["pair_id"]
    assert out2["pairs"][0]["target_label"] is None
    assert out2["pairs"][0]["target_non_evaluable_reason"] == "TARGET_ACQUISITION_FAILURE"

def test_hostile_inputs():
    root = create_synthetic_root()
    s_obs = [create_obs(0, "a2a3", "cp", 10)]
    t_obs = [create_obs(0, "b2b3", "cp", 10)]
    
    # 1. Wrong schema
    with pytest.raises(ValueError, match="wrong outer schema"):
        derive_root_pair_labels_v3(
            root, create_record("WRONG", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs, "SOURCE")),
            create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs, "TARGET")),
            "m", "s", "t", "seal", "appr"
        )
        
    # 2. Duplicate UCI
    bad_obs = [create_obs(0, "a2a3", "cp", 10), create_obs(1, "a2a3", "cp", 20)]
    with pytest.raises(ValueError, match="missing canonical_acquisition_order or duplicate canonical UCI"):
        derive_root_pair_labels_v3(
            root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", bad_obs, "SOURCE")),
            create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", bad_obs, "TARGET")),
            "m", "s", "t", "seal", "appr"
        )
        
    # 3. Source/Target legal universe mismatch
    with pytest.raises(ValueError, match="SOURCE/TARGET legal universe mismatch"):
        derive_root_pair_labels_v3(
            root, create_record("CP_SOURCE_FEASIBILITY_RESULT_V2", create_payload_dict("CP_SOURCE_SF18_50K_ISOLATED_V1", [create_obs(0, "a2a3", "cp", 10)], "SOURCE")),
            create_record("CP_TARGET_ACQUISITION_RESULT_V2", create_payload_dict("CP_TARGET_SF18_250K_ISOLATED_V1", [create_obs(0, "b2b3", "cp", 10)], "TARGET")),
            "m", "s", "t", "seal", "appr"
        )

def test_approved_sha_gate_hostile(tmp_path, monkeypatch):
    assert check_approved_sha(None) == False
    assert check_approved_sha("0000000000000000000000000000000000000000") == False

def test_roundtrip_and_determinism(tmp_path):
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
        all_partition_counts={"TRAIN": 0, "VALIDATION": 0, "TEST": 1},
        eligible_partition_counts={"TRAIN": 0, "VALIDATION": 0, "TEST": 1}
    )
    
    out1 = tmp_path / "out1.jsonl.zst"
    mat1 = TargetLabelMaterializerV3(str(m_path), str(s_path), str(t_path), str(out1), "m", "s", "t", "seal", "appr", exp)
    u_sha1 = mat1.run()
    
    out2 = tmp_path / "out2.jsonl.zst"
    mat2 = TargetLabelMaterializerV3(str(m_path), str(s_path), str(t_path), str(out2), "m", "s", "t", "seal", "appr", exp)
    u_sha2 = mat2.run()
    
    with open(out1, "rb") as f: c_bytes1 = f.read()
    with open(out2, "rb") as f: c_bytes2 = f.read()
    
    assert u_sha1 == u_sha2
    assert c_bytes1 == c_bytes2
