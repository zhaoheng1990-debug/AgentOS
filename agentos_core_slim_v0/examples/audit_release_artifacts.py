"""Independently verify AgentOS smoke manifests and return-pack ZIP files."""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _hash_bytes(encoded)


def audit_artifact_dir(path: Path) -> dict[str, Any]:
    root = path.resolve()
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    committed_manifest = dict(manifest)
    recorded_manifest_hash = committed_manifest.pop("manifest_hash", "")
    file_checks = []
    for item in manifest.get("files", []):
        file_path = root / item["path"]
        exists = file_path.is_file()
        data = file_path.read_bytes() if exists else b""
        file_checks.append(
            {
                "path": item["path"],
                "exists": exists,
                "bytes_match": exists and len(data) == item["bytes"],
                "sha256_match": exists and _hash_bytes(data) == item["sha256"],
            }
        )
    zip_paths = sorted(root.glob("*.zip"))
    zip_checks = []
    expected_entries = {
        item.relative_to(root).as_posix()
        for item in root.rglob("*")
        if item.is_file() and item.suffix.lower() != ".zip"
    }
    for zip_path in zip_paths:
        with zipfile.ZipFile(zip_path, "r") as archive:
            names = archive.namelist()
            bad_crc_entry = archive.testzip()
            for name in names:
                archive.read(name)
        zip_checks.append(
            {
                "path": zip_path.name,
                "entry_count": len(names),
                "duplicate_entries_absent": len(names) == len(set(names)),
                "crc_valid": bad_crc_entry is None,
                "entry_set_matches_directory": set(names) == expected_entries,
                "sha256": _hash_bytes(zip_path.read_bytes()),
                "bytes": zip_path.stat().st_size,
            }
        )
    failure_artifacts = sorted(
        item.relative_to(root).as_posix()
        for item in root.rglob("*failure*.json")
        if item.is_file()
    )
    gates = {
        "manifest_status_pass": manifest.get("status") == "PASS",
        "manifest_hash_valid": recorded_manifest_hash == _hash_payload(committed_manifest),
        "manifest_files_valid": bool(file_checks)
        and all(item["exists"] and item["bytes_match"] and item["sha256_match"] for item in file_checks),
        "exactly_one_return_pack": len(zip_checks) == 1,
        "return_pack_valid": len(zip_checks) == 1
        and zip_checks[0]["crc_valid"]
        and zip_checks[0]["duplicate_entries_absent"]
        and zip_checks[0]["entry_set_matches_directory"],
        "failure_artifacts_absent": not failure_artifacts,
    }
    return {
        "artifact_dir": str(root),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "manifest_file_count": len(file_checks),
        "file_checks": file_checks,
        "zip_checks": zip_checks,
        "failure_artifacts": failure_artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audits = [audit_artifact_dir(path) for path in args.artifact_dir]
    payload = {
        "status": "PASS" if all(item["status"] == "PASS" for item in audits) else "FAIL",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": len(audits),
        "audits": audits,
    }
    payload["audit_hash"] = _hash_payload(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(args.output)}, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
