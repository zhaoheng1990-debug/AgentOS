"""Verify package inventory, evidence anchors, and applied postimages."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(pack: Path, repo: Path) -> dict[str, object]:
    manifest = json.loads((pack / "05_MANIFEST.json").read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    for row in manifest["files"]:
        path = pack / row["path"]
        checks[f"package:{row['path']}"] = (
            path.is_file()
            and path.stat().st_size == row["bytes"]
            and sha256(path) == row["sha256"]
        )
    checks["patch_hash"] = sha256(pack / manifest["patch"]["path"]) == manifest["patch"]["sha256"]
    for relative_path, expected in manifest["postimage_hashes"].items():
        checks[f"postimage:{relative_path}"] = sha256(repo / relative_path) == expected
    for relative_path, expected in manifest["unchanged_anchor_hashes"].items():
        checks[f"unchanged:{relative_path}"] = sha256(repo / relative_path) == expected

    evidence = json.loads((pack / "evidence" / "EVIDENCE_INDEX.json").read_text(encoding="utf-8"))
    for section in ("theory_updates", "verification_anchors"):
        for item in evidence[section]:
            path = Path(item["path"])
            checks[f"evidence:{item.get('version', item.get('object'))}"] = (
                path.is_file() and sha256(path) == item["sha256"]
            )
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "check_count": len(checks),
        "passed_count": sum(checks.values()),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    result = verify(args.pack.resolve(), args.repo.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
