# TARGET Label Evidence V2 Audit Supplement

This supplement completes the independent hostile evidence audit of the real ChessHeat TARGET label artifact sealed by V2. The initial audit provided substantial evidence, but several independently requested audit gates were not evidenced, necessitating this supplement.

## Initial Audit Context
- **Initial Audit Commit SHA:** 2f7560a38427754404c6f1ee6115db950d18815c
- **Audit-Script Correction & Restart:** During the initial audit, the temporary audit script was corrected to properly expect the string `"SOURCE_EQUAL"` instead of `"EQUAL"` for tied SOURCE CP values. The script was subsequently restarted and successfully matched all 17,788,903 pair feature values. This record officially designates that event as: `AUDIT_SCRIPT_CORRECTION_AND_RESTART`.

## Immutability Snapshots
Complete set of hashes computed strictly **BEFORE** and **AFTER** the supplemental audit (all values are exact matches in both snapshots):
- **Artifact Compressed:** dea9346f9cb125f9c35e8824bb937daf4ea7fc51cff7f6c7c437caac8ae2c92d
- **V1 Seal:** c53efd42bf56cebd8ebde7ed4a7abc6732454e5e77c40d30bde8b67eee11e937
- **V2 Seal:** 2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4
- **SOURCE Raw:** 7eb640c572dad4c6607cfb1b5ccf99597672042e5c516f131feab02223ccfa6b
- **TARGET Raw:** d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00
- **TARGET Acq Seal V2:** 1f17ac7e27531d27bc050d49a8a1e60aa5e0ab53c26f28b2540f868c27a43dad
- **Protocol V7 JSON:** ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef
- **Manifest Decompressed:** 5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d
- **Runtime Pin:** dc707aa6d2709fcdfb108263356a8b0cab4cc459dffd29ba5524241f48ea3e22
- **Runtime Requirements:** da56c02977e00d88d897af40d227d773822aa7134d30e1d40c68e1518d666026
- **Materializer Non-Reexecution:** CONFIRMED. The canonical artifact identities remained strictly immutable throughout.

## Seal and Provenance Checks
- **Complete V2 Seal-to-Evidence Cross-Check:** PASS. Every material field inside the V2 seal JSON object explicitly matched the actual evidence value derived dynamically during the audit.
- **Runtime Pin / Runtime Requirements:** PASS.
- **CompareTyped Truth Table Result:** COMPARE_TYPED_TRUTH_TABLE_PASS. Verified CP/CP, Mate/Mate, CP/Mate comparison correctness.

## Canonical Observation and Universal Equality
- **Roots Checked for Legal-Universe Equality:** 33859
- **Legal-Universe Mismatches:** 0
- **Canonical Observation-Alignment Verdict:** PASS. Verified `len(observations) == len(canonical_acquisition_order)` and identical ordering/indices exactly for all 33,859 paired SOURCE and TARGET records.

## Information Boundary Verification
- **Authoritative Complete Key-Name Inventory:** `['a_X', 'board_arrangement_fen', 'castling_rights', 'conservative_split_group', 'd_X', 'en_passant_square', 'fullmove_number', 'halfmove_clock', 'history_available', 'history_identity', 'label_derivation_protocol', 'label_derivation_software_revision', 'm1_uci', 'm2_uci', 'manifest_sha256', 'pair_id', 'pairs', 'partition', 'protocol_id', 'protocol_json_sha256', 'root_identity', 'root_record_digest', 'schema', 'side_to_move', 'source_cp_m1', 'source_cp_m2', 'source_cp_move_count', 'source_pair_count', 'source_raw_sha256', 'source_status', 'sufficient_position', 'target_evaluable_pair_count', 'target_label', 'target_non_evaluable_pair_count', 'target_raw_sha256', 'target_seal_v2_sha256', 'target_status', 'variant']`
- **Why Prior Inventories Differed:** An incomplete `set.update(list)` or nested dictionary parsing logic in the first audit script only explored the first level of pairs (or didn't descend fully). The supplemental authoritative inventory recursively aggregated all keys correctly across all structures and arrays.
- **Information-Boundary Verdict:** PASS. Explicit programmatic rejection of forbidden leakages (`score_value`, `mate distance`, `PV`, etc.) succeeded.

## Scientific Reconfirmation
- **Decompressed Canonical SHA256:** c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2
- **Decompressed Bytes:** 3933405259
- **Record Count:** 33859
- **Execution-Log Limitation:** ORIGINAL_EXECUTION_LOG_NOT_PRESERVED.
- **Outcome Distribution Computed:** NO
- **Model Training:** 0 / UNAUTHORIZED

## Final Verdict
**TARGET_LABEL_EVIDENCE_V2_AUDIT_PASS**
