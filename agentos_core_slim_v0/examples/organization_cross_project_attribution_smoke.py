"""Audit organization-component attribution across projects without pooling effects."""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


COMPONENTS = (
    "COORDINATOR",
    "ADVERSARIAL_REVIEWER",
    "REPLICATOR",
    "SYNTHESIZER",
)
RETURN_PACK_NAME = "AgentOS_OrganizationCrossProjectAttribution_ReturnPack_v0_1.zip"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_payload(payload: Any) -> str:
    return _hash_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _direction(value: float) -> str:
    if value > 0.0:
        return "BENEFICIAL"
    if value < 0.0:
        return "HARMFUL"
    return "UNCERTAIN"


def _load_feedback(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise ValueError("cross_project_source_feedback_must_pass")
    if payload.get("evidence_tier") != "LIVE_PROJECT":
        raise ValueError("cross_project_source_must_be_live_project")
    gates = payload.get("gates")
    if not isinstance(gates, dict) or not gates or not all(gates.values()):
        raise ValueError("cross_project_source_gates_incomplete")
    return payload


def _context_record(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    context_key = payload.get("context_key")
    if not isinstance(context_key, str) or not context_key:
        raise ValueError("cross_project_context_key_required")
    diagnosis = payload.get("diagnosis") or {}
    attribution = ((diagnosis.get("attribution") or {}).get("components") or [])
    hypotheses = diagnosis.get("component_hypotheses") or []
    by_component = {item.get("component_id"): item for item in attribution if isinstance(item, dict)}
    by_hypothesis = {item.get("component_id"): item for item in hypotheses if isinstance(item, dict)}
    if set(by_component) != set(COMPONENTS) or set(by_hypothesis) != set(COMPONENTS):
        raise ValueError("cross_project_component_set_mismatch")

    rows = []
    for component_id in COMPONENTS:
        item = by_component[component_id]
        hypothesis = by_hypothesis[component_id]
        if item.get("identifiability") != "IDENTIFIED_MATCHED_ABLATION":
            raise ValueError("cross_project_component_not_identified")
        pair_count = item.get("matched_pair_count")
        if not isinstance(pair_count, int) or isinstance(pair_count, bool) or pair_count < 2:
            raise ValueError("cross_project_matched_pair_count_insufficient")
        effectiveness = item.get("mean_effectiveness_contribution")
        if not isinstance(effectiveness, (int, float)) or isinstance(effectiveness, bool):
            raise ValueError("cross_project_effectiveness_contribution_invalid")
        direction = _direction(float(effectiveness))
        if (
            hypothesis.get("causal_status") != "IDENTIFIED_MATCHED_ABLATION"
            or hypothesis.get("direction") != direction
        ):
            raise ValueError("cross_project_provider_direction_mismatch")
        rows.append(
            {
                "component_id": component_id,
                "matched_pair_count": pair_count,
                "direction": direction,
                "mean_effectiveness_contribution": float(effectiveness),
                "mean_cbit_contribution": item.get("mean_cbit_contribution"),
                "mean_cost_contribution": item.get("mean_cost_contribution"),
                "provider_causal_status": hypothesis.get("causal_status"),
                "provider_direction": hypothesis.get("direction"),
            }
        )
    return {
        "context_key": context_key,
        "source_path": str(path.resolve()),
        "source_sha256": _hash_bytes(path.read_bytes()),
        "source_bundle_count": payload.get("source_bundle_count"),
        "source_record_count": payload.get("record_count"),
        "components": rows,
    }


def _manifest(output_dir: Path, status: str) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {"manifest.json", RETURN_PACK_NAME}:
            files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _hash_bytes(path.read_bytes()),
                }
            )
    payload = {"status": status, "created_at": _utc_now(), "files": files}
    payload["manifest_hash"] = _hash_payload(payload)
    _write_json(output_dir / "manifest.json", payload)
    return payload


def _return_pack(output_dir: Path) -> Path:
    path = output_dir / RETURN_PACK_NAME
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(output_dir.rglob("*")):
            if item.is_file() and item != path:
                archive.write(item, item.relative_to(output_dir).as_posix())
    return path


def run_audit(source_paths: tuple[Path, ...], output_dir: Path) -> dict[str, Any]:
    if len(source_paths) < 2:
        raise ValueError("cross_project_requires_multiple_contexts")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    contexts = [_context_record(path, _load_feedback(path)) for path in source_paths]
    context_keys = [item["context_key"] for item in contexts]
    if len(context_keys) != len(set(context_keys)):
        raise ValueError("cross_project_contexts_must_be_unique")

    component_transfer = []
    for component_id in COMPONENTS:
        directions = {
            context["context_key"]: next(
                item["direction"] for item in context["components"] if item["component_id"] == component_id
            )
            for context in contexts
        }
        unique_directions = set(directions.values())
        component_transfer.append(
            {
                "component_id": component_id,
                "context_directions": directions,
                "transfer_status": (
                    "DIRECTION_CONSISTENT_ACROSS_OBSERVED_CONTEXTS"
                    if len(unique_directions) == 1
                    else "CONTEXT_DEPENDENT"
                ),
                "candidate_state": "CANDIDATE_ONLY",
            }
        )

    gates = {
        "multiple_unique_contexts": len(contexts) >= 2 and len(context_keys) == len(set(context_keys)),
        "all_components_identified_per_context": all(
            len(context["components"]) == len(COMPONENTS)
            and all(item["matched_pair_count"] >= 2 for item in context["components"])
            for context in contexts
        ),
        "provider_directions_match_kernel_effect_signs": all(
            item["provider_direction"] == item["direction"]
            for context in contexts
            for item in context["components"]
        ),
        "transfer_claims_remain_candidate_only": all(
            item["candidate_state"] == "CANDIDATE_ONLY" for item in component_transfer
        ),
        "context_effects_not_pooled": True,
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": "organization-cross-project-attribution-v0-1",
        "status": status,
        "created_at": _utc_now(),
        "context_count": len(contexts),
        "contexts": contexts,
        "component_transfer": component_transfer,
        "gates": gates,
        "measurement_boundary": (
            "Effect sizes remain scoped to each context. This audit compares signs only, emits no pooled causal "
            "estimate or universal role ranking, and keeps cross-context transfer claims candidate-only."
        ),
        "manifest_path": str(output_dir / "manifest.json"),
        "return_pack": str(output_dir / RETURN_PACK_NAME),
    }
    _write_json(output_dir / "cross_project_attribution_result.json", result)
    _manifest(output_dir, status)
    _return_pack(output_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-result", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_audit(tuple(args.source_result), args.output_dir)
        print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, indent=2))
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure = {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)}
        _write_json(args.output_dir / "cross_project_attribution_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
