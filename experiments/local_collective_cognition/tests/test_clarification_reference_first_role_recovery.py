import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_reference_first_role_analysis import (  # noqa: E402
    build_specialist_recovery_analysis,
    build_specialist_role_analysis,
    validate_specialist_recovery_analysis,
)
from local_collective_cognition.clarification_reference_first_role_recovery import (  # noqa: E402
    RECOVERY_VERSION,
    ReferenceFirstSpecialistRecoveryRuntime,
    build_recovered_specialist_role_run,
    build_specialist_recovery_plan,
    validate_specialist_recovery_plan,
    validate_specialist_recovery_run,
)
from local_collective_cognition.clarification_reference_first_role_runtime import validate_specialist_role_run  # noqa: E402
from local_collective_cognition.clarification_reference_first_roles import MODEL_IDS, ROLE_TASK_KIND  # noqa: E402


OUTPUT = ROOT / "outputs" / "clarification_reference_first_v0_15"


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


class FixtureFlatRecoveryAdapter:
    def __init__(self, model_id, forbidden_reference_hash):
        self.forbidden_reference_hash = forbidden_reference_hash
        self.profile = ProviderCapabilityProfile(provider_id="fixture-recovery-" + model_id, model_id=model_id, task_kinds=(ROLE_TASK_KIND,), max_timeout_seconds=180)

    def invoke(self, task):
        visible = json.dumps({"inputs": task.inputs, "evidence": task.allowed_evidence}, sort_keys=True)
        assert self.forbidden_reference_hash not in visible
        role_id = task.inputs["role_id"]
        item = task.inputs["item"]
        base = {"recovery_version": RECOVERY_VERSION, "role_id": role_id, "recovery_task_id": task.expected_schema["properties"]["recovery_task_id"]["enum"][0], "conflict_id": item["conflict_id"]}
        if role_id == "OBJECT_GROUNDING":
            result = {**base, "selected_object": "NONE", "selection_basis": "NO_PREFERENCE", "support": "No fixture object is fixed.", "counterevidence": "Both candidates remain possible.", "confidence": 0.7}
        elif role_id == "PRAGMATIC_DEFAULT":
            result = {**base, "pragmatic_preference": "NONE", "default_advantage": "No fixture advantage.", "counterpressure": "Both candidates remain possible.", "confidence": 0.7}
        else:
            result = {**base, "assessment_completeness": "COMPLETE", "missing_information": [], "rationale": "The fixture can be assessed as open.", "confidence": 0.7}
        return {"result": result, "usage": {"input_tokens": 50, "output_tokens": 30, "provider_calls": 1}, "provenance_refs": list(task.allowed_evidence)}


def test_flat_recovery_recovers_rejected_batches_without_reusing_payloads():
    corpus = read("private_reference_first_corpus.json")
    reference = read("reference_first_model_panel_reference_candidate.json")
    role_plan = read("local_specialist_role_plan.json")
    initial_run = read("local_specialist_role_run.json")
    recovery_plan = build_specialist_recovery_plan(role_plan=role_plan, failed_run=initial_run)
    validate_specialist_recovery_plan(recovery_plan, role_plan=role_plan, failed_run=initial_run)
    assert recovery_plan["task_count"] == 72
    assert recovery_plan["semantic_payload_reuse_from_failed_batches"] is False
    evidence_refs = [*corpus["evidence_refs"], f"artifact://{corpus['artifact_hash']}", f"surface://{corpus['public_surface']['surface_hash']}"]
    adapters = tuple(FixtureFlatRecoveryAdapter(model_id, reference["artifact_hash"]) for model_id in MODEL_IDS)
    recovery_run = ReferenceFirstSpecialistRecoveryRuntime(role_plan=role_plan, failed_run=initial_run, recovery_plan=recovery_plan, evidence_refs=evidence_refs).evaluate(experiment_id="fixture-flat-recovery", adapters=adapters)
    validate_specialist_recovery_run(recovery_run, recovery_plan=recovery_plan)
    assert len(recovery_run["outputs"]) == 72 and not recovery_run["failures"]
    recovered = build_recovered_specialist_role_run(role_plan=role_plan, initial_run=initial_run, recovery_plan=recovery_plan, recovery_run=recovery_run)
    validate_specialist_role_run(recovered, corpus_artifact=corpus, role_plan=role_plan)
    analysis = build_specialist_role_analysis(corpus_artifact=corpus, frozen_reference=reference, role_plan=role_plan, role_run=recovered)
    assert analysis["receipt_coverage"] == 1.0
    assert analysis["coordinator_run_allowed"] is True
    assert analysis["accounting"]["provider_calls"] == initial_run["accounting"]["provider_calls"] + 72
    recovery_analysis = build_specialist_recovery_analysis(
        corpus_artifact=corpus,
        frozen_reference=reference,
        role_plan=role_plan,
        initial_run=initial_run,
        recovery_plan=recovery_plan,
        recovery_run=recovery_run,
    )
    validate_specialist_recovery_analysis(
        recovery_analysis,
        corpus_artifact=corpus,
        frozen_reference=reference,
        role_plan=role_plan,
        initial_run=initial_run,
        recovery_plan=recovery_plan,
        recovery_run=recovery_run,
    )
    assert recovery_analysis["strict_receipt_coverage"] == 1.0
    assert recovery_analysis["candidate_state"] == "LOCAL_SPECIALIST_RECEIPTS_FROZEN"
    assert recovery_analysis["coordinator_run_allowed"] is True
