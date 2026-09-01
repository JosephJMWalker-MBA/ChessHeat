import hashlib
import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from types import MappingProxyType
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
    all_train: int
    all_validation: int
    all_test: int
    eligible_train: int
    eligible_validation: int
    eligible_test: int

FROZEN_JULY_2026_LABEL_EXPECTATIONS = LabelMaterializationExpectations(
    total_roots=33859,
    pair_eligible_roots=33444,
    zero_pair_roots=415,
    total_pairs=17788903,
    all_train=23639,
    all_validation=5148,
    all_test=5072,
    eligible_train=23350,
    eligible_validation=5094,
    eligible_test=5000
)

def get_target_pair_id(root_identity: str, m1_uci: str, m2_uci: str) -> str:
    domain = "CHESSHEAT_TARGET_PAIR_V1|"
    s = f"{domain}{root_identity}|{m1_uci}|{m2_uci}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _validate_failure_record(record: dict):
    if "experiment_result" in record:
        raise ValueError("FAILURE containing experiment_result")
    if type(record.get("error_type")) is not str or not record.get("error_type"):
        raise ValueError("FAILURE missing error_type")
    if type(record.get("error_message")) is not str or not record.get("error_message"):
        raise ValueError("FAILURE missing error_message")

def _validate_source_success(data: dict, expected_perspective: str) -> list:
    if data.get("instrument_role") != "SOURCE":
        raise ValueError("wrong SOURCE role")
    if data.get("instrument_id") != "CP_SOURCE_SF18_50K_ISOLATED_V1":
        raise ValueError("wrong SOURCE instrument")
    if data.get("producer_uci_name") != "Stockfish 18":
        raise ValueError("wrong producer")
    if data.get("pre_spawn_sha256") != "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374":
        raise ValueError("wrong pre SHA")
    if data.get("post_spawn_sha256") != "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374":
        raise ValueError("wrong post SHA")
    if data.get("comparison_perspective") != expected_perspective:
        raise ValueError("wrong comparison perspective")
        
    canonical_order = data.get("canonical_acquisition_order")
    if type(canonical_order) is not list or not canonical_order:
        raise ValueError("canonical order missing or wrong type")
    if any(type(x) is not str or not x for x in canonical_order):
        raise ValueError("canonical order wrong type")
    if len(canonical_order) != len(set(canonical_order)):
        raise ValueError("duplicate canonical UCI")
    if canonical_order != sorted(canonical_order):
        raise ValueError("nonlexical canonical order")
        
    obs = data.get("observations", [])
    if type(obs) is not list or len(obs) != len(canonical_order):
        raise ValueError("wrong observation count")
        
    for i, o in enumerate(obs):
        if type(o) is not dict:
            raise ValueError("malformed observation")
        if o.get("canonical_acquisition_index") != i:
            raise ValueError("wrong canonical index")
        if o.get("isolation_sequence_index") != i:
            raise ValueError("wrong isolation index")
        if o.get("root_move_uci") != canonical_order[i]:
            raise ValueError("wrong root_move_uci")
        if o.get("requested_nodes") != 50000:
            raise ValueError("wrong SOURCE requested_nodes")
        if o.get("score_type") not in ("cp", "mate"):
            raise ValueError("invalid score type")
        if type(o.get("score_value")) is not int or type(o.get("score_value")) is bool:
            raise ValueError("noninteger score_value")
        if o.get("perspective") != expected_perspective:
            raise ValueError("wrong observation perspective")
            
    return canonical_order

def _validate_target_success(data: dict, expected_perspective: str) -> list:
    if data.get("instrument_role") != "TARGET":
        raise ValueError("wrong TARGET role")
    if data.get("instrument_id") != "CP_TARGET_SF18_250K_ISOLATED_V1":
        raise ValueError("wrong TARGET instrument")
    if data.get("producer_uci_name") != "Stockfish 18":
        raise ValueError("wrong producer")
    if data.get("pre_spawn_sha256") != "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374":
        raise ValueError("wrong pre SHA")
    if data.get("post_spawn_sha256") != "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374":
        raise ValueError("wrong post SHA")
    if data.get("comparison_perspective") != expected_perspective:
        raise ValueError("wrong comparison perspective")
        
    canonical_order = data.get("canonical_acquisition_order")
    if type(canonical_order) is not list or not canonical_order:
        raise ValueError("canonical order missing or wrong type")
    if any(type(x) is not str or not x for x in canonical_order):
        raise ValueError("canonical order wrong type")
    if len(canonical_order) != len(set(canonical_order)):
        raise ValueError("duplicate canonical UCI")
    if canonical_order != sorted(canonical_order):
        raise ValueError("nonlexical canonical order")
        
    obs = data.get("observations", [])
    if type(obs) is not list or len(obs) != len(canonical_order):
        raise ValueError("wrong observation count")
        
    for i, o in enumerate(obs):
        if type(o) is not dict:
            raise ValueError("malformed observation")
        if o.get("canonical_acquisition_index") != i:
            raise ValueError("wrong canonical index")
        if o.get("isolation_sequence_index") != i:
            raise ValueError("wrong isolation index")
        if o.get("root_move_uci") != canonical_order[i]:
            raise ValueError("wrong root_move_uci")
        if o.get("requested_nodes") != 250000:
            raise ValueError("wrong TARGET requested_nodes")
        if o.get("score_type") not in ("cp", "mate"):
            raise ValueError("invalid score type")
        if type(o.get("score_value")) is not int or type(o.get("score_value")) is bool:
            raise ValueError("noninteger score_value")
        if o.get("perspective") != expected_perspective:
            raise ValueError("wrong observation perspective")
            
    return canonical_order
            
def derive_root_pair_labels_v6(
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
        raise ValueError("wrong SOURCE outer schema")
    if target_record.get("schema") != "CP_TARGET_ACQUISITION_RESULT_V2":
        raise ValueError("wrong TARGET outer schema")
        
    s_status = source_record.get("status")
    t_status = target_record.get("status")
    if s_status not in ("SUCCESS", "FAILURE"):
        raise ValueError("invalid SOURCE status")
    if t_status not in ("SUCCESS", "FAILURE"):
        raise ValueError("invalid TARGET status")
        
    root_id = manifest_record["root_identity"]
    root_digest = manifest_record["root_record_digest"]
    
    if source_record.get("root_identity") != root_id or target_record.get("root_identity") != root_id:
        raise ValueError("wrong root identity")
    if source_record.get("root_record_digest") != root_digest or target_record.get("root_record_digest") != root_digest:
        raise ValueError("wrong root digest")
    
    persp = "white" if manifest_record["sufficient_position"]["side_to_move"] == "w" else "black"
    partition = get_partition(manifest_record["sufficient_position"])
    
    s_order = None
    if s_status == "SUCCESS":
        if "experiment_result" not in source_record:
            raise ValueError("SUCCESS missing ExperimentResult")
        s_er = ExperimentResult(**source_record["experiment_result"])
        s_data = s_er.data
        if "spec_digest" not in s_data or s_data["spec_digest"] != s_er.spec_digest:
            raise ValueError("wrong inner spec_digest")
        s_order = _validate_source_success(s_data, persp)
    else:
        _validate_failure_record(source_record)
        
    target_valid = False
    if t_status == "SUCCESS":
        if "experiment_result" not in target_record:
            raise ValueError("SUCCESS missing ExperimentResult")
        t_er = ExperimentResult(**target_record["experiment_result"])
        t_data = t_er.data
        if "spec_digest" not in t_data or t_data["spec_digest"] != t_er.spec_digest:
            raise ValueError("wrong inner spec_digest")
        t_order = _validate_target_success(t_data, persp)
        if s_order is not None and t_order != s_order:
            raise ValueError("SOURCE/TARGET legal-universe mismatch")
        t_obs_map = {obs["root_move_uci"]: obs for obs in t_data["observations"]}
        target_valid = True
    else:
        _validate_failure_record(target_record)
    
    out = {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
        "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V6",
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
        return out
        
    eligible_source_moves = {}
    for obs in s_data["observations"]:
        if obs["score_type"] == "cp":
            eligible_source_moves[obs["root_move_uci"]] = obs["score_value"]
            
    out["source_cp_move_count"] = len(eligible_source_moves)
    sorted_ucis = sorted(eligible_source_moves.keys())
    k = len(sorted_ucis)
    out["source_pair_count"] = k * (k - 1) // 2
        
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



def _verify_runtime_pin():
    import sys
    import json
    import hashlib
    import importlib.metadata
    from pathlib import Path

    pin_path = Path("artifacts/research/target_label_derivation_runtime_pin_v1.json")
    if not pin_path.exists():
        raise RuntimeError("Missing runtime pin artifact")
    with open(pin_path, "r") as f:
        pin = json.load(f)


    if pin.get("schema") != "CHESSHEAT_TARGET_LABEL_DERIVATION_RUNTIME_V1":
        raise RuntimeError("Invalid runtime pin schema")
        
    if pin.get("compression_level") != 3:
        raise RuntimeError("Invalid compression_level in pin")
    if pin.get("compression_threads") != 0:
        raise RuntimeError("Invalid compression_threads in pin")
    if pin.get("write_checksum") is not True:
        raise RuntimeError("Invalid write_checksum in pin")
    if pin.get("write_content_size") is not False:
        raise RuntimeError("Invalid write_content_size in pin")
    if pin.get("write_dict_id") is not False:
        raise RuntimeError("Invalid write_dict_id in pin")
    if pin.get("scientific_artifact_identity") != "UNCOMPRESSED_CANONICAL_JSONL_SHA256":
        raise RuntimeError("Invalid scientific artifact identity in pin")
        
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if pin["python_version"] != py_ver:
        raise RuntimeError(f"Python version mismatch. Expected {pin['python_version']}, got {py_ver}")

    with open(sys.executable, "rb") as f:
        exe_sha = hashlib.sha256(f.read()).hexdigest()
    if pin["python_executable_sha256"] != exe_sha:
        raise RuntimeError("Python executable SHA mismatch")

    z_ver = importlib.metadata.version("zstandard")
    if pin["zstandard_version"] != z_ver:
        raise RuntimeError(f"zstandard version mismatch. Expected {pin['zstandard_version']}, got {z_ver}")

    record_bytes = None
    for file_obj in importlib.metadata.files("zstandard"):
        if file_obj.name == "RECORD":
            record_bytes = file_obj.read_binary()
            break
    if not record_bytes:
        raise RuntimeError("Missing zstandard RECORD")

    rec_sha = hashlib.sha256(record_bytes).hexdigest()
    if pin["zstandard_record_sha256"] != rec_sha:
        raise RuntimeError("zstandard RECORD SHA mismatch")

    import zstandard as zstd
    zstd_path = Path(zstd.__file__).parent
    for name, expected_sha in pin["zstandard_native_file_sha256"].items():
        so_path = zstd_path / name
        if not so_path.exists():
            raise RuntimeError(f"Missing native extension {name}")
        with open(so_path, "rb") as f:
            so_sha = hashlib.sha256(f.read()).hexdigest()
        if so_sha != expected_sha:
            raise RuntimeError(f"Native extension {name} SHA mismatch")


class TargetLabelMaterializerV6:
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
        _verify_runtime_pin()
        import zstandard as zstd
        import io
        
        if os.path.exists(self.output_path):
            raise FileExistsError("Output already exists")
        if os.path.exists(self.tmp_output_path):
            raise FileExistsError("Temporary output already exists")
            
        dctx = zstd.ZstdDecompressor()
        cctx = zstd.ZstdCompressor(level=3, threads=0, write_checksum=True, write_content_size=False, write_dict_id=False)
        
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
                                
                                out_rec = derive_root_pair_labels_v6(
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
                                out_bytes = out_json.encode("utf-8")
                                uncompressed_sha.update(out_bytes)
                                writer.write(out_bytes)
                                
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
        if all_partition_counts["TRAIN"] != self.expectations.all_train or all_partition_counts["VALIDATION"] != self.expectations.all_validation or all_partition_counts["TEST"] != self.expectations.all_test:
            raise ValueError("All partition counts mismatch")
        if eligible_partition_counts["TRAIN"] != self.expectations.eligible_train or eligible_partition_counts["VALIDATION"] != self.expectations.eligible_validation or eligible_partition_counts["TEST"] != self.expectations.eligible_test:
            raise ValueError("Eligible partition counts mismatch")
            
        if source_reads != self.expectations.total_roots:
            raise ValueError(f"Consumed {source_reads} SOURCE records")
        if target_reads != self.expectations.total_roots:
            raise ValueError(f"Consumed {target_reads} TARGET records")
            
        # 4. Mandatory Temp-Artifact Readback
        actual_uncompressed_sha = hashlib.sha256()
        decompressed_count = 0
        dctx2 = zstd.ZstdDecompressor()
        with open(self.tmp_output_path, "rb") as of2:
            with dctx2.stream_reader(of2) as reader2:
                buf = b""
                while True:
                    chunk = reader2.read(65536)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line_with_nl = line + b"\n"
                        actual_uncompressed_sha.update(line_with_nl)
                        
                        line_str = line.decode("utf-8")
                        rec = json.loads(line_str)
                        if rec.get("schema") != "CP_TARGET_PAIR_LABEL_ROOT_V6":
                            raise ValueError("Unexpected schema in readback")
                            
                        re_json = json.dumps(rec, sort_keys=True, separators=(",", ":"), allow_nan=False)
                        if re_json != line_str:
                            raise ValueError("Exact canonical serialization equality failed")
                            
                        decompressed_count += 1
                        
                if buf != b"":
                    raise ValueError("Unterminated final line in readback")
                    
        if actual_uncompressed_sha.hexdigest() != uncompressed_sha.hexdigest():
            raise ValueError("actual_decompressed_sha256 != uncompressed_sha")
            
        if decompressed_count != self.expectations.total_roots:
            raise ValueError("decompressed root count mismatch")
            
        os.rename(self.tmp_output_path, self.output_path)
        return uncompressed_sha.hexdigest()
