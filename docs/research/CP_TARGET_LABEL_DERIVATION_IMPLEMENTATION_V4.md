# CP TARGET Label Derivation Implementation V4

## V3 Pre-Audit Failure

The V3 implementation failed hostile re-audit due to the following critical issues:

- `TextIOWrapper` buffered output was not flushed/finalized before zstd writer closure, allowing silent truncation.
- Intended canonical SHA was calculated before proving those bytes reached the compressed artifact.
- Production roundtrip test never decompressed and content-verified output.
- Hostile/approved-SHA test coverage was materially narrower than STOP report claims.
- `spec_digest` presence was fail-open in the payload rather than strictly required.
- SOURCE-failure branch skipped full TARGET semantic validation, returning early and leaving a corrupted TARGET branch un-verified.

## V4 Architecture and Fixes

- **No Text Buffers:** Replaced `TextIOWrapper` with direct UTF-8 encoded binary writes to the zstd compressor to ensure exact buffer alignment and determinism.
- **Mandatory Readback:** The temporary `.zst` artifact is closed, re-opened, entirely decompressed, and validated line-by-line (including strict canonical parity and length checks) before atomic rename into the final artifact path. The decompressed canonical bytes must yield the same SHA256 as intended.
- **Fail-Closed Temporary State:** The execution fails closed if `.tmp` or `.zst` target files already exist, preserving evidence of aborted runs.
- **Strict Inner Payload Requirements:** `spec_digest` is now strictly enforced and cannot be missing or spoofed.
- **Comprehensive Failure Validation:** TARGET is structurally and semantically verified independently even when SOURCE resulted in a failure.
- **Deep Target Boundary Verification:** Ensures no TARGET information escapes beyond `target_label` (or non-evaluable status) using a recursive payload inspection during hostile test coverage.
- **Strict Canonical Order Constraints:** SOURCE and TARGET canonical acquisition orders must be exact non-empty string lists, non-duplicated, perfectly lexically sorted, and perfectly matched to each other.
- **Expanded Hostile Matrix:** Added strict tests covering 20+ distinct validation failures previously only claimed in reports.
