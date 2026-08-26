import pytest
from chessheat.cp_target_labels import derive_root_pair_labels_v1

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

def create_payload(instrument, obs_list):
    return {
        "spec_digest": "spec1",
        "artifact_digest": "art1",
        "data": {
            "observations": obs_list,
            "pre_sha256": "sf",
            "post_sha256": "sf"
        }
    }

def test_canonical_m1_m2_unordered_generation_and_mate_exclusion():
    # Source has CP a2a3 (10), CP b2b3 (20), MATE c2c3 (1)
    s_obs = [
        {"move_uci": "a2a3", "score_type": "cp", "score_value": 10, "perspective": "white"},
        {"move_uci": "b2b3", "score_type": "cp", "score_value": 20, "perspective": "white"},
        {"move_uci": "c2c3", "score_type": "mate", "score_value": 1, "perspective": "white"},
    ]
    # Target has CP a2a3 (5), CP b2b3 (-5), MATE c2c3 (-1)
    t_obs = [
        {"move_uci": "a2a3", "score_type": "cp", "score_value": 5, "perspective": "white"},
        {"move_uci": "b2b3", "score_type": "cp", "score_value": -5, "perspective": "white"},
        {"move_uci": "c2c3", "score_type": "mate", "score_value": -1, "perspective": "white"},
    ]
    
    root = create_synthetic_root()
    s_payload = create_payload("CP_SOURCE_SF18_50K_ISOLATED_V1", s_obs)
    t_payload = create_payload("CP_TARGET_SF18_250K_ISOLATED_V1", t_obs)
    
    out = derive_root_pair_labels_v1(
        root, "SUCCESS", "SUCCESS", s_payload, t_payload,
        "m_sha", "s_sha", "t_sha", "seal_sha"
    )
    
    assert out["source_cp_move_count"] == 2 # c2c3 is mate
    assert out["source_pair_count"] == 1 # 2 choose 2
    assert len(out["pairs"]) == 1
    
    pair = out["pairs"][0]
    assert pair["m1_uci"] == "a2a3"
    assert pair["m2_uci"] == "b2b3"
    assert pair["source_cp_m1"] == 10
    assert pair["source_cp_m2"] == 20
    assert pair["d_X"] == "SOURCE_SECOND_BETTER"
    assert pair["a_X"] == 10
    
    # Target: a2a3 (5) vs b2b3 (-5). 5 > -5, so FIRST_BETTER
    assert pair["target_label"] == "FIRST_BETTER"
    
    # Information boundary check
    keys = set(pair.keys())
    assert "target_cp" not in keys
    assert "target_score" not in keys
    assert "target_score_value" not in keys
    assert "target_mate" not in keys
    assert "target_mate_distance" not in keys

def test_target_invariance():
    s_obs = [
        {"move_uci": "a2a3", "score_type": "cp", "score_value": 10, "perspective": "white"},
        {"move_uci": "b2b3", "score_type": "cp", "score_value": 20, "perspective": "white"},
    ]
    t_obs_1 = [
        {"move_uci": "a2a3", "score_type": "cp", "score_value": 5, "perspective": "white"},
        {"move_uci": "b2b3", "score_type": "cp", "score_value": -5, "perspective": "white"},
    ]
    t_obs_2 = [
        {"move_uci": "a2a3", "score_type": "cp", "score_value": -50, "perspective": "white"},
        {"move_uci": "b2b3", "score_type": "cp", "score_value": 50, "perspective": "white"},
    ]
    
    root = create_synthetic_root()
    s_payload = create_payload("src", s_obs)
    
    out1 = derive_root_pair_labels_v1(root, "SUCCESS", "SUCCESS", s_payload, create_payload("tgt", t_obs_1), "m", "s", "t", "seal")
    out2 = derive_root_pair_labels_v1(root, "SUCCESS", "SUCCESS", s_payload, create_payload("tgt", t_obs_2), "m", "s", "t", "seal")
    
    # Assert structural invariance
    assert out1["source_cp_move_count"] == out2["source_cp_move_count"]
    assert out1["source_pair_count"] == out2["source_pair_count"]
    assert out1["pairs"][0]["pair_id"] == out2["pairs"][0]["pair_id"]
    assert out1["pairs"][0]["d_X"] == out2["pairs"][0]["d_X"]
    
    # Only label changes
    assert out1["pairs"][0]["target_label"] == "FIRST_BETTER"
    assert out2["pairs"][0]["target_label"] == "SECOND_BETTER"
    
def test_target_failure_invariance():
    s_obs = [
        {"move_uci": "a2a3", "score_type": "cp", "score_value": 10, "perspective": "white"},
        {"move_uci": "b2b3", "score_type": "cp", "score_value": 20, "perspective": "white"},
    ]
    root = create_synthetic_root()
    s_payload = create_payload("src", s_obs)
    
    t_obs_1 = [
        {"move_uci": "a2a3", "score_type": "cp", "score_value": 5, "perspective": "white"},
        {"move_uci": "b2b3", "score_type": "cp", "score_value": -5, "perspective": "white"},
    ]
    
    out1 = derive_root_pair_labels_v1(root, "SUCCESS", "SUCCESS", s_payload, create_payload("tgt", t_obs_1), "m", "s", "t", "seal")
    out2 = derive_root_pair_labels_v1(root, "SUCCESS", "FAILURE", s_payload, None, "m", "s", "t", "seal")
    
    assert out1["pairs"][0]["pair_id"] == out2["pairs"][0]["pair_id"]
    assert out2["pairs"][0]["target_label"] is None
    assert out2["pairs"][0]["target_non_evaluable_reason"] == "TARGET_ACQUISITION_FAILURE"

def test_move_set_mismatch_fail_closed():
    s_obs = [{"move_uci": "a2a3", "score_type": "cp", "score_value": 10, "perspective": "white"}]
    t_obs = [{"move_uci": "b2b3", "score_type": "cp", "score_value": 10, "perspective": "white"}]
    
    root = create_synthetic_root()
    s_payload = create_payload("src", s_obs)
    t_payload = create_payload("tgt", t_obs)
    
    with pytest.raises(ValueError, match="Move set mismatch"):
        derive_root_pair_labels_v1(root, "SUCCESS", "SUCCESS", s_payload, t_payload, "m", "s", "t", "seal")
        
def test_zero_source_pair():
    s_obs = [{"move_uci": "a2a3", "score_type": "cp", "score_value": 10, "perspective": "white"}]
    t_obs = [{"move_uci": "a2a3", "score_type": "cp", "score_value": 10, "perspective": "white"}]
    
    root = create_synthetic_root()
    s_payload = create_payload("src", s_obs)
    t_payload = create_payload("tgt", t_obs)
    
    out = derive_root_pair_labels_v1(root, "SUCCESS", "SUCCESS", s_payload, t_payload, "m", "s", "t", "seal")
    assert out["source_cp_move_count"] == 1
    assert out["source_pair_count"] == 0
    assert len(out["pairs"]) == 0

def test_compare_typed_binding(monkeypatch):
    # Ensure compare_scores is called
    import chessheat.attribution
    called = []
    orig = chessheat.attribution.compare_scores
    def fake_compare(a, b):
        called.append(True)
        return orig(a, b)
    monkeypatch.setattr("chessheat.cp_target_labels.compare_scores", fake_compare)
    
    s_obs = [
        {"move_uci": "a2a3", "score_type": "cp", "score_value": 10, "perspective": "white"},
        {"move_uci": "b2b3", "score_type": "cp", "score_value": 20, "perspective": "white"},
    ]
    t_obs = [
        {"move_uci": "a2a3", "score_type": "cp", "score_value": 5, "perspective": "white"},
        {"move_uci": "b2b3", "score_type": "cp", "score_value": 5, "perspective": "white"},
    ]
    
    root = create_synthetic_root()
    out = derive_root_pair_labels_v1(root, "SUCCESS", "SUCCESS", create_payload("src", s_obs), create_payload("tgt", t_obs), "m", "s", "t", "seal")
    assert out["pairs"][0]["target_label"] == "EQUAL"
    assert len(called) == 1
