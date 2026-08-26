# CP_TARGET_ACQUISITION_EVIDENCE_V2

- **V1 seal defect:** The preliminary seal V1 erroneously conflated `manifest_record_count` with `admitted_root_count`. It also did not programmatically enforce exact completion equality gates.
- **Acquisition unchanged:** The raw TARGET bytes were unchanged and acquisition was not repeated. V1 acquisition remains authoritative raw evidence.
- **Explicit execution authorization:** GRANTED (2026-08-22)
- **Implementation SHA:** 1c8fbb778a7bffb76d149fa1ea00aa3f8c054ce8
- **Authoritative supplemental audit SHA:** 29c4794acdb32faed7deb7c07bcca3a60e41d650
- **Stockfish SHA:** ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374
- **TARGET instrument:** CP_TARGET_SF18_250K_ISOLATED_V1
- **Node budget:** 250,000 nodes per legal child
- **Manifest SHA:** 5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d
- **Manifest records:** 40,038
- **Admitted root count:** 33,859
- **Raw artifact path:** artifacts/research/cp_target_acquisition_2026_07/raw/cp_target_root_results_v2.jsonl
- **Raw artifact SHA256:** d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00
- **Raw artifact bytes:** 770029516
- **Exact root count:** 33,859
- **SUCCESS/FAILURE counts:** 33,859 SUCCESS / 0 FAILURE
- **Total observations:** 1,067,664
- **CP-typed observations:** 1,030,419
- **Mate-typed observations:** 37,245
- **Failure-type counts:** 0
- **Maximum engine session epoch:** 1
- **Full production resume validation result:** PASS
- **Population-prefix validation result:** PASS
- **Exact completion equality gates:** PASS
- **Machine-readable seal V2 path:** artifacts/research/cp_target_acquisition_2026_07/cp_target_acquisition_seal_v2.json
- **Machine-readable seal V2 SHA256:** 1f17ac7e27531d27bc050d49a8a1e60aa5e0ab53c26f28b2540f868c27a43dad
- **SOURCE untouch/isolation:** VERIFIED (untouched)
- **Claimed ceiling:** Unchanged
- **TARGET labels:** 0
- **Pair analysis:** 0
- **Model training:** 0

This repaired evidence asserts acquisition completeness relative to the frozen admitted-root population, properly disentangles the total manifest size, enforces strict count equality gates, and guarantees that no downstream analysis was performed.
