import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from chessheat.contributor_compute import (
    ContributorComputeError,
    PACKET_SCHEMA,
    preflight,
    run_packet,
    verify_bundle,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repo, text=True, stderr=subprocess.STDOUT
    ).strip()


def _make_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "ChessHeat Tests")
    (repo / "bound.txt").write_text("frozen\n", encoding="utf-8")
    _git(repo, "add", "bound.txt")
    _git(repo, "commit", "-m", "frozen science")
    return repo, _git(repo, "rev-parse", "HEAD")


def _packet(approved_sha: str, *, status="AUTHORIZED_FOR_CONTRIBUTOR_EXECUTION"):
    writer = (
        "from pathlib import Path; import sys; "
        "Path(sys.argv[1]).write_text(sys.argv[2], encoding='utf-8')"
    )
    return {
        "schema": PACKET_SCHEMA,
        "packet_id": "CHESSHEAT-COMPUTE-TEST-001",
        "scientific_class": "REPLICATION_EXACT",
        "scientific_admission_policy": "REFERENCE_ONLY_NO_SCIENTIFIC_ADMISSION",
        "status": status,
        "approved_science_sha": approved_sha,
        "bound_files": ["bound.txt"],
        "scientific_parameters": {
            "purpose": "synthetic test only"
        },
        "runtime_policy": {
            "max_parallel_workers": 2,
            "adaptive_fields": ["max_workers"],
        },
        "engine": {"required": False},
        "work_units": [
            {
                "work_unit_id": "R001",
                "argv": [
                    sys.executable,
                    "-c",
                    writer,
                    "{work_dir}/result.txt",
                    "alpha",
                ],
                "timeout_seconds": 30,
                "required_outputs": ["result.txt"],
            },
            {
                "work_unit_id": "R002",
                "argv": [
                    sys.executable,
                    "-c",
                    writer,
                    "{work_dir}/result.txt",
                    "beta",
                ],
                "timeout_seconds": 30,
                "required_outputs": ["result.txt"],
            },
        ],
    }


def _write_packet(tmp_path: Path, packet) -> Path:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    return packet_path


def test_preflight_and_complete_bundle_roundtrip(tmp_path):
    repo, approved = _make_repo(tmp_path)
    packet_path = _write_packet(tmp_path, _packet(approved))
    bundle = tmp_path / "bundle"

    packet, report, environment = preflight(packet_path, repo)
    assert packet["packet_id"] == "CHESSHEAT-COMPUTE-TEST-001"
    assert report["verdict"] == "PASS"
    assert report["repository"]["approved_science_sha"] == approved
    assert "python_version" in environment

    manifest = run_packet(
        packet_path,
        repo,
        bundle,
        max_workers=2,
    )
    assert manifest["verdict"] == "COMPLETE"
    assert manifest["work_unit_count"] == 2

    verification = verify_bundle(bundle)
    assert verification["verdict"] == "PASS"
    assert verification["work_unit_count"] == 2


def test_resume_reuses_accepted_work_units(tmp_path):
    repo, approved = _make_repo(tmp_path)
    packet_path = _write_packet(tmp_path, _packet(approved))
    bundle = tmp_path / "bundle"

    first = run_packet(packet_path, repo, bundle)
    assert all(v["status"] == "EXECUTED" for v in first["execution_summary"])

    second = run_packet(packet_path, repo, bundle)
    assert all(v["status"] == "REUSED" for v in second["execution_summary"])
    assert verify_bundle(bundle)["verdict"] == "PASS"


def test_bundle_tampering_fails_closed(tmp_path):
    repo, approved = _make_repo(tmp_path)
    packet_path = _write_packet(tmp_path, _packet(approved))
    bundle = tmp_path / "bundle"
    run_packet(packet_path, repo, bundle)

    stdout = bundle / "work_units" / "R001" / "attempts" / "0001" / "stdout.log"
    stdout.write_text("tampered", encoding="utf-8")

    with pytest.raises(ContributorComputeError, match="stdout log changed|Bundle index mismatch"):
        verify_bundle(bundle)


def test_unauthorized_packet_can_preflight_but_not_run(tmp_path):
    repo, approved = _make_repo(tmp_path)
    packet_path = _write_packet(
        tmp_path, _packet(approved, status="EXAMPLE_NOT_AUTHORIZED")
    )

    _, report, _ = preflight(packet_path, repo)
    assert report["verdict"] == "PASS"

    with pytest.raises(ContributorComputeError, match="not authorized"):
        run_packet(packet_path, repo, tmp_path / "bundle")


def test_bound_scientific_file_may_not_drift_on_descendant_commit(tmp_path):
    repo, approved = _make_repo(tmp_path)

    (repo / "bound.txt").write_text("changed\n", encoding="utf-8")
    _git(repo, "add", "bound.txt")
    _git(repo, "commit", "-m", "mutate science")
    packet_path = _write_packet(tmp_path, _packet(approved))

    with pytest.raises(ContributorComputeError, match="differs from approved"):
        preflight(packet_path, repo)


def test_dirty_repository_fails_closed(tmp_path):
    repo, approved = _make_repo(tmp_path)
    packet_path = _write_packet(tmp_path, _packet(approved))
    (repo / "untracked.txt").write_text("drift", encoding="utf-8")

    with pytest.raises(ContributorComputeError, match="clean Git working tree"):
        preflight(packet_path, repo)


def test_runtime_parallelism_is_packet_bounded(tmp_path):
    repo, approved = _make_repo(tmp_path)
    packet = _packet(approved)
    packet["runtime_policy"]["max_parallel_workers"] = 1
    packet_path = _write_packet(tmp_path, packet)

    with pytest.raises(ContributorComputeError, match="exceeds packet maximum"):
        run_packet(packet_path, repo, tmp_path / "bundle", max_workers=2)


def test_engine_digest_mismatch_fails_preflight(tmp_path):
    repo, approved = _make_repo(tmp_path)
    engine = tmp_path / "stockfish"
    engine.write_bytes(b"not-stockfish")
    packet = _packet(approved)
    packet["engine"] = {
        "required": True,
        "sha256": "0" * 64,
    }
    packet_path = _write_packet(tmp_path, packet)

    with pytest.raises(ContributorComputeError, match="Engine SHA256 mismatch"):
        preflight(packet_path, repo, str(engine))
