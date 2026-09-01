# TARGET Label Derivation Implementation V6

## Overview
V5 was designated `PREAUDIT_FAIL` due to deterministic implementation and provenance defects, notably regarding mutable expectations, unverified runtime pin drift, canonical buffer processing, and improper output schema identity mapping.

V6 repairs all known V5 deficiencies while retaining strict environment-binding safeguards. 

## V6 Repairs

### Output Path and Protocol Identity
- Output filename is exactly `cp_target_pair_labels_v6.jsonl.zst`.
- Replaced the erroneous V4 references. `schema = CP_TARGET_PAIR_LABEL_ROOT_V6`.
- Output records `label_derivation_protocol = CP_TARGET_LABEL_DERIVATION_V6`.
- Correctly binds the `label_derivation_software_revision` property to the V6 commit SHA. 

### Runtime Binding and Hostile Protection
- `check_approved_sha` now expands its strict 40-character `git cat-file -t commit` gating to include `artifacts/research/target_label_derivation_runtime_pin_v1.json` and `requirements/target-label-runtime-v1.txt`.
- Explicit mocked git hostility tests were written in `test_approved_sha_gate_hostile` to ensure staged and unstaged drift of the pin files forcibly abort derivation. 

### Runtime Pin Validation
- A new test suite `test_runtime_pin_hostile` validates that monkeypatched environment mismatches instantly throw `RuntimeError`.
- Validates properties down to `zstandard_record_sha256` and exact bytes of `.so` shared objects.
- V6 rewritten canonical runtime pin SHA256: `dc707aa6d2709fcdfb108263356a8b0cab4cc459dffd29ba5524241f48ea3e22`.

### Expectation Freezing
- `LabelMaterializationExpectations` refactored from mutable mappings to immutable scalar integers within a `@dataclass(frozen=True)`. Tests assert `TypeError` is raised on mutation attempt of `FROZEN_JULY_2026_LABEL_EXPECTATIONS`.

### Manifest Buffer Integrity
- Manifest buffer end verification logic swapped from `if buf.strip():` to exactly `if buf != b"":` for the final line check, strictly requiring no trailing whitespace characters or unread anomalies. 
