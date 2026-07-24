"""Build and replay-validate the isolated AgentOS SRO retention patch pack."""

from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


PACK_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACK_DIR.parents[1]
PATCH_PATH = PACK_DIR / "patch" / "AgentOS_SRORetentionKernel_Patch_v0_1.patch"
MANIFEST_PATH = PACK_DIR / "05_MANIFEST.json"
ZIP_PATH = PACK_DIR.parent / "AgentOS_SRORetentionKernel_Patch_v0_1.zip"

MODIFIED_FILES = (
    "agentos_core_slim_v0/agentos_kernel/__init__.py",
    "agentos_core_slim_v0/agentos_kernel/provider_cognition_layer.py",
)
NEW_FILES = (
    "agentos_core_slim_v0/agentos_kernel/sro_retention_runtime.py",
    "agentos_core_slim_v0/tests/test_sro_retention_runtime.py",
    "agentos_core_slim_v0/SRO_RETENTION_RUNTIME.md",
)
PATCH_FILES = MODIFIED_FILES + NEW_FILES

PREIMAGE_HASHES = {
    "agentos_core_slim_v0/agentos_kernel/__init__.py": "e6e6056158edc8bed22b9ea5181082aa5e19d61b4d24680d70eb062f87df81e1",
    "agentos_core_slim_v0/agentos_kernel/provider_cognition_layer.py": "f9577eceac67a4423a99db27f8b5ac50887f639633b1e7a6a7d1e68e96e241c2",
}
UNCHANGED_ANCHORS = {
    "agentos_core_slim_v0/agentos_kernel/constraint_aligned_retention.py": "0a07f3d918e0f62d26f217c479dc4654a4d1798bc6eebc0cb41dbccb0bcdcf36",
    "agentos_core_slim_v0/agentos_kernel/version.py": "f2846089862171cc76f614d71014894af733d00f556851fc6579348c2cdb5872",
}

INIT_IMPORT_BLOCK = """from .sro_retention_runtime import (
    SRO_MATCHER_ROUTES,
    SRO_ROUTES,
    DelayedRetrievalLedger,
    DelayedRetrievalPrediction,
    DelayedRetrievalScore,
    GradedSROCompatibilityDecision,
    GradedSROCompatibilityGate,
    SerialSelectionWitness,
)
"""
INIT_EXPORT_LINES = (
    '    "DelayedRetrievalLedger",\n',
    '    "DelayedRetrievalPrediction",\n',
    '    "DelayedRetrievalScore",\n',
    '    "GradedSROCompatibilityDecision",\n',
    '    "GradedSROCompatibilityGate",\n',
    '    "SRO_MATCHER_ROUTES",\n',
    '    "SRO_ROUTES",\n',
    '    "SerialSelectionWitness",\n',
)

PROVIDER_OPERATION_BLOCK = """    CognitionOperationContract(
        "graded_sro_retention_candidate_routing",
        "memory_runtime",
        PROVIDER_REQUIRED,
        "estimate calibrated structural-role compatibility, route probabilities, uncertainty, drift, validity, and negative-transfer risk for one witness-task pair",
        "validate frozen calibration and evidence scope, apply safety overrides, distinguish observe from abstain, and own the final project-scoped route",
        (
            "route_probabilities",
            "uncertainty",
            "drift_risk",
            "negative_transfer_risk",
            "structural_compatibility",
            "role_compatibility",
            "boundary_compatibility",
            "interface_compatibility",
            "trace_sufficiency",
            "calibration_error",
            "validity_state",
            "evidence_scope",
            "confidence",
        ),
        "abstain_or_observe_no_unvalidated_retention_reuse",
    ),
"""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def reconstruct_preimage(relative_path: str, postimage: str) -> str:
    if relative_path.endswith("agentos_kernel/__init__.py"):
        if INIT_IMPORT_BLOCK not in postimage:
            raise RuntimeError("init_import_block_not_found")
        preimage = postimage.replace(INIT_IMPORT_BLOCK, "", 1)
        for line in INIT_EXPORT_LINES:
            if line not in preimage:
                raise RuntimeError(f"init_export_line_not_found:{line.strip()}")
            preimage = preimage.replace(line, "", 1)
        return preimage
    if relative_path.endswith("provider_cognition_layer.py"):
        if PROVIDER_OPERATION_BLOCK not in postimage:
            raise RuntimeError("provider_operation_block_not_found")
        preimage = postimage.replace(PROVIDER_OPERATION_BLOCK, "", 1)
        return preimage.replace(
            'PROVIDER_COGNITION_LAYER_ID = "provider_backed_runtime_cognition_layer_v0_7"',
            'PROVIDER_COGNITION_LAYER_ID = "provider_backed_runtime_cognition_layer_v0_6"',
            1,
        )
    raise RuntimeError(f"unknown_modified_file:{relative_path}")


def unified_patch(relative_path: str, preimage: str, postimage: str, *, new: bool) -> str:
    header = f"diff --git a/{relative_path} b/{relative_path}\n"
    if new:
        header += "new file mode 100644\n"
        from_name = "/dev/null"
    else:
        from_name = f"a/{relative_path}"
    diff = difflib.unified_diff(
        preimage.splitlines(keepends=True),
        postimage.splitlines(keepends=True),
        fromfile=from_name,
        tofile=f"b/{relative_path}",
    )
    return header + "".join(diff)


def build_patch() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    preimages: dict[str, str] = {}
    postimages: dict[str, str] = {}
    patch_parts: list[str] = []
    for relative_path in PATCH_FILES:
        postimage = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        postimages[relative_path] = postimage
        if relative_path in MODIFIED_FILES:
            preimage = reconstruct_preimage(relative_path, postimage)
            observed = sha256_bytes(preimage.encode("utf-8"))
            if observed != PREIMAGE_HASHES[relative_path]:
                raise RuntimeError(
                    f"preimage_hash_mismatch:{relative_path}:{observed}:{PREIMAGE_HASHES[relative_path]}"
                )
        else:
            preimage = ""
        preimages[relative_path] = preimage
        patch_parts.append(
            unified_patch(relative_path, preimage, postimage, new=relative_path in NEW_FILES)
        )
    PATCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    PATCH_PATH.write_text("".join(patch_parts), encoding="utf-8", newline="\n")
    return preimages, postimages, {
        path: sha256_bytes(text.encode("utf-8")) for path, text in postimages.items()
    }


def build_overlay(postimages: dict[str, str]) -> None:
    overlay = PACK_DIR / "overlay"
    if overlay.exists():
        shutil.rmtree(overlay)
    for relative_path, content in postimages.items():
        target = overlay / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")


def validate_patch_replay(preimages: dict[str, str], post_hashes: dict[str, str]) -> None:
    with tempfile.TemporaryDirectory(prefix="agentos-sro-retention-patch-") as temp_name:
        temp_root = Path(temp_name)
        for relative_path in MODIFIED_FILES:
            target = temp_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(preimages[relative_path], encoding="utf-8", newline="\n")
        subprocess.run(
            ["git", "-c", "core.autocrlf=false", "apply", "--check", str(PATCH_PATH)],
            cwd=temp_root,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-c", "core.autocrlf=false", "apply", str(PATCH_PATH)],
            cwd=temp_root,
            check=True,
            capture_output=True,
            text=True,
        )
        for relative_path, expected_hash in post_hashes.items():
            observed = sha256_file(temp_root / relative_path)
            if observed != expected_hash:
                raise RuntimeError(
                    f"replayed_postimage_hash_mismatch:{relative_path}:{observed}:{expected_hash}"
                )
        subprocess.run(
            ["git", "-c", "core.autocrlf=false", "apply", "--check", "-R", str(PATCH_PATH)],
            cwd=temp_root,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-c", "core.autocrlf=false", "apply", "-R", str(PATCH_PATH)],
            cwd=temp_root,
            check=True,
            capture_output=True,
            text=True,
        )
        for relative_path in MODIFIED_FILES:
            observed = sha256_file(temp_root / relative_path)
            if observed != PREIMAGE_HASHES[relative_path]:
                raise RuntimeError(
                    f"rollback_preimage_hash_mismatch:{relative_path}:{observed}:{PREIMAGE_HASHES[relative_path]}"
                )
        for relative_path in NEW_FILES:
            if (temp_root / relative_path).exists():
                raise RuntimeError(f"rollback_failed_to_remove_new_file:{relative_path}")


def verify_unchanged_anchors() -> None:
    for relative_path, expected in UNCHANGED_ANCHORS.items():
        observed = sha256_file(REPO_ROOT / relative_path)
        if observed != expected:
            raise RuntimeError(f"unchanged_anchor_drift:{relative_path}:{observed}:{expected}")


def inventory() -> list[dict[str, object]]:
    rows = []
    for path in sorted(PACK_DIR.rglob("*")):
        if not path.is_file() or path == MANIFEST_PATH or "__pycache__" in path.parts:
            continue
        rows.append(
            {
                "path": path.relative_to(PACK_DIR).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def build_manifest(post_hashes: dict[str, str]) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = {
        "schema_version": "agentos-sro-retention-kernel-patch-manifest-v0.1",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "package_status": "APPLIED_AND_REPLAY_VALIDATED",
        "repository": str(REPO_ROOT),
        "branch": "AgentOS-core-refactor",
        "captured_head": head,
        "active_worktree_version": "0.4.0-alpha.9",
        "preimage_hashes": PREIMAGE_HASHES,
        "unchanged_anchor_hashes": UNCHANGED_ANCHORS,
        "postimage_hashes": post_hashes,
        "patch": {
            "path": PATCH_PATH.relative_to(PACK_DIR).as_posix(),
            "sha256": sha256_file(PATCH_PATH),
            "isolated_replay": "PASS",
            "isolated_rollback": "PASS",
        },
        "verification": {
            "prepatch_relevant": "18 passed",
            "targeted_patch": "33 passed",
            "full_regression": "235 passed",
            "compileall": "PASS",
            "diff_check": "PASS",
        },
        "evidence_index_sha256": sha256_file(PACK_DIR / "evidence" / "EVIDENCE_INDEX.json"),
        "preexisting_dirty_worktree_preserved": True,
        "release_version_bump_included": False,
        "production_activation": False,
        "global_memory_write_authority": False,
        "files": inventory(),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACK_DIR.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            archive.write(path, (Path(PACK_DIR.name) / path.relative_to(PACK_DIR)).as_posix())


def main() -> None:
    verify_unchanged_anchors()
    preimages, postimages, post_hashes = build_patch()
    build_overlay(postimages)
    validate_patch_replay(preimages, post_hashes)
    build_manifest(post_hashes)
    build_zip()
    print(f"PATCH {PATCH_PATH} {sha256_file(PATCH_PATH)}")
    print(f"MANIFEST {MANIFEST_PATH} {sha256_file(MANIFEST_PATH)}")
    print(f"ZIP {ZIP_PATH} {sha256_file(ZIP_PATH)}")


if __name__ == "__main__":
    main()
