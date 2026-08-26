import hashlib
import json
from typing import Dict, Any, List, Optional
from chessheat.experiment import ExperimentResult
from chessheat.protocol_freeze import SourcePairFeatures, get_partition
from chessheat.attribution import compare_scores
from chessheat.models import Score

def get_target_pair_id(root_identity: str, m1_uci: str, m2_uci: str) -> str:
    domain = "CHESSHEAT_TARGET_PAIR_V1|"
    s = f"{domain}{root_identity}|{m1_uci}|{m2_uci}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def derive_root_pair_labels_v1(
    manifest_record: Dict[str, Any],
    source_status: str,
    target_status: str,
    source_payload: Optional[Dict[str, Any]],
    target_payload: Optional[Dict[str, Any]],
    manifest_sha256: str,
    source_raw_sha256: str,
    target_raw_sha256: str,
    target_seal_v2_sha256: str
) -> Dict[str, Any]:
    
    root_id = manifest_record["root_identity"]
    root_digest = manifest_record["root_record_digest"]
    
    # 1. Output template
    out = {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V1",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "protocol_json_sha256": "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef",
        "source_raw_sha256": source_raw_sha256,
        "target_raw_sha256": target_raw_sha256,
        "target_seal_v2_sha256": target_seal_v2_sha256,
        "manifest_sha256": manifest_sha256,
        "root_identity": root_id,
        "root_record_digest": root_digest,
        "sufficient_position": manifest_record["sufficient_position"],
        "conservative_split_group": manifest_record["transposition_group"],
        "partition": get_partition(manifest_record["sufficient_position"]),
        "source_status": source_status,
        "target_status": target_status,
        "source_cp_move_count": 0,
        "source_pair_count": 0,
        "target_evaluable_pair_count": 0,
        "target_non_evaluable_pair_count": 0,
        "pairs": []
    }
    
    if source_status != "SUCCESS":
        return out
        
    s_data = source_payload["data"]
    
    # Identify eligible source moves
    eligible_source_moves = {}
    source_ucis = set()
    s_list = s_data.get("observations", [])
    
    # check valid perspective from root
    persp = "white" if manifest_record["sufficient_position"]["side_to_move"] == "w" else "black"
    
    for obs in s_list:
        uci = obs["move_uci"]
        source_ucis.add(uci)
        if obs["score_type"] == "cp" and isinstance(obs["score_value"], int):
            if obs["perspective"] == persp:
                eligible_source_moves[uci] = obs["score_value"]
                
    out["source_cp_move_count"] = len(eligible_source_moves)
    sorted_ucis = sorted(eligible_source_moves.keys())
    k = len(sorted_ucis)
    out["source_pair_count"] = k * (k - 1) // 2
    
    # Handle target alignment and pair evaluation
    t_obs_map = {}
    target_valid = False
    fail_reason = None
    
    if target_status == "SUCCESS":
        t_data = target_payload["data"]
        t_list = t_data.get("observations", [])
        target_ucis = set(o["move_uci"] for o in t_list)
        
        # Mismatch fail-closed check
        s_canonical_order = [o["move_uci"] for o in s_list]
        t_canonical_order = [o["move_uci"] for o in t_list]
        if source_ucis != target_ucis or s_canonical_order != t_canonical_order:
            raise ValueError(f"Move set mismatch at root {root_id}")
            
        target_valid = True
        for obs in t_list:
            t_obs_map[obs["move_uci"]] = obs
    else:
        fail_reason = "TARGET_ACQUISITION_FAILURE"
        
    pairs = []
    for i in range(k):
        for j in range(i+1, k):
            m1, cp1 = sorted_ucis[i], eligible_source_moves[sorted_ucis[i]]
            m2, cp2 = sorted_ucis[j], eligible_source_moves[sorted_ucis[j]]
            
            # Using protocol SourcePairFeatures for consistent d_X, a_X
            pf = SourcePairFeatures(m1, cp1, m2, cp2)
            
            pair_dict = {
                "pair_id": get_target_pair_id(root_id, pf.m1_uci, pf.m2_uci),
                "m1_uci": pf.m1_uci,
                "m2_uci": pf.m2_uci,
                "source_cp_m1": pf.cp1,
                "source_cp_m2": pf.cp2,
                "d_X": pf.d_x,
                "a_X": pf.a_x,
                "target_label": None
            }
            
            if not target_valid:
                pair_dict["target_non_evaluable_reason"] = fail_reason
                out["target_non_evaluable_pair_count"] += 1
            else:
                o1 = t_obs_map[pf.m1_uci]
                o2 = t_obs_map[pf.m2_uci]
                
                try:
                    s1 = Score(type=o1["score_type"], value=o1["score_value"], perspective=o1["perspective"])
                    s2 = Score(type=o2["score_type"], value=o2["score_value"], perspective=o2["perspective"])
                    cmp_res = compare_scores(s1, s2)
                    
                    if cmp_res > 0:
                        pair_dict["target_label"] = "FIRST_BETTER"
                    elif cmp_res == 0:
                        pair_dict["target_label"] = "EQUAL"
                    else:
                        pair_dict["target_label"] = "SECOND_BETTER"
                    
                    out["target_evaluable_pair_count"] += 1
                except Exception as e:
                    pair_dict["target_non_evaluable_reason"] = "UNORDERED"
                    out["target_non_evaluable_pair_count"] += 1
            
            pairs.append(pair_dict)
            
    out["pairs"] = pairs
    return out


class TargetLabelMaterializerV1:
    def __init__(
        self,
        manifest_path: str,
        source_path: str,
        target_path: str,
        output_path: str,
        manifest_sha: str,
        source_sha: str,
        target_sha: str,
        target_seal_sha: str
    ):
        self.manifest_path = manifest_path
        self.source_path = source_path
        self.target_path = target_path
        self.output_path = output_path
        
        self.manifest_sha = manifest_sha
        self.source_sha = source_sha
        self.target_sha = target_sha
        self.target_seal_sha = target_seal_sha

    def run(self):
        import zstandard as zstd
        dctx = zstd.ZstdDecompressor()
        with open(self.manifest_path, "rb") as mf:
            with dctx.stream_reader(mf) as m_reader:
                # Due to memory constraints and sequential nature, we'll process 
                # line by line. But stream_reader doesn't natively do readline.
                # In python, we can wrap it with io.TextIOWrapper.
                import io
                m_txt = io.TextIOWrapper(m_reader, encoding='utf-8')
                
                with open(self.source_path, "r") as sf, open(self.target_path, "r") as tf:
                    
                    # We will output as zstd jsonl
                    cctx = zstd.ZstdCompressor()
                    with open(self.output_path, "wb") as of:
                        with cctx.stream_writer(of) as writer:
                            w_txt = io.TextIOWrapper(writer, encoding='utf-8')
                            
                            for m_line in m_txt:
                                if not m_line.strip():
                                    continue
                                m_rec = json.loads(m_line)
                                if not m_rec.get("inclusion") == "ADMITTED":
                                    continue
                                
                                s_line = sf.readline()
                                t_line = tf.readline()
                                if not s_line or not t_line:
                                    raise ValueError("Mismatch in file lengths!")
                                    
                                s_rec = json.loads(s_line)
                                t_rec = json.loads(t_line)
                                
                                if s_rec["root_identity"] != m_rec["root_identity"]:
                                    raise ValueError("Source root_identity mismatch")
                                if t_rec["root_identity"] != m_rec["root_identity"]:
                                    raise ValueError("Target root_identity mismatch")
                                if s_rec.get("root_record_digest") != m_rec.get("root_record_digest"):
                                    raise ValueError("Source root digest mismatch")
                                if t_rec.get("root_record_digest") != m_rec.get("root_record_digest"):
                                    raise ValueError("Target root digest mismatch")
                                    
                                # Mismatch fail-closed check for instrument roles
                                if s_rec["status"] == "SUCCESS":
                                    if s_rec.get("instrument_role") != "SOURCE":
                                        pass # Sometimes missing role in early records? 
                                    if s_rec["instrument_id"] != "CP_SOURCE_SF18_50K_ISOLATED_V1":
                                        raise ValueError("Source instrument mismatch")
                                if t_rec["status"] == "SUCCESS":
                                    if t_rec["instrument_id"] != "CP_TARGET_SF18_250K_ISOLATED_V1":
                                        raise ValueError("Target instrument mismatch")
                                        
                                out_rec = derive_root_pair_labels_v1(
                                    manifest_record=m_rec,
                                    source_status=s_rec["status"],
                                    target_status=t_rec["status"],
                                    source_payload=s_rec.get("experiment_result"),
                                    target_payload=t_rec.get("experiment_result"),
                                    manifest_sha256=self.manifest_sha,
                                    source_raw_sha256=self.source_sha,
                                    target_raw_sha256=self.target_sha,
                                    target_seal_v2_sha256=self.target_seal_sha
                                )
                                
                                w_txt.write(json.dumps(out_rec, sort_keys=True, separators=(",", ":")) + "\n")

