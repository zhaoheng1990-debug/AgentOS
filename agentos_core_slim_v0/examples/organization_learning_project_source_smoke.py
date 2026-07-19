"""Cognitive organization learning smoke over completed alpha.6 trial results."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CORE_ROOT.parent
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import CreditProfile, ProviderCapabilityProfile, ProviderTaskRouter  # noqa: E402
from agentos_runtime import (  # noqa: E402
    CognitiveOrganizationLearningRuntime,
    OrganizationLearningSeed,
    organization_records_from_execution_smoke_result,
)
from examples.project_source_group_cognition_smoke import (  # noqa: E402
    LiveProviderSpec,
    OpenAICompatibleJsonAdapter,
)


ALLOWED_VARIANTS = (
    "SOLO",
    "FIXED_TEAM",
    "DYNAMIC_TEAM",
    "DYNAMIC_NO_COORDINATOR",
    "DYNAMIC_NO_REVIEWER",
    "DYNAMIC_NO_REPLICATOR",
    "DYNAMIC_NO_SYNTHESIZER",
)


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


class StaticDiagnosisProvider:
    def __init__(self) -> None:
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-diagnosis-provider",
            model_id="fixture-diagnosis-model",
            task_kinds=("cognitive_organization_failure_diagnosis",),
            max_timeout_seconds=120,
        )
        self.tasks: list[Any] = []

    def invoke(self, task: Any) -> dict[str, Any]:
        self.tasks.append(task)
        attribution = {
            item["component_id"]: item for item in task.inputs["matched_attribution"]["components"]
        }
        hypotheses = []
        next_variants = []
        for component_id, item in attribution.items():
            identified = item["identifiability"] == "IDENTIFIED_MATCHED_ABLATION"
            contribution = item["mean_effectiveness_contribution"]
            direction = "UNCERTAIN"
            if identified and contribution is not None:
                direction = "BENEFICIAL" if contribution > 0 else "HARMFUL" if contribution < 0 else "UNCERTAIN"
            hypotheses.append(
                {
                    "component_id": component_id,
                    "direction": direction,
                    "causal_status": (
                        "IDENTIFIED_MATCHED_ABLATION" if identified else "HYPOTHESIS_ONLY"
                    ),
                    "rationale": (
                        "Matched ablation supports this bounded direction."
                        if identified
                        else "No sufficient matched ablation exists; this remains a hypothesis."
                    ),
                    "evidence_refs": list(task.allowed_evidence),
                }
            )
            if not identified:
                next_variants.append(item["ablation_variant"])
        if not next_variants:
            next_variants = ["SOLO", "FIXED_TEAM", "DYNAMIC_TEAM"]
        result = {
            "failure_modes": [
                "Team cost may exceed correction gain.",
                "A full-team result cannot identify one component without matched ablation.",
            ],
            "component_hypotheses": hypotheses,
            "coordination_cost_assessment": "Compare full dynamic execution with a no-coordinator matched trial.",
            "next_experiment_variants": next_variants,
            "confidence": 0.6,
            "evidence_refs": list(task.allowed_evidence),
        }
        return {
            "result": result,
            "usage": {"total_tokens": 1},
            "provenance_refs": list(task.allowed_evidence),
        }


class RecordingProvider:
    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.profile = delegate.profile
        self.tasks: list[Any] = []
        self.responses: list[dict[str, Any]] = []

    def invoke(self, task: Any) -> dict[str, Any]:
        self.tasks.append(task)
        response = self.delegate.invoke(task)
        self.responses.append(response)
        return response


def _write_provider_diagnosis_audit(output_dir: Path, provider: Any) -> None:
    if not isinstance(provider, RecordingProvider):
        return
    tasks = [
        {
            "task_id": task.task_id,
            "task_kind": task.task_kind,
            "objective": task.objective,
            "inputs": task.inputs,
            "allowed_evidence": task.allowed_evidence,
            "expected_schema": task.expected_schema,
            "budget": task.budget,
            "timeout_seconds": task.timeout_seconds,
            "freshness_requirement": task.freshness_requirement,
            "failure_semantics": task.failure_semantics,
            "idempotency_key": task.idempotency_key,
        }
        for task in provider.tasks
    ]
    _write_json(
        output_dir / "provider_diagnosis_audit.json",
        {
            "tasks": tasks,
            "responses": provider.responses,
        },
    )


def _live_provider() -> RecordingProvider:
    spec = LiveProviderSpec(
        "deepseek",
        "deepseek-v4-pro",
        "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY",
        "cognitive_organization_failure_diagnosis",
        3200,
        {"thinking": {"type": "disabled"}},
    )
    return RecordingProvider(OpenAICompatibleJsonAdapter(spec))


def _advisory_credits(payload: dict[str, Any]) -> dict[str, CreditProfile]:
    evaluation = payload["counterfactual_evaluation"]
    profiles = {item["subject_id"]: item for item in payload.get("credit_profiles", [])}
    subject_by_protocol = {
        "SOLO": evaluation.get("best_member_subject_id"),
        "FIXED_TEAM": evaluation.get("fixed_team_subject_id"),
        "DYNAMIC_TEAM": evaluation.get("dynamic_team_subject_id"),
    }
    result = {}
    for protocol, subject_id in subject_by_protocol.items():
        item = profiles.get(subject_id)
        if not item:
            continue
        result[protocol] = CreditProfile(
            subject_id=item["subject_id"],
            subject_kind=item["subject_kind"],
            event_count=item["event_count"],
            positive_weight=item["positive_weight"],
            negative_weight=item["negative_weight"],
            trust_score=item["trust_score"],
            confidence=item["confidence"],
            advisory_only=True,
            selection_authority=False,
        )
    return result


def _build_return_pack(output_dir: Path) -> Path:
    path = output_dir / "AgentOS_CognitiveOrganizationLearning_ReturnPack_v0_1.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(output_dir.rglob("*")):
            if item.is_file() and item != path:
                archive.write(item, item.relative_to(output_dir).as_posix())
    return path


def _manifest(output_dir: Path, status: str) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {
            "manifest.json",
            "AgentOS_CognitiveOrganizationLearning_ReturnPack_v0_1.zip",
        }:
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


def run_smoke(
    source_result_paths: tuple[Path, ...],
    output_dir: Path,
    *,
    context_key: str,
    evidence_tier: str,
    provider_mode: str = "scripted",
    expected_recommendation: str | None = None,
    experiment_family: str = "ANY",
    max_variants: int = 3,
) -> dict[str, Any]:
    if not source_result_paths:
        raise ValueError("organization_learning_source_results_required")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in source_result_paths]
    records = tuple(
        item
        for index, payload in enumerate(payloads, start=1)
        for item in organization_records_from_execution_smoke_result(
            payload,
            context_key=context_key,
            evidence_tier=evidence_tier,
            trial_group_id=f"trial-{index}",
        )
    )
    evidence_refs = records[0].evidence_refs
    if any(item.evidence_refs != evidence_refs for item in records):
        raise ValueError("organization_learning_source_results_evidence_mismatch")
    provider: Any = _live_provider() if provider_mode == "live" else StaticDiagnosisProvider()
    runtime = CognitiveOrganizationLearningRuntime(
        runtime_id="project-source-organization-learning",
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
        advisory_credit_profiles=_advisory_credits(payloads[0]),
    )
    runtime.admit_records(records)
    try:
        diagnosis = runtime.diagnose()
    except Exception:
        _write_provider_diagnosis_audit(output_dir, provider)
        raise
    _write_provider_diagnosis_audit(output_dir, provider)
    policy = runtime.synthesize_policy()
    proposal = runtime.propose_experiment(max_variants=max_variants, experiment_family=experiment_family)
    authorization = runtime.authorize_experiment(
        kernel_authorization_ref="kernel://organization-learning/project-source-smoke",
        budget={
            "max_trial_runs": len(proposal.selected_variants)
            + int(
                any(item.startswith("DYNAMIC_NO_") for item in proposal.selected_variants)
                and "DYNAMIC_TEAM" not in proposal.selected_variants
            ),
            "max_provider_calls_per_run": 20,
        },
    )
    source_inventory = [
        {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": _hash_bytes(path.read_bytes()),
        }
        for path in source_result_paths
    ]
    identifiability = {item.component_id: item.identifiability for item in diagnosis.attribution.components}
    gates = {
        "all_source_results_unique": len({item["sha256"] for item in source_inventory}) == len(source_inventory),
        "all_records_admitted": len(records) == 3 * len(source_result_paths),
        "context_and_tier_preserved": all(
            item.context_key == context_key and item.evidence_tier == evidence_tier for item in records
        ),
        "provider_causality_bounded": all(
            item["causal_status"] == identifiability[item["component_id"]]
            or (
                item["causal_status"] == "HYPOTHESIS_ONLY"
                and identifiability[item["component_id"]] == "NOT_IDENTIFIABLE"
            )
            for item in diagnosis.component_hypotheses
        ),
        "credit_remains_advisory": policy.credit_is_advisory and not policy.route_selection_authority,
        "policy_has_no_execution_authority": not policy.execution_authorized,
        "experiment_requires_separate_authorization": not proposal.execution_authorized
        and authorization.execution_authorized,
        "replay_valid": runtime.verify_replay()["valid"],
    }
    if expected_recommendation:
        gates["expected_recommendation"] = policy.recommendation == expected_recommendation
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": f"organization-learning-{evidence_tier.lower()}-{provider_mode}",
        "status": status,
        "created_at": _utc_now(),
        "provider_mode": provider_mode,
        "experiment_family": experiment_family,
        "max_variants": max_variants,
        "context_key": context_key,
        "evidence_tier": evidence_tier,
        "source_trial_count": len(source_result_paths),
        "source_inventory": source_inventory,
        "gates": gates,
        "diagnosis": diagnosis.as_dict(),
        "policy_candidate": policy.as_dict(),
        "experiment_proposal": proposal.as_dict(),
        "experiment_authorization": authorization.as_dict(),
        "measurement_boundary": (
            "Protocol selection requires repeated complete three-arm trials in one context and evidence tier. "
            "Component causality requires repeated matched ablations. Credit remains advisory."
        ),
        "return_pack": str(output_dir / "AgentOS_CognitiveOrganizationLearning_ReturnPack_v0_1.zip"),
        "manifest_path": str(output_dir / "manifest.json"),
    }
    _write_json(output_dir / "organization_learning_snapshot.json", runtime.snapshot().as_dict())
    _write_json(output_dir / "organization_learning_result.json", result)
    _manifest(output_dir, status)
    _build_return_pack(output_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-result", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--context-key", required=True)
    parser.add_argument("--evidence-tier", choices=("LIVE_PROJECT", "SCRIPTED_FIXTURE"), required=True)
    parser.add_argument("--provider-mode", choices=("scripted", "live"), default="scripted")
    parser.add_argument("--experiment-family", choices=("ANY", "MATCHED_ABLATION"), default="ANY")
    parser.add_argument("--max-variants", type=int, default=3)
    parser.add_argument("--expected-recommendation")
    args = parser.parse_args()
    try:
        result = run_smoke(
            tuple(args.source_result),
            args.output_dir,
            context_key=args.context_key,
            evidence_tier=args.evidence_tier,
            provider_mode=args.provider_mode,
            expected_recommendation=args.expected_recommendation,
            experiment_family=args.experiment_family,
            max_variants=args.max_variants,
        )
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure = {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:1000]}
        _write_json(args.output_dir / "organization_learning_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1
    print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
