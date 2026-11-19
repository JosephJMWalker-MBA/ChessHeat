# CP Target Label Derivation Protocol — Replication V1 (`V7_REPLICATION_1`)

**Status**: PROSPECTIVE PROTOCOL SPECIFICATION  
**Parent Protocol**: `CP_TARGET_LABEL_DERIVATION_V6` / `CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7`  
**Date**: November 19, 2026  
**Governing Invariant**: *The mathematics needs to earn the color.*

---

## 1. Context & Motivation

Following the empirical audit of the reconstructed canonical dataset ([`STAGE_1_SOURCE_RECONSTRUCTION_AUDIT.md`](file:///Users/josephjmwalker-mba/.gemini/antigravity/brain/98be6610-9999-4088-a66a-c829a6cba095/STAGE_1_SOURCE_RECONSTRUCTION_AUDIT.md)):
1. **Reconstructed SOURCE Data** (`artifacts/research/cp_source_feasibility_2026_07/reconstruction_attempt_1/cp_source_root_results_v2.jsonl`):
   - Demonstrates **100% exact parity** across byte length (`764,529,894` bytes), record count (`33,859`), CP child alternatives (`1,037,581`), mate child alternatives (`30,083`), eligible roots (`33,444`), zero-pair roots (`415`), total CP/CP pairs (`17,788,903`), distribution percentiles (Min, Med, P90, P95, Max), and partition splits (Train: 23,639/23,350/289; Val: 5,148/5,094/54; Test: 5,072/5,000/72).
   - Exhibits cryptographic hash `9cfe28a13f185e207ac42c5708597b0577ef93f4fce29ca482e4e6a9c8d83774` due to shallow search leaf-node evaluation shifts across platform environments.
2. **Reconstructed TARGET Data** (`artifacts/research/cp_target_acquisition_2026_07/raw/cp_target_root_results_v2.jsonl`):
   - Proven **100% bit-identical** to the canonical historical receipt via the 16-root probe match (`4a7e01366dc58ad589c507b997bdca90da40391bb7bf0427f246196ac965dfe1`, `337,585` bytes).
   - Guaranteed full-corpus canonical SHA-256: `d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00` (`770,029,516` bytes).

To preserve complete research provenance and scientific integrity without overwriting historical seals or substituting unearned hashes, this protocol formally specifies the **Replication V1** derivation lineage.

---

## 2. Bound Input Artifacts

| Dependency | Bound Path | Required SHA-256 | Required Bytes | Records |
| :--- | :--- | :--- | :--- | :--- |
| **Manifest** | `artifacts/research/cp_source_feasibility_2026_07/cp_root_population_manifest_v2.jsonl.zst` | `5a013e64...` (decompressed) | `33,859` admitted | `40,038` |
| **SOURCE Raw** | `artifacts/research/cp_source_feasibility_2026_07/reconstruction_attempt_1/cp_source_root_results_v2.jsonl` | `9cfe28a13f185e207ac42c5708597b0577ef93f4fce29ca482e4e6a9c8d83774` | `764,529,894` | `33,859` |
| **TARGET Raw** | `artifacts/research/cp_target_acquisition_2026_07/raw/cp_target_root_results_v2.jsonl` | `d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00` | `770,029,516` | `33,859` |
| **Protocol JSON**| `artifacts/research/cp_representation_efficiency_protocol_v7.json` | `ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef` | - | - |

---

## 3. Mathematical & Derivation Invariance

The derivation logic under `V7_REPLICATION_1` is **strictly identical** to `CP_TARGET_LABEL_DERIVATION_V6`:
- **Pair Construction**: For every admitted root with $\ge 2$ finite SOURCE CP alternatives, all unordered pairs $(m_1, m_2)$ with $m_1 < m_2$ (lexicographical UCI order) are formed.
- **Direction ($d_X$) & Amplitude ($a_X$)**: Computed directly from SOURCE evaluations.
- **Target Labeling**: Evaluated via `chessheat.attribution.compare_scores` on typed TARGET observations.
- **Mate Policy**: Typed mate observations remain ordered; mate/mate and mate/cp comparisons comply with the semantic contract.
- **Target Failure**: Unobserved or failed target evaluations produce non-evaluable pairs; zero TARGET-evaluable pairs drop the root during training with nominal budget preservation and no replacement.

---

## 4. Output Artifacts & Sealing

- **Compressed Transport Artifact**: `artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v7_rep1.jsonl.zst`
- **Execution Cache**: `artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v7_rep1.jsonl`
- **Derivation Seal**: `artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v7_rep1.json`

The seal explicitly records both the historical provenance lineage and the replication hashes, ensuring full transparency in all subsequent publications and benchmark reports.

---

## 5. Execution Governance

- **Target Acquisition**: Authorized under Stage 2 execution admission.
- **Label Derivation**: Blocked pending completion and verification of Target Acquisition.
- **Downstream Model Training**: Strictly UNAUTHORIZED (`CHESSHEAT_REAL_TRAINING_AUTHORIZED=0`).
