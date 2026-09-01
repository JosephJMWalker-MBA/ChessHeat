# TARGET Label Derivation Implementation V5

## Overview
This document describes the repair of the V4 TARGET label derivation, promoting it to V5. The V4 implementation suffered from several critical issues related to immutability, environment strictness, test coverage, and stream handling. 

## V4 Failures and Deficiencies
1. **Readback Fail-Open**: The canonical readback logic in V4 mistakenly used `if re_json != line_str.strip(): pass` instead of properly failing on inequality, effectively disabling the exact byte-level verification check.
2. **Missing Dependency Pinning**: `zstandard` was dynamically loaded from the host without checking version or compiled extensions, opening the pipeline to downstream binary drift.
3. **Inadequate Hostile Tests**: V4 possessed only 15 test cases for hostile injection.
4. **Mutable Expectations**: `LabelMaterializationExpectations` lacked deep-freezing, permitting tests to modify runtime states globally.
5. **Stream Validation Missing**: Manifest final decompression buffer merely checked `.strip()` instead of requiring an exact empty buffer `b""`.

## V5 Repairs

### 1. Hostile Environment Defenses
- Fixed the readback equivalence check to raise a `ValueError` if `re_json != line_str`.
- Updated test matrices in `test_cp_target_labels.py` from 15 to 45 unique hostile assertions. Tests now mock `git cat-file -t` to explicitly exercise `check_approved_sha` and validate `commit` objects strictly.

### 2. Runtime Environment Sealing
- Generated `target_label_derivation_runtime_pin_v1.json` which hashes the precise Python 3.13.5 executable, `zstandard` version, dependency RECORD file, and the two `.so` extensions on macOS.
- V5 materializer now enforces a fail-closed check at initialization via `_verify_runtime_pin()`. The derivation aborts instantly if the environment does not match the pinned artifact exactly.

### 3. Zstd Determinism Options
- Compressor instances are now constructed with:
  `cctx = zstd.ZstdCompressor(level=3, threads=0, write_checksum=True, write_content_size=False, write_dict_id=False)`
  This removes multithreading overhead and prevents undocumented dictionary headers from changing the output stream layout between architecture executions.

### 4. Git Object Verification
- The `check_approved_sha` method enforces exact 40-character lowercase hexadecimal lengths and strictly checks that the repository points to a valid `commit` (rather than a tree or blob).

### 5. Strict Expectation Types
- Used `MappingProxyType` to deep-freeze all partition counting dictionaries, preventing any accidental mutation during processing loops.
