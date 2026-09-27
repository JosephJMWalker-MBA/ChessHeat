"""Contributor-compute provenance and execution wrapper for ChessHeat.

This module is intentionally separate from scientific measurement semantics.
It executes only versioned work packets and records enough provenance to make
outside compute auditable.  It does not authorize a scientific experiment.
"""

from __future__ import annotations

import concurrent.futures
import datetime as _dt
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


PACKET_SCHEMA = "CHESSHEAT_CONTRIBUTOR_COMPUTE_PACKET_V1"
AUTHORIZED_STATUS = "AUTHORIZED_FOR_CONTRIBUTOR_EXECUTION"
SCIENTIFIC_CLASSES = {
    "REPLICATION_EXACT",
    "PROSPECTIVE_SHARD",
    "COMPUTE_EXTENSION",
}
_WORK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ContributorComputeError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Union[os.PathLike, str]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _run_git(repo_root: Path, args: List[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=repo_root,
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise ContributorComputeError(
            f"git {' '.join(args)} failed: {exc.output.strip()}"
        ) from exc


def load_packet(path: Union[os.PathLike, str]) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            packet = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContributorComputeError(f"Cannot read packet: {exc}") from exc
    validate_packet(packet)
    return packet


def validate_packet(packet: Dict[str, Any]) -> None:
    if not isinstance(packet, dict):
        raise ContributorComputeError("Packet must be a JSON object")
    if packet.get("schema") != PACKET_SCHEMA:
        raise ContributorComputeError("Contributor packet schema mismatch")

    packet_id = packet.get("packet_id")
    if not isinstance(packet_id, str) or not _WORK_ID_RE.match(packet_id):
        raise ContributorComputeError("Invalid packet_id")

    if packet.get("scientific_class") not in SCIENTIFIC_CLASSES:
        raise ContributorComputeError("Invalid scientific_class")

    approved = packet.get("approved_science_sha")
    if not isinstance(approved, str) or not _SHA40_RE.match(approved):
        raise ContributorComputeError("approved_science_sha must be 40 lowercase hex characters")

    bound_files = packet.get("bound_files")
    if not isinstance(bound_files, list) or not bound_files:
        raise ContributorComputeError("bound_files must be a non-empty list")
    if len(set(bound_files)) != len(bound_files):
        raise ContributorComputeError("bound_files may not contain duplicates")
    for rel in bound_files:
        _validate_relative_path(rel, "bound file")

    scientific_parameters = packet.get("scientific_parameters")
    if not isinstance(scientific_parameters, dict):
        raise ContributorComputeError("scientific_parameters must be an object")

    runtime = packet.get("runtime_policy")
    if not isinstance(runtime, dict):
        raise ContributorComputeError("runtime_policy must be an object")
    max_parallel = runtime.get("max_parallel_workers")
    if not isinstance(max_parallel, int) or isinstance(max_parallel, bool) or max_parallel < 1:
        raise ContributorComputeError("runtime_policy.max_parallel_workers must be >= 1")
    adaptive = runtime.get("adaptive_fields", [])
    if not isinstance(adaptive, list) or any(not isinstance(v, str) for v in adaptive):
        raise ContributorComputeError("runtime_policy.adaptive_fields must be a string list")
    unsupported = set(adaptive) - {"max_workers"}
    if unsupported:
        raise ContributorComputeError(f"Unsupported adaptive runtime fields: {sorted(unsupported)}")

    engine = packet.get("engine", {"required": False})
    if not isinstance(engine, dict) or not isinstance(engine.get("required", False), bool):
        raise ContributorComputeError("engine must declare boolean required")
    if engine.get("required"):
        expected = engine.get("sha256")
        if not isinstance(expected, str) or not _SHA256_RE.match(expected):
            raise ContributorComputeError("Required engine must declare sha256")

    units = packet.get("work_units")
    if not isinstance(units, list) or not units:
        raise ContributorComputeError("work_units must be a non-empty list")
    seen = set()
    for unit in units:
        if not isinstance(unit, dict):
            raise ContributorComputeError("Each work unit must be an object")
        wid = unit.get("work_unit_id")
        if not isinstance(wid, str) or not _WORK_ID_RE.match(wid):
            raise ContributorComputeError("Invalid work_unit_id")
        if wid in seen:
            raise ContributorComputeError(f"Duplicate work_unit_id: {wid}")
        seen.add(wid)

        argv = unit.get("argv")
        if not isinstance(argv, list) or not argv or any(not isinstance(v, str) or not v for v in argv):
            raise ContributorComputeError(f"{wid}: argv must be a non-empty string list")
        timeout = unit.get("timeout_seconds")
        if timeout is not None and (
            not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1
        ):
            raise ContributorComputeError(f"{wid}: timeout_seconds must be a positive integer or null")
        outputs = unit.get("required_outputs", [])
        if not isinstance(outputs, list):
            raise ContributorComputeError(f"{wid}: required_outputs must be a list")
        for rel in outputs:
            _validate_relative_path(rel, f"{wid} required output")


def _validate_relative_path(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ContributorComputeError(f"Invalid {label} path")
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ContributorComputeError(f"{label} must be a safe relative path: {value}")


def verify_repository(repo_root: Union[os.PathLike, str], packet: Dict[str, Any]) -> Dict[str, Any]:
    repo = Path(repo_root).resolve()
    if not (repo / ".git").exists():
        # Worktrees may use a .git file, so accept any .git filesystem entry.
        if not (repo / ".git").is_file():
            raise ContributorComputeError("repo_root is not a Git work tree")

    status = _run_git(repo, ["status", "--porcelain"])
    if status:
        raise ContributorComputeError("Contributor execution requires a clean Git working tree")

    head = _run_git(repo, ["rev-parse", "HEAD"])
    approved = packet["approved_science_sha"]
    obj_type = _run_git(repo, ["cat-file", "-t", approved])
    if obj_type != "commit":
        raise ContributorComputeError("approved_science_sha is not a commit")

    try:
        subprocess.check_output(
            ["git", "merge-base", "--is-ancestor", approved, head],
            cwd=repo,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        raise ContributorComputeError("approved_science_sha is not an ancestor of HEAD") from exc

    bound_results = {}
    for rel in packet["bound_files"]:
        local = repo / rel
        if not local.is_file():
            raise ContributorComputeError(f"Bound file missing locally: {rel}")
        try:
            approved_bytes = subprocess.check_output(
                ["git", "show", f"{approved}:{rel}"],
                cwd=repo,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as exc:
            raise ContributorComputeError(
                f"Bound file absent from approved commit: {rel}"
            ) from exc
        local_bytes = local.read_bytes()
        if local_bytes != approved_bytes:
            raise ContributorComputeError(
                f"Bound file differs from approved scientific commit: {rel}"
            )
        bound_results[rel] = sha256_bytes(local_bytes)

    return {
        "repo_root": str(repo),
        "head_sha": head,
        "approved_science_sha": approved,
        "git_status_porcelain": "",
        "bound_files": bound_results,
    }


def verify_engine(packet: Dict[str, Any], engine_path: Optional[str]) -> Dict[str, Any]:
    engine = packet.get("engine", {"required": False})
    if not engine.get("required"):
        if engine_path:
            path = Path(engine_path).expanduser().resolve()
            if not path.is_file():
                raise ContributorComputeError("Supplied engine_path is not a file")
            return {
                "required": False,
                "supplied": True,
                "path": str(path),
                "sha256": sha256_file(path),
            }
        return {"required": False, "supplied": False}

    if not engine_path:
        raise ContributorComputeError("This packet requires --engine-path")
    path = Path(engine_path).expanduser().resolve()
    if not path.is_file():
        raise ContributorComputeError("Required engine_path is not a file")
    actual = sha256_file(path)
    if actual != engine["sha256"]:
        raise ContributorComputeError(
            f"Engine SHA256 mismatch: expected {engine['sha256']}, got {actual}"
        )
    return {
        "required": True,
        "supplied": True,
        "path": str(path),
        "sha256": actual,
    }


def environment_snapshot() -> Dict[str, Any]:
    total_memory = None
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_PHYS_PAGES")
        total_memory = int(page_size) * int(pages)
    except (AttributeError, ValueError, OSError):
        pass

    torch_info: Dict[str, Any] = {"available": False}
    try:
        import torch  # type: ignore

        torch_info = {
            "available": True,
            "version": str(torch.__version__),
            "cuda_available": bool(torch.cuda.is_available()),
            "mps_available": bool(
                hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
            ),
        }
    except Exception:
        pass

    return {
        "python_version": platform.python_version(),
        "python_executable": str(Path(sys.executable).resolve()),
        "implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "total_memory_bytes": total_memory,
        "torch": torch_info,
    }


def preflight(
    packet_path: Union[os.PathLike, str],
    repo_root: Union[os.PathLike, str],
    engine_path: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    packet = load_packet(packet_path)
    repo_report = verify_repository(repo_root, packet)
    engine_report = verify_engine(packet, engine_path)
    environment = environment_snapshot()
    packet_sha = sha256_bytes(canonical_json_bytes(packet))

    report = {
        "schema": "CHESSHEAT_CONTRIBUTOR_PREFLIGHT_V1",
        "packet_id": packet["packet_id"],
        "packet_sha256": packet_sha,
        "scientific_class": packet["scientific_class"],
        "packet_status": packet.get("status"),
        "repository": repo_report,
        "engine": engine_report,
        "verdict": "PASS",
    }
    return packet, report, environment


def _atomic_write_json(path: Path, value: Any, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if exclusive:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o644)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            raise
        return

    tmp = path.with_name(f".tmp_{path.name}_{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _safe_bundle_path(bundle_dir: Union[os.PathLike, str], repo_root: Union[os.PathLike, str]) -> Path:
    bundle = Path(bundle_dir).expanduser().resolve()
    repo = Path(repo_root).expanduser().resolve()
    try:
        bundle.relative_to(repo)
    except ValueError:
        return bundle
    raise ContributorComputeError(
        "Contributor bundle must live outside the Git working tree"
    )


def _expand_argv(
    argv: Iterable[str], repo_root: Path, work_dir: Path, engine_path: Optional[str]
) -> List[str]:
    replacements = {
        "{repo_root}": str(repo_root),
        "{work_dir}": str(work_dir),
        "{engine_path}": str(Path(engine_path).expanduser().resolve()) if engine_path else "",
        "{python_executable}": str(Path(sys.executable).resolve()),
    }
    result = []
    for arg in argv:
        expanded = arg
        for token, value in replacements.items():
            expanded = expanded.replace(token, value)
        if "{engine_path}" in arg and not engine_path:
            raise ContributorComputeError("Work unit requires {engine_path} but none was supplied")
        result.append(expanded)
    return result


def _assert_runtime_repo_guard(repo_root: Path, bound_hashes: Dict[str, str]) -> None:
    status = _run_git(repo_root, ["status", "--porcelain"])
    if status:
        raise ContributorComputeError("Repository changed during contributor execution")
    for rel, expected_sha in bound_hashes.items():
        path = repo_root / rel
        if not path.is_file() or sha256_file(path) != expected_sha:
            raise ContributorComputeError(
                f"Bound scientific file changed during contributor execution: {rel}"
            )


def _next_attempt_dir(work_dir: Path) -> Path:
    attempts = work_dir / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    existing = []
    for p in attempts.iterdir():
        if p.is_dir() and p.name.isdigit():
            existing.append(int(p.name))
    n = (max(existing) + 1) if existing else 1
    attempt_dir = attempts / f"{n:04d}"
    attempt_dir.mkdir()
    return attempt_dir


def _hash_required_outputs(work_dir: Path, unit: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    outputs = {}
    for rel in unit.get("required_outputs", []):
        path = (work_dir / rel).resolve()
        try:
            path.relative_to(work_dir.resolve())
        except ValueError as exc:
            raise ContributorComputeError(f"Output escapes work unit directory: {rel}") from exc
        if not path.is_file():
            raise ContributorComputeError(f"Required output missing: {rel}")
        outputs[rel] = {
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    return outputs


def verify_accepted_work_unit(work_dir: Path, unit: Dict[str, Any]) -> Dict[str, Any]:
    accepted_path = work_dir / "accepted_result.json"
    if not accepted_path.is_file():
        raise ContributorComputeError("accepted_result.json missing")
    try:
        accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContributorComputeError("Corrupt accepted_result.json") from exc
    if accepted.get("schema") != "CHESSHEAT_CONTRIBUTOR_ACCEPTED_WORK_UNIT_V1":
        raise ContributorComputeError("Accepted work-unit schema mismatch")
    if accepted.get("work_unit_id") != unit["work_unit_id"]:
        raise ContributorComputeError("Accepted work-unit identity mismatch")
    attempt_name = accepted.get("accepted_attempt")
    if not isinstance(attempt_name, str) or not attempt_name.isdigit():
        raise ContributorComputeError("Accepted attempt identity is invalid")
    attempt_dir = work_dir / "attempts" / attempt_name
    attempt_path = attempt_dir / "attempt.json"
    if not attempt_path.is_file():
        raise ContributorComputeError("Accepted attempt record is missing")
    if accepted.get("accepted_attempt_sha256") != sha256_file(attempt_path):
        raise ContributorComputeError("Accepted attempt record changed")
    try:
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContributorComputeError("Accepted attempt record is corrupt") from exc
    if attempt.get("work_unit_id") != unit["work_unit_id"] or attempt.get("exit_code") != 0:
        raise ContributorComputeError("Accepted attempt semantics are invalid")
    stdout_path = attempt_dir / "stdout.log"
    stderr_path = attempt_dir / "stderr.log"
    if attempt.get("stdout_sha256") != (sha256_file(stdout_path) if stdout_path.is_file() else None):
        raise ContributorComputeError("Accepted stdout log changed")
    if attempt.get("stderr_sha256") != (sha256_file(stderr_path) if stderr_path.is_file() else None):
        raise ContributorComputeError("Accepted stderr log changed")
    current = _hash_required_outputs(work_dir, unit)
    if accepted.get("outputs") != current:
        raise ContributorComputeError(
            f"Accepted work-unit outputs changed for {unit['work_unit_id']}"
        )
    return accepted


def _execute_unit(
    unit: Dict[str, Any],
    repo_root: Path,
    bundle_dir: Path,
    engine_path: Optional[str],
    packet_id: str,
    bound_hashes: Dict[str, str],
) -> Dict[str, Any]:
    wid = unit["work_unit_id"]
    work_dir = bundle_dir / "work_units" / wid
    work_dir.mkdir(parents=True, exist_ok=True)
    accepted_path = work_dir / "accepted_result.json"

    if accepted_path.exists():
        accepted = verify_accepted_work_unit(work_dir, unit)
        return {"work_unit_id": wid, "status": "REUSED", "accepted": accepted}

    _assert_runtime_repo_guard(repo_root, bound_hashes)
    attempt_dir = _next_attempt_dir(work_dir)
    stdout_path = attempt_dir / "stdout.log"
    stderr_path = attempt_dir / "stderr.log"
    argv = _expand_argv(unit["argv"], repo_root, work_dir, engine_path)
    env = os.environ.copy()
    env.update(
        {
            "CHESSHEAT_CONTRIBUTOR_PACKET_ID": packet_id,
            "CHESSHEAT_CONTRIBUTOR_WORK_UNIT_ID": wid,
            "CHESSHEAT_CONTRIBUTOR_WORK_DIR": str(work_dir),
        }
    )

    started = _utc_now()
    exit_code: Optional[int] = None
    timed_out = False
    interrupted = False
    error_text = None
    try:
        with open(stdout_path, "wb") as stdout, open(stderr_path, "wb") as stderr:
            try:
                proc = subprocess.run(
                    argv,
                    cwd=repo_root,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=unit.get("timeout_seconds"),
                    shell=False,
                    check=False,
                )
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
            except KeyboardInterrupt:
                interrupted = True
                raise
            except Exception as exc:
                error_text = repr(exc)
    finally:
        ended = _utc_now()
        attempt = {
            "schema": "CHESSHEAT_CONTRIBUTOR_ATTEMPT_V1",
            "work_unit_id": wid,
            "argv": argv,
            "started_at": started,
            "ended_at": ended,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "interrupted": interrupted,
            "error": error_text,
            "stdout_sha256": sha256_file(stdout_path) if stdout_path.exists() else None,
            "stderr_sha256": sha256_file(stderr_path) if stderr_path.exists() else None,
        }
        _atomic_write_json(attempt_dir / "attempt.json", attempt)

    if interrupted:
        raise KeyboardInterrupt
    if timed_out:
        raise ContributorComputeError(f"{wid}: timed out")
    if error_text is not None:
        raise ContributorComputeError(f"{wid}: execution error: {error_text}")
    if exit_code != 0:
        raise ContributorComputeError(f"{wid}: process exited with {exit_code}")

    _assert_runtime_repo_guard(repo_root, bound_hashes)
    outputs = _hash_required_outputs(work_dir, unit)
    accepted = {
        "schema": "CHESSHEAT_CONTRIBUTOR_ACCEPTED_WORK_UNIT_V1",
        "work_unit_id": wid,
        "argv": argv,
        "accepted_attempt": attempt_dir.name,
        "accepted_attempt_sha256": sha256_file(attempt_dir / "attempt.json"),
        "outputs": outputs,
    }
    _atomic_write_json(accepted_path, accepted, exclusive=True)
    return {"work_unit_id": wid, "status": "EXECUTED", "accepted": accepted}


def _initialize_bundle(
    bundle_dir: Path,
    packet: Dict[str, Any],
    packet_path: Path,
    preflight_report: Dict[str, Any],
    environment: Dict[str, Any],
) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    packet_copy = bundle_dir / "packet.json"
    preflight_copy = bundle_dir / "preflight_report.json"
    environment_copy = bundle_dir / "environment.json"

    if packet_copy.exists():
        existing = json.loads(packet_copy.read_text(encoding="utf-8"))
        if canonical_json_bytes(existing) != canonical_json_bytes(packet):
            raise ContributorComputeError("Bundle belongs to a different packet")
        if not preflight_copy.is_file() or not environment_copy.is_file():
            raise ContributorComputeError("Existing bundle is missing preflight/environment records")
        old_preflight = json.loads(preflight_copy.read_text(encoding="utf-8"))
        old_environment = json.loads(environment_copy.read_text(encoding="utf-8"))
        if canonical_json_bytes(old_preflight) != canonical_json_bytes(preflight_report):
            raise ContributorComputeError("Preflight identity changed across resume")
        if canonical_json_bytes(old_environment) != canonical_json_bytes(environment):
            raise ContributorComputeError("Environment changed across resume; start a new bundle")
        return

    _atomic_write_json(packet_copy, packet, exclusive=True)
    _atomic_write_json(preflight_copy, preflight_report, exclusive=True)
    _atomic_write_json(environment_copy, environment, exclusive=True)


def _build_bundle_index(bundle_dir: Path) -> Dict[str, Any]:
    files = {}
    for path in sorted(bundle_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(bundle_dir).as_posix()
        if rel == "bundle_index.json":
            continue
        files[rel] = {
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    return {
        "schema": "CHESSHEAT_CONTRIBUTOR_BUNDLE_INDEX_V1",
        "files": files,
    }


def run_packet(
    packet_path: Union[os.PathLike, str],
    repo_root: Union[os.PathLike, str],
    bundle_dir: Union[os.PathLike, str],
    *,
    engine_path: Optional[str] = None,
    max_workers: int = 1,
) -> Dict[str, Any]:
    packet_path = Path(packet_path).expanduser().resolve()
    repo_root = Path(repo_root).expanduser().resolve()
    bundle_dir = _safe_bundle_path(bundle_dir, repo_root)

    packet, preflight_report, environment = preflight(
        packet_path, repo_root, engine_path
    )
    if packet.get("status") != AUTHORIZED_STATUS:
        raise ContributorComputeError(
            f"Packet is not authorized for execution: {packet.get('status')}"
        )

    max_allowed = packet["runtime_policy"]["max_parallel_workers"]
    adaptive = set(packet["runtime_policy"].get("adaptive_fields", []))
    if max_workers != 1 and "max_workers" not in adaptive:
        raise ContributorComputeError("Packet does not allow max_workers adaptation")
    if not isinstance(max_workers, int) or isinstance(max_workers, bool) or max_workers < 1:
        raise ContributorComputeError("max_workers must be >= 1")
    if max_workers > max_allowed:
        raise ContributorComputeError(
            f"max_workers={max_workers} exceeds packet maximum {max_allowed}"
        )

    _initialize_bundle(
        bundle_dir, packet, packet_path, preflight_report, environment
    )

    started = _utc_now()
    results = []
    units = packet["work_units"]
    bound_hashes = preflight_report["repository"]["bound_files"]

    try:
        if max_workers == 1:
            for unit in units:
                results.append(
                    _execute_unit(
                        unit,
                        repo_root,
                        bundle_dir,
                        engine_path,
                        packet["packet_id"],
                        bound_hashes,
                    )
                )
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        _execute_unit,
                        unit,
                        repo_root,
                        bundle_dir,
                        engine_path,
                        packet["packet_id"],
                        bound_hashes,
                    ): unit["work_unit_id"]
                    for unit in units
                }
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())
    except KeyboardInterrupt:
        raise
    except Exception:
        # Do not publish a final manifest/index for an incomplete invocation.
        raise

    _assert_runtime_repo_guard(repo_root, bound_hashes)

    accepted = {}
    for unit in units:
        wid = unit["work_unit_id"]
        accepted[wid] = verify_accepted_work_unit(
            bundle_dir / "work_units" / wid, unit
        )

    ended = _utc_now()
    manifest = {
        "schema": "CHESSHEAT_CONTRIBUTOR_RUN_MANIFEST_V1",
        "packet_id": packet["packet_id"],
        "packet_sha256": preflight_report["packet_sha256"],
        "scientific_class": packet["scientific_class"],
        "approved_science_sha": packet["approved_science_sha"],
        "scientific_parameters_sha256": sha256_bytes(
            canonical_json_bytes(packet["scientific_parameters"])
        ),
        "repo_head_sha": preflight_report["repository"]["head_sha"],
        "max_workers": max_workers,
        "started_at": started,
        "ended_at": ended,
        "work_unit_count": len(units),
        "accepted_work_units": sorted(accepted),
        "execution_summary": sorted(
            [{"work_unit_id": r["work_unit_id"], "status": r["status"]} for r in results],
            key=lambda v: v["work_unit_id"],
        ),
        "verdict": "COMPLETE",
    }
    _atomic_write_json(bundle_dir / "run_manifest.json", manifest)
    index = _build_bundle_index(bundle_dir)
    _atomic_write_json(bundle_dir / "bundle_index.json", index)
    return manifest


def verify_bundle(bundle_dir: Union[os.PathLike, str]) -> Dict[str, Any]:
    bundle = Path(bundle_dir).expanduser().resolve()
    packet_path = bundle / "packet.json"
    manifest_path = bundle / "run_manifest.json"
    index_path = bundle / "bundle_index.json"
    if not packet_path.is_file() or not manifest_path.is_file() or not index_path.is_file():
        raise ContributorComputeError("Bundle is incomplete")

    packet = load_packet(packet_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "CHESSHEAT_CONTRIBUTOR_RUN_MANIFEST_V1":
        raise ContributorComputeError("Run manifest schema mismatch")
    if manifest.get("packet_id") != packet["packet_id"]:
        raise ContributorComputeError("Run manifest packet mismatch")
    if manifest.get("packet_sha256") != sha256_bytes(canonical_json_bytes(packet)):
        raise ContributorComputeError("Run manifest packet SHA mismatch")
    expected_ids = sorted(unit["work_unit_id"] for unit in packet["work_units"])
    if manifest.get("work_unit_count") != len(expected_ids):
        raise ContributorComputeError("Run manifest work-unit count mismatch")
    if manifest.get("accepted_work_units") != expected_ids:
        raise ContributorComputeError("Run manifest accepted-work-unit set mismatch")

    for unit in packet["work_units"]:
        verify_accepted_work_unit(bundle / "work_units" / unit["work_unit_id"], unit)

    expected_index = _build_bundle_index(bundle)
    actual_index = json.loads(index_path.read_text(encoding="utf-8"))
    if canonical_json_bytes(actual_index) != canonical_json_bytes(expected_index):
        raise ContributorComputeError("Bundle index mismatch; bundle was modified")

    return {
        "schema": "CHESSHEAT_CONTRIBUTOR_BUNDLE_VERIFICATION_V1",
        "packet_id": packet["packet_id"],
        "scientific_class": packet["scientific_class"],
        "work_unit_count": len(packet["work_units"]),
        "verdict": "PASS",
    }
