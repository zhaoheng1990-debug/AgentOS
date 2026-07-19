"""Feed repeated matched-ablation bundles into Kernel-owned organization learning."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import COMPONENT_VARIANTS, ProviderTaskRouter  # noqa: E402
from agentos_runtime import (  # noqa: E402
    CognitiveOrganizationLearningRuntime,
    OrganizationLearningSeed,
    organization_records_from_ablation_smoke_result,
)
from examples.organization_learning_project_source_smoke import (  # noqa: E402
    ALLOWED_VARIANTS,
    StaticDiagnosisProvider,
    _live_provider,
)


RETURN_PACK_NAME = "AgentOS_OrganizationAblationLearningFeedback_ReturnPack_v0_1.zip"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _hash_bytes(encoded)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _write_manifest(output_dir: Path, status: str) -> dict[str, Any]:
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


def _write_return_pack(output_dir: Path) -> Path:
    path = output_dir / RETURN_PACK_NAME
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(output_dir.rglob("*")):
            if item.is_file() and item != path:
                archive.write(item, item.relative_to(output_dir).as_posix())
    return path


def run_feedback(
    source_result_paths: tuple[Path, ...],
    output_dir: Path,
    *,
    context_key: str,
    evidence_tier: str,
    provider_mode: str = "scripted",
    authorize_next_max_variants: int = 0,
) -> dict[str, Any]:
    if len(source_result_paths) < 2:
        raise ValueError("organization_ablation_feedback_requires_two_bundles")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in source_result_paths]
    selected_variant_sets = [tuple(payload.get("selected_variants", ())) for payload in payloads]
    if any(not selected for selected in selected_variant_sets):
        raise ValueError("organization_ablation_feedback_protocol_set_missing")
    variant_counts = Counter(
        variant for selected in selected_variant_sets for variant in set(selected)
    )
    records = tuple(
        record
        for index, payload in enumerate(payloads, start=1)
        for record in organization_records_from_ablation_smoke_result(
            payload,
            context_key=context_key,
            evidence_tier=evidence_tier,
            trial_group_id=f"matched-ablation-{index}",
        )
    )
    evidence_refs = records[0].evidence_refs
    if any(record.evidence_refs != evidence_refs for record in records):
        raise ValueError("organization_ablation_feedback_evidence_mismatch")
    provider: Any = _live_provider() if provider_mode == "live" else StaticDiagnosisProvider()
    runtime = CognitiveOrganizationLearningRuntime(
        runtime_id="organization-ablation-learning-feedback",
        seed=OrganizationLearningSeed(
            context_key=context_key,
            evidence_tier=evidence_tier,
            evidence_refs=evidence_refs,
            allowed_experiment_variants=ALLOWED_VARIANTS,
            minimum_repeated_trials=2,
            improvement_threshold=0.02,
        ),
        diagnosis_router=ProviderTaskRouter([provider]),
        workspace_root=output_dir / "runtime",
    )
    runtime.admit_records(records)
    diagnosis = runtime.diagnose()
    policy = runtime.synthesize_policy()
    by_component = {item.component_id: item for item in diagnosis.attribution.components}
    component_by_variant = {variant: component for component, variant in COMPONENT_VARIANTS.items()}
    expected_identified = {
        component_by_variant[variant]
        for variant, count in variant_counts.items()
        if count >= runtime.seed.minimum_repeated_trials
    }
    expected_unidentified = set(COMPONENT_VARIANTS) - expected_identified
    source_inventory = [
        {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": _hash_bytes(path.read_bytes()),
        }
        for path in source_result_paths
    ]
    proposal = None
    authorization = None
    if authorize_next_max_variants:
        proposal = runtime.propose_experiment(
            max_variants=authorize_next_max_variants,
            experiment_family="MATCHED_ABLATION",
        )
        authorization = runtime.authorize_experiment(
            kernel_authorization_ref="kernel://organization-ablation-learning-feedback/next-experiment",
            budget={
                "max_trial_runs": len(proposal.selected_variants) + 1,
                "max_provider_calls_per_run": 20,
            },
        )
    gates = {
        "two_independent_bundles": len({item["sha256"] for item in source_inventory}) >= 2,
        "all_records_admitted": len(records)
        == sum(len(selected) + 1 for selected in selected_variant_sets),
        "matched_pair_count_reaches_two": all(
            by_component[component].matched_pair_count >= 2 for component in expected_identified
        ),
        "selected_components_identified": all(
            by_component[component].identifiability == "IDENTIFIED_MATCHED_ABLATION"
            for component in expected_identified
        ),
        "untested_components_remain_unidentified": all(
            by_component[component].identifiability == "NOT_IDENTIFIABLE"
            for component in expected_unidentified
        ),
        "provider_causality_bounded": all(
            item["causal_status"] == by_component[item["component_id"]].identifiability
            or (
                item["causal_status"] == "HYPOTHESIS_ONLY"
                and by_component[item["component_id"]].identifiability == "NOT_IDENTIFIABLE"
            )
            for item in diagnosis.component_hypotheses
        ),
        "policy_remains_candidate_only": (
            not policy.execution_authorized and not policy.route_selection_authority
        ),
        "replay_valid": runtime.verify_replay()["valid"],
    }
    if authorize_next_max_variants:
        gates["next_experiment_separately_authorized"] = (
            proposal is not None
            and not proposal.execution_authorized
            and authorization is not None
            and authorization.execution_authorized
        )
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": f"organization-ablation-learning-feedback-{evidence_tier.lower()}-{provider_mode}",
        "status": status,
        "created_at": _utc_now(),
        "provider_mode": provider_mode,
        "context_key": context_key,
        "evidence_tier": evidence_tier,
        "source_inventory": source_inventory,
        "source_bundle_count": len(source_result_paths),
        "record_count": len(records),
        "variant_bundle_counts": dict(sorted(variant_counts.items())),
        "gates": gates,
        "diagnosis": diagnosis.as_dict(),
        "policy_candidate": policy.as_dict(),
        "next_experiment_proposal": proposal.as_dict() if proposal else None,
        "next_experiment_authorization": authorization.as_dict() if authorization else None,
        "measurement_boundary": (
            "Kernel computes matched effects from Harness-owned metrics. Provider explains the admitted report but "
            "cannot alter measurements, identifiability, causal direction, or candidate state."
        ),
        "return_pack": str(output_dir / RETURN_PACK_NAME),
        "manifest_path": str(output_dir / "manifest.json"),
    }
    _write_json(output_dir / "organization_learning_snapshot.json", runtime.snapshot().as_dict())
    _write_json(output_dir / "organization_ablation_learning_feedback_result.json", result)
    _write_manifest(output_dir, status)
    _write_return_pack(output_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-result", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--context-key", required=True)
    parser.add_argument("--evidence-tier", choices=("LIVE_PROJECT", "SCRIPTED_FIXTURE"), required=True)
    parser.add_argument("--provider-mode", choices=("scripted", "live"), default="scripted")
    parser.add_argument("--authorize-next-max-variants", type=int, default=0)
    args = parser.parse_args()
    try:
        result = run_feedback(
            tuple(args.source_result),
            args.output_dir,
            context_key=args.context_key,
            evidence_tier=args.evidence_tier,
            provider_mode=args.provider_mode,
            authorize_next_max_variants=args.authorize_next_max_variants,
        )
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure = {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:1000]}
        _write_json(args.output_dir / "organization_ablation_learning_feedback_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1
    print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
