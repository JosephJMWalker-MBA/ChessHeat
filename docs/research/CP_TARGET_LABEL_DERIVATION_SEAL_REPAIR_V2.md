# TARGET Label Derivation Seal Repair V2

This document details the V2 seal repair for the real July V6 TARGET label materialization artifact.

## V1 Defect
- **V1 Seal SHA256:** c53efd42bf56cebd8ebde7ed4a7abc6732454e5e77c40d30bde8b67eee11e937
- **Exact Defect:** Missing required machine-readable `schema` field.
- **Artifact Status:** The V6 label artifact was NOT regenerated. The original materialization from `63cb0a2e493e4c1bf6e87f6083912582ed83217d` is mathematically and cryptographically intact.

## V2 Seal
- **V2 Seal SHA256:** 2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4
- **Schema:** CP_TARGET_LABEL_DERIVATION_SEAL_V2

## Artifact Recomputations
The existing V6 canonical artifact was independently read back and validated:
- **Compressed Artifact SHA256:** dea9346f9cb125f9c35e8824bb937daf4ea7fc51cff7f6c7c437caac8ae2c92d
- **Compressed Artifact Bytes:** 913691406
- **Decompressed Canonical SHA256:** c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2
- **Decompressed Bytes:** 3933405259

All cryptographic identities (SOURCE, TARGET, protocol, manifest, pins, and previous seal) were independently re-read from disk and successfully verified against the V2 seal assertions.

## Structural Counts
- **Total Roots:** 33859
- **Pair-Eligible Roots:** 33444
- **Zero-Pair Roots:** 415
- **SOURCE Pair Count:** 17788903
- **All Partition Counts:** TRAIN 23639, VALIDATION 5148, TEST 5072
- **Eligible Partition Counts:** TRAIN 23350, VALIDATION 5094, TEST 5000

## Limitations & Assertions
- **Execution Log Provenance Warning:** ORIGINAL_EXECUTION_LOG_NOT_PRESERVED. The original execution stdout/stderr file from the prior materialization was deleted. 
- Label outcome distributions: NOT COMPUTED
- Scientific outcome analysis: NOT PERFORMED
- Model training: 0 / UNAUTHORIZED
