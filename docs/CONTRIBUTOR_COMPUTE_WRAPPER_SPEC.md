# Contributor Compute Wrapper Specification v1

## Purpose

The contributor-compute wrapper turns an authorized ChessHeat work packet into an auditable execution bundle.

It is infrastructure, not scientific authorization.

The wrapper must remain outside the core measurement semantics and must not silently adapt scientific settings to hardware.

## Commands

### Preflight only

```bash
python scripts/run_contributor_compute.py preflight \
  --packet path/to/packet.json \
  --repo-root .
```

If the packet requires an external engine:

```bash
python scripts/run_contributor_compute.py preflight \
  --packet path/to/packet.json \
  --repo-root . \
  --engine-path /path/to/stockfish
```

Preflight verifies identities and reports the environment but never executes work units.

### Run or resume

The bundle must live outside the Git working tree.

```bash
python scripts/run_contributor_compute.py run \
  --packet path/to/packet.json \
  --repo-root . \
  --bundle ~/chessheat-runs/PACKET-ID \
  --max-workers 4
```

If interrupted, run the same command against the same bundle directory. On POSIX systems the wrapper launches each job in its own process session and terminates that process group on timeout or keyboard interruption before preserving the attempt record.

Accepted work units are verified and reused. Missing units execute. A corrupted accepted record fails closed.

### Verify a completed bundle

```bash
python scripts/run_contributor_compute.py verify \
  --bundle ~/chessheat-runs/PACKET-ID
```

## Packet schema

Required top-level fields:

```json
{
  "schema": "CHESSHEAT_CONTRIBUTOR_COMPUTE_PACKET_V1",
  "packet_id": "CHESSHEAT-COMPUTE-...",
  "scientific_class": "REPLICATION_EXACT",
  "scientific_admission_policy": "CANDIDATE_REPLICATION_EVIDENCE",
  "status": "AUTHORIZED_FOR_CONTRIBUTOR_EXECUTION",
  "approved_science_sha": "40 lowercase hex characters",
  "bound_files": ["..."],
  "scientific_parameters": {},
  "runtime_policy": {
    "max_parallel_workers": 4,
    "adaptive_fields": ["max_workers"]
  },
  "engine": {
    "required": false
  },
  "work_units": []
}
```

Allowed scientific classes:

- `REPLICATION_EXACT`
- `PROSPECTIVE_SHARD`
- `COMPUTE_EXTENSION`

Admission policy is explicit and separate from execution authorization. v1 recognizes:

- `REFERENCE_ONLY_NO_SCIENTIFIC_ADMISSION`
- `CANDIDATE_REPLICATION_EVIDENCE`
- `CANDIDATE_PROSPECTIVE_SHARD`
- `CANDIDATE_EXTENSION_EVIDENCE`

The policy must be compatible with the packet's scientific class. In particular, the deterministic infrastructure reference packet is executable while remaining permanently ineligible for scientific admission.

Only packets whose status is exactly:

```text
AUTHORIZED_FOR_CONTRIBUTOR_EXECUTION
```

may execute.

Any other status is inspectable/preflightable but fails closed at run time.

## Work units

Each work unit requires:

```json
{
  "work_unit_id": "R001",
  "argv": [
    "python",
    "scripts/some_repo_controlled_runner.py",
    "--output",
    "{work_dir}/result.json"
  ],
  "timeout_seconds": 7200,
  "required_outputs": [
    "result.json"
  ]
}
```

The wrapper does not invoke a shell.

Supported placeholders in argv:

- `{repo_root}`
- `{work_dir}`
- `{engine_path}`
- `{python_executable}`

`{engine_path}` may only be used when an engine path is supplied.

Required output paths are relative to the work-unit directory and may not escape it.

When a deterministic reference or exact replication is expected to be byte-identical, a work unit may additionally declare:

```json
"expected_output_sha256": {
  "result.json": "..."
}
```

The wrapper then fails closed if the produced bytes differ.

## Bound scientific files

`approved_science_sha` identifies the scientific implementation a packet is meant to execute.

The contributor's checked-out HEAD may be newer than that commit, which allows wrapper/documentation improvements to coexist with an older frozen scientific implementation.

However:

1. the approved scientific SHA must be an ancestor of HEAD;
2. the working tree must be clean;
3. every `bound_files` path must exist in the approved commit;
4. every local bound file must be byte-for-byte identical to its version at the approved scientific SHA.

This means documentation and contributor infrastructure can evolve without silently mutating frozen scientific code.

## Runtime adaptation

v1 exposes only one adaptive runtime field:

`max_workers`

A packet controls:

- whether `max_workers` may adapt;
- the maximum allowed value.

The wrapper refuses undeclared adaptive fields.

Parallelism is therefore explicit rather than inferred from hardware.

The wrapper also checks that the Git working tree remains clean and that every bound scientific file retains its preflight digest before and after accepted work. A work packet is expected to write all outputs into `{work_dir}`, not back into the repository.

Future versions may add other execution-only knobs, but only after demonstrating that they do not alter the scientific object.

## External engine binding

If a packet declares:

```json
{
  "engine": {
    "required": true,
    "sha256": "..."
  }
}
```

the wrapper requires `--engine-path` and hashes the executable bytes.

Execution stops if the digest does not match.

The bundle records the resolved engine path and actual digest.

## Environment capture

v1 records:

- Python version;
- Python executable;
- Python implementation;
- OS;
- OS release/version;
- architecture;
- processor string;
- CPU count;
- physical memory when available;
- PyTorch version when importable;
- CUDA availability when importable;
- Apple MPS availability when importable.

Environment capture is descriptive provenance. It does not imply that every field is a scientific variable.

## Execution attempts

Each work unit stores attempts independently:

```text
work_units/R001/
  attempts/
    0001/
      stdout.log
      stderr.log
      attempt.json
  accepted_result.json
```

An attempt records:

- exact expanded argv;
- start/end UTC timestamps;
- exit code;
- timeout state;
- interruption state;
- execution error if any;
- stdout SHA-256;
- stderr SHA-256.

An accepted record is written only after a zero exit code and successful required-output verification.

## Resumption rule

When `accepted_result.json` exists, the wrapper recomputes hashes for every required output.

If the hashes match, that work unit is reused.

If they do not match, the wrapper fails closed.

It does not silently rerun a work unit whose accepted evidence has been altered.

## Bundle finalization

A final manifest is written only after every work unit has a valid accepted result.

`bundle_index.json` then hashes every final file in the bundle except the index itself.

The verifier recomputes the entire index and rejects any modified bundle.

## Scientific admission is separate

A wrapper verdict of `PASS` means:

> The submitted bundle is internally consistent with its contributor packet and wrapper provenance.

It does not mean:

> The result is scientifically admitted into ChessHeat.

Project-side scientific admission still requires the governing protocol and research authority to determine whether the bundle is:

- exact replication evidence;
- a separately versioned prospective shard;
- an extension experiment;
- or inadmissible for the proposed use.

## Security

A packet can execute repository code.

Only execute packets obtained from a ChessHeat repository/commit you intentionally trust.

Do not run the wrapper as root or with unnecessary elevated privileges.

## v1 non-goals

v1 does not provide:

- distributed scheduling;
- a central job-claim server;
- automatic GitHub upload;
- contributor identity verification;
- cryptographic packet signatures;
- cloud object storage;
- automatic scientific pooling;
- automatic authorization of any blocked experiment.

Those can be added only if actual community usage justifies the complexity.
