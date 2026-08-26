import hashlib
import json
import os
import subprocess
from typing import Dict, Any, List, Optional
from chessheat.experiment import ExperimentResult
from chessheat.protocol_freeze import SourcePairFeatures, get_partition
from chessheat.attribution import compare_scores
from chessheat.models import Score

def get_target_pair_id(root_identity: str, m1_uci: str, m2_uci: str) -> str:
    domain = "CHESSHEAT_TARGET_PAIR_V1|"
    s = f"{domain}{root_identity}|{m1_uci}|{m2_uci}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def derive_root_pair_labels_v2(
    manifest_record: Dict[str, Any],
    source_status: str,
    target_status: str,
    source_payload: Optional[Dict[str, Any]],
    target_payload: Optional[Dict[str, Any]],
    manifest_sha256: str,
    source_raw_sha256: str,
    target_raw_sha256: str,
    target_seal_v2_sha256: str,
    approved_sha: str
) -> Dict[str, Any]:
    
    root_id = manifest_record["root_identity"]
    root_digest = manifest_record["root_record_digest"]
    
    out = {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V2",
        "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V2",
        "label_derivation_software_revision": approved_sha,
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
        
    er_source = ExperimentResult(**source_payload)
    s_data = er_source.data
    
    persp = "white" if manifest_record["sufficient_position"]["side_to_move"] == "w" else "black"
    
    if s_data.get("comparison_perspective") != persp:
        raise ValueError("Source comparison_perspective mismatch")
    
    eligible_source_moves = {}
    source_ucis = set()
    s_list = s_data.get("observations", [])
    
    s_canonical_order = []
    
    for i, obs in enumerate(s_list):
        if obs["canonical_acquisition_index"] != i:
            raise ValueError("Source canonical index mismatch")
        if obs["isolation_sequence_index"] != i:
            raise ValueError("Source isolation sequence mismatch")
            
        uci = obs["root_move_uci"]
        if uci in source_ucis:
            raise ValueError("Duplicate source UCI")
            
        source_ucis.add(uci)
        s_canonical_order.append(uci)
        
        if obs["score_type"] == "cp" and type(obs["score_value"]) is int:
            if obs["perspective"] != persp:
                raise ValueError("Source perspective mismatch on individual observation")
            eligible_source_moves[uci] = obs["score_value"]
            
    out["source_cp_move_count"] = len(eligible_source_moves)
    sorted_ucis = sorted(eligible_source_moves.keys())
    k = len(sorted_ucis)
    out["source_pair_count"] = k * (k - 1) // 2
    
    t_obs_map = {}
    target_valid = False
    fail_reason = None
    
    if target_status == "SUCCESS":
        if not target_payload:
            raise ValueError("Target SUCCESS but payload missing")
            
        er_target = ExperimentResult(**target_payload)
        t_data = er_target.data
        
        if t_data.get("comparison_perspective") != persp:
            raise ValueError("Target comparison_perspective mismatch")
            
        t_list = t_data.get("observations", [])
        
        if len(t_list) != len(s_list):
            raise ValueError("Move set length mismatch")
            
        target_ucis = set()
        for i, obs in enumerate(t_list):
            if obs["canonical_acquisition_index"] != i:
                raise ValueError("Target canonical index mismatch")
            if obs["isolation_sequence_index"] != i:
                raise ValueError("Target isolation sequence mismatch")
                
            uci = obs["root_move_uci"]
            if uci != s_canonical_order[i]:
                raise ValueError("Target legal-move universe mismatch")
            if uci in target_ucis:
                raise ValueError("Duplicate target UCI")
                
            target_ucis.add(uci)
            t_obs_map[uci] = obs
            
        target_valid = True
    else:
        fail_reason = "TARGET_ACQUISITION_FAILURE"
        
    pairs = []
    for i in range(k):
        for j in range(i+1, k):
            m1, cp1 = sorted_ucis[i], eligible_source_moves[sorted_ucis[i]]
            m2, cp2 = sorted_ucis[j], eligible_source_moves[sorted_ucis[j]]
            
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
                
                if o1["score_type"] not in ("cp", "mate") or o2["score_type"] not in ("cp", "mate"):
                    raise ValueError("Invalid target score type")
                if type(o1["score_value"]) is not int or type(o2["score_value"]) is not int:
                    raise ValueError("Target score value must be integer")
                if type(o1["score_value"]) is bool or type(o2["score_value"]) is bool:
                    raise ValueError("Target score value must not be boolean")
                if o1["perspective"] != persp or o2["perspective"] != persp:
                    raise ValueError("Target perspective mismatch")
                
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
            
            pairs.append(pair_dict)
            
    out["pairs"] = pairs
    return out


class TargetLabelMaterializerV2:
    def __init__(
        self,
        manifest_path: str,
        source_path: str,
        target_path: str,
        output_path: str,
        manifest_sha: str,
        source_sha: str,
        target_sha: str,
        target_seal_sha: str,
        approved_sha: str
    ):
        self.manifest_path = manifest_path
        self.source_path = source_path
        self.target_path = target_path
        self.output_path = output_path
        self.tmp_output_path = output_path + ".tmp"
        
        self.manifest_sha = manifest_sha
        self.source_sha = source_sha
        self.target_sha = target_sha
        self.target_seal_sha = target_seal_sha
        self.approved_sha = approved_sha
        
        self.total_roots = 0
        self.total_source_pair_count = 0
        self.zero_pair_roots = 0

    def run(self) -> str:
        import zstandard as zstd
        import io
        
        dctx = zstd.ZstdDecompressor()
        
        # Freeze compression config to deterministic values
        cctx = zstd.ZstdCompressor(level=3, threads=1, write_checksum=True)
        
        uncompressed_sha = hashlib.sha256()
        
        with open(self.manifest_path, "rb") as mf:
            with dctx.stream_reader(mf) as m_reader:
                m_txt = io.TextIOWrapper(m_reader, encoding='utf-8')
                
                with open(self.source_path, "r") as sf, open(self.target_path, "r") as tf:
                    with open(self.tmp_output_path, "wb") as of:
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
                                    
                                if s_rec["status"] == "SUCCESS":
                                    s_data = s_rec["experiment_result"]["data_payload"]
                                    if '"instrument_role":"SOURCE"' not in s_data:
                                        raise ValueError("Source instrument role mismatch")
                                    if '"instrument_id":"CP_SOURCE_SF18_50K_ISOLATED_V1"' not in s_data:
                                        raise ValueError("Source instrument id mismatch")
                                    if '"producer_uci_name":"Stockfish 18"' not in s_data:
                                        raise ValueError("Producer mismatch")
                                        
                                if t_rec["status"] == "SUCCESS":
                                    t_data = t_rec["experiment_result"]["data_payload"]
                                    if '"instrument_role":"TARGET"' not in t_data:
                                        raise ValueError("Target instrument role mismatch")
                                    if '"instrument_id":"CP_TARGET_SF18_250K_ISOLATED_V1"' not in t_data:
                                        raise ValueError("Target instrument id mismatch")
                                    if '"producer_uci_name":"Stockfish 18"' not in t_data:
                                        raise ValueError("Producer mismatch")
                                        
                                out_rec = derive_root_pair_labels_v2(
                                    manifest_record=m_rec,
                                    source_status=s_rec["status"],
                                    target_status=t_rec["status"],
                                    source_payload=s_rec.get("experiment_result"),
                                    target_payload=t_rec.get("experiment_result"),
                                    manifest_sha256=self.manifest_sha,
                                    source_raw_sha256=self.source_sha,
                                    target_raw_sha256=self.target_sha,
                                    target_seal_v2_sha256=self.target_seal_sha,
                                    approved_sha=self.approved_sha
                                )
                                
                                self.total_roots += 1
                                pairs_count = out_rec["source_pair_count"]
                                self.total_source_pair_count += pairs_count
                                if pairs_count == 0:
                                    self.zero_pair_roots += 1
                                
                                out_json = json.dumps(out_rec, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
                                uncompressed_bytes = out_json.encode('utf-8')
                                uncompressed_sha.update(uncompressed_bytes)
                                
                                w_txt.write(out_json)
                                
                            if sf.readline() or tf.readline():
                                raise ValueError("Unread source or target records remain")
                                
        # Enforce gates before renaming
        if self.total_roots != 33859:
            raise ValueError(f"Total roots: {self.total_roots} != 33859")
        if self.total_source_pair_count != 17788903:
            raise ValueError(f"Total pair count: {self.total_source_pair_count} != 17788903")
        if self.zero_pair_roots != 415:
            raise ValueError(f"Zero pair roots: {self.zero_pair_roots} != 415")
            
        os.rename(self.tmp_output_path, self.output_path)
        return uncompressed_sha.hexdigest()
