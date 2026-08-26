import hashlib
import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from chessheat.experiment import ExperimentResult
from chessheat.protocol_freeze import SourcePairFeatures, get_partition
from chessheat.attribution import compare_scores
from chessheat.models import Score

@dataclass(frozen=True)
class LabelMaterializationExpectations:
    total_roots: int
    pair_eligible_roots: int
    zero_pair_roots: int
    total_pairs: int
    all_partition_counts: Dict[str, int]
    eligible_partition_counts: Dict[str, int]

FROZEN_JULY_2026_LABEL_EXPECTATIONS = LabelMaterializationExpectations(
    total_roots=33859,
    pair_eligible_roots=33444,
    zero_pair_roots=415,
    total_pairs=17788903,
    all_partition_counts={"TRAIN": 23639, "VALIDATION": 5148, "TEST": 5072},
    eligible_partition_counts={"TRAIN": 23350, "VALIDATION": 5094, "TEST": 5000}
)

def get_target_pair_id(root_identity: str, m1_uci: str, m2_uci: str) -> str:
    domain = "CHESSHEAT_TARGET_PAIR_V1|"
    s = f"{domain}{root_identity}|{m1_uci}|{m2_uci}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _validate_failure_record(record: dict):
    if "experiment_result" in record:
        raise ValueError("FAILURE containing experiment_result")
    if "error_type" not in record or "error_message" not in record:
        raise ValueError("FAILURE missing error fields")

def _validate_source_success(data: dict, expected_perspective: str) -> list:
    if data.get("instrument_role") != "SOURCE":
        raise ValueError("wrong instrument role")
    if data.get("instrument_id") != "CP_SOURCE_SF18_50K_ISOLATED_V1":
        raise ValueError("wrong instrument ID")
    if data.get("producer_uci_name") != "Stockfish 18":
        raise ValueError("wrong producer")
    if data.get("pre_spawn_sha256") != "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374":
        raise ValueError("wrong pre SHA")
    if data.get("post_spawn_sha256") != "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374":
        raise ValueError("wrong post SHA")
    if data.get("comparison_perspective") != expected_perspective:
        raise ValueError("wrong comparison perspective")
        
    canonical_order = data.get("canonical_acquisition_order")
    if canonical_order is None or len(canonical_order) != len(set(canonical_order)):
        raise ValueError("missing canonical_acquisition_order or duplicate canonical UCI")
        
    obs = data.get("observations", [])
    if len(obs) != len(canonical_order):
        raise ValueError("wrong observation count")
        
    for i, o in enumerate(obs):
        if o.get("canonical_acquisition_index") != i:
            raise ValueError("wrong canonical index")
        if o.get("isolation_sequence_index") != i:
            raise ValueError("wrong isolation index")
        if o.get("root_move_uci") != canonical_order[i]:
            raise ValueError("wrong root_move_uci")
        if o.get("requested_nodes") != 50000:
            raise ValueError("wrong SOURCE requested_nodes")
        if o.get("score_type") not in ("cp", "mate"):
            raise ValueError("invalid score_type")
        if type(o.get("score_value")) is not int or type(o.get("score_value")) is bool:
            raise ValueError("noninteger score_value")
        if o.get("perspective") != expected_perspective:
            raise ValueError("wrong observation perspective")
            
    return canonical_order

def _validate_target_success(data: dict, expected_perspective: str, expected_order: list):
    if data.get("instrument_role") != "TARGET":
        raise ValueError("wrong instrument role")
    if data.get("instrument_id") != "CP_TARGET_SF18_250K_ISOLATED_V1":
        raise ValueError("wrong instrument ID")
    if data.get("producer_uci_name") != "Stockfish 18":
        raise ValueError("wrong producer")
    if data.get("pre_spawn_sha256") != "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374":
        raise ValueError("wrong pre SHA")
    if data.get("post_spawn_sha256") != "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374":
        raise ValueError("wrong post SHA")
    if data.get("comparison_perspective") != expected_perspective:
        raise ValueError("wrong comparison perspective")
        
    canonical_order = data.get("canonical_acquisition_order")
    if canonical_order != expected_order:
        raise ValueError("SOURCE/TARGET legal universe mismatch")
        
    obs = data.get("observations", [])
    if len(obs) != len(canonical_order):
        raise ValueError("wrong observation count")
        
    for i, o in enumerate(obs):
        if o.get("canonical_acquisition_index") != i:
            raise ValueError("wrong canonical index")
        if o.get("isolation_sequence_index") != i:
            raise ValueError("wrong isolation index")
        if o.get("root_move_uci") != canonical_order[i]:
            raise ValueError("wrong root_move_uci")
        if o.get("requested_nodes") != 250000:
            raise ValueError("wrong TARGET requested_nodes")
        if o.get("score_type") not in ("cp", "mate"):
            raise ValueError("invalid score_type")
        if type(o.get("score_value")) is not int or type(o.get("score_value")) is bool:
            raise ValueError("noninteger score_value")
        if o.get("perspective") != expected_perspective:
            raise ValueError("wrong observation perspective")
            
def derive_root_pair_labels_v3(
    manifest_record: Dict[str, Any],
    source_record: Dict[str, Any],
    target_record: Dict[str, Any],
    manifest_sha256: str,
    source_raw_sha256: str,
    target_raw_sha256: str,
    target_seal_v2_sha256: str,
    approved_sha: str
) -> Dict[str, Any]:
    
    if source_record.get("schema") != "CP_SOURCE_FEASIBILITY_RESULT_V2":
        raise ValueError("wrong outer schema")
    if target_record.get("schema") != "CP_TARGET_ACQUISITION_RESULT_V2":
        raise ValueError("wrong outer schema")
        
    s_status = source_record.get("status")
    t_status = target_record.get("status")
    if s_status not in ("SUCCESS", "FAILURE") or t_status not in ("SUCCESS", "FAILURE"):
        raise ValueError("invalid outer status")
        
    root_id = manifest_record["root_identity"]
    root_digest = manifest_record["root_record_digest"]
    
    if source_record.get("root_identity") != root_id or target_record.get("root_identity") != root_id:
        raise ValueError("wrong root identity")
    if source_record.get("root_record_digest") != root_digest or target_record.get("root_record_digest") != root_digest:
        raise ValueError("wrong root digest")
    
    persp = "white" if manifest_record["sufficient_position"]["side_to_move"] == "w" else "black"
    partition = get_partition(manifest_record["sufficient_position"])
    
    out = {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V3",
        "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V3",
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
        "partition": partition,
        "source_status": s_status,
        "target_status": t_status,
        "source_cp_move_count": 0,
        "source_pair_count": 0,
        "target_evaluable_pair_count": 0,
        "target_non_evaluable_pair_count": 0,
        "pairs": []
    }
    
    if s_status == "FAILURE":
        _validate_failure_record(source_record)
        return out
        
    if "experiment_result" not in source_record:
        raise ValueError("SUCCESS missing ExperimentResult")
        
    s_er = ExperimentResult(**source_record["experiment_result"])
    s_data = s_er.data
    if "spec_digest" in s_data and s_data["spec_digest"] != s_er.spec_digest:
        raise ValueError("wrong inner spec_digest")
        
    s_order = _validate_source_success(s_data, persp)
    
    eligible_source_moves = {}
    for obs in s_data["observations"]:
        if obs["score_type"] == "cp":
            eligible_source_moves[obs["root_move_uci"]] = obs["score_value"]
            
    out["source_cp_move_count"] = len(eligible_source_moves)
    sorted_ucis = sorted(eligible_source_moves.keys())
    k = len(sorted_ucis)
    out["source_pair_count"] = k * (k - 1) // 2
    
    target_valid = False
    
    if t_status == "SUCCESS":
        if "experiment_result" not in target_record:
            raise ValueError("SUCCESS missing ExperimentResult")
        t_er = ExperimentResult(**target_record["experiment_result"])
        t_data = t_er.data
        if "spec_digest" in t_data and t_data["spec_digest"] != t_er.spec_digest:
            raise ValueError("wrong inner spec_digest")
            
        _validate_target_success(t_data, persp, s_order)
        t_obs_map = {obs["root_move_uci"]: obs for obs in t_data["observations"]}
        target_valid = True
    else:
        _validate_failure_record(target_record)
        
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
                pair_dict["target_non_evaluable_reason"] = "TARGET_ACQUISITION_FAILURE"
                out["target_non_evaluable_pair_count"] += 1
            else:
                o1 = t_obs_map[pf.m1_uci]
                o2 = t_obs_map[pf.m2_uci]
                
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


class TargetLabelMaterializerV3:
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
        approved_sha: str,
        expectations: LabelMaterializationExpectations
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
        self.expectations = expectations

    def run(self) -> str:
        import zstandard as zstd
        import io
        
        if os.path.exists(self.output_path):
            raise FileExistsError("Output already exists")
            
        dctx = zstd.ZstdDecompressor()
        cctx = zstd.ZstdCompressor(level=3, threads=1, write_checksum=True)
        
        uncompressed_sha = hashlib.sha256()
        
        total_roots = 0
        pair_eligible_roots = 0
        zero_pair_roots = 0
        total_pairs = 0
        all_partition_counts = {"TRAIN": 0, "VALIDATION": 0, "TEST": 0}
        eligible_partition_counts = {"TRAIN": 0, "VALIDATION": 0, "TEST": 0}
        
        source_reads = 0
        target_reads = 0
        
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
                                
                                source_reads += 1
                                target_reads += 1
                                
                                s_rec = json.loads(s_line)
                                t_rec = json.loads(t_line)
                                
                                out_rec = derive_root_pair_labels_v3(
                                    manifest_record=m_rec,
                                    source_record=s_rec,
                                    target_record=t_rec,
                                    manifest_sha256=self.manifest_sha,
                                    source_raw_sha256=self.source_sha,
                                    target_raw_sha256=self.target_sha,
                                    target_seal_v2_sha256=self.target_seal_sha,
                                    approved_sha=self.approved_sha
                                )
                                
                                total_roots += 1
                                pairs_count = out_rec["source_pair_count"]
                                total_pairs += pairs_count
                                part = out_rec["partition"]
                                all_partition_counts[part] += 1
                                
                                if pairs_count == 0:
                                    zero_pair_roots += 1
                                else:
                                    pair_eligible_roots += 1
                                    eligible_partition_counts[part] += 1
                                
                                out_json = json.dumps(out_rec, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
                                uncompressed_bytes = out_json.encode('utf-8')
                                uncompressed_sha.update(uncompressed_bytes)
                                
                                w_txt.write(out_json)
                                
                            if sf.readline() or tf.readline():
                                raise ValueError("Unread source or target records remain")
                                
        if pair_eligible_roots + zero_pair_roots != total_roots:
            raise ValueError("Root accounting error")
            
        if total_roots != self.expectations.total_roots:
            raise ValueError(f"Total roots mismatch: {total_roots}")
        if pair_eligible_roots != self.expectations.pair_eligible_roots:
            raise ValueError(f"Pair eligible roots mismatch: {pair_eligible_roots}")
        if zero_pair_roots != self.expectations.zero_pair_roots:
            raise ValueError(f"Zero pair roots mismatch: {zero_pair_roots}")
        if total_pairs != self.expectations.total_pairs:
            raise ValueError(f"Total pairs mismatch: {total_pairs}")
        if all_partition_counts != self.expectations.all_partition_counts:
            raise ValueError("All partition counts mismatch")
        if eligible_partition_counts != self.expectations.eligible_partition_counts:
            raise ValueError("Eligible partition counts mismatch")
            
        if source_reads != self.expectations.total_roots:
            raise ValueError(f"Consumed {source_reads} SOURCE records")
        if target_reads != self.expectations.total_roots:
            raise ValueError(f"Consumed {target_reads} TARGET records")
            
        os.rename(self.tmp_output_path, self.output_path)
        return uncompressed_sha.hexdigest()
