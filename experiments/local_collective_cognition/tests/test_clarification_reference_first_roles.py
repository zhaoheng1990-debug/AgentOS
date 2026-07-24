from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_reference_first_holdout import validate_reference_first_holdout  # noqa: E402
from local_collective_cognition.clarification_reference_first_panel import validate_reference_first_reference  # noqa: E402
from local_collective_cognition.clarification_reference_first_role_analysis import (  # noqa: E402
    build_specialist_role_analysis,
    validate_specialist_role_analysis,
)
from local_collective_cognition.clarification_reference_first_role_runtime import (  # noqa: E402
    ReferenceFirstSpecialistRuntime,
    validate_specialist_role_run,
)
from local_collective_cognition.clarification_reference_first_roles import (  # noqa: E402
    MODEL_IDS,
    ROLE_TASK_KIND,
    build_specialist_role_plan,
    validate_specialist_role_payload,
    validate_specialist_role_plan,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


OUTPUT = ROOT / "outputs" / "clarification_reference_first_v0_15"


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def artifacts():
    corpus = read("private_reference_first_corpus.json")
    reference = read("reference_first_model_panel_reference_candidate.json")
    progress = read("reference_frozen_progress.json")
    validate_reference_first_holdout(corpus)
    validate_reference_first_reference(reference)
    return corpus, reference, progress


class FixtureRoleAdapter:
    def __init__(self, model_id, forbidden_reference_hash):
        self.forbidden_reference_hash = forbidden_reference_hash
        self.seen_tasks = []
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + model_id,
            model_id=model_id,
            task_kinds=(ROLE_TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        visible = json.dumps({"inputs": task.inputs, "evidence": task.allowed_evidence}, sort_keys=True)
        assert self.forbidden_reference_hash not in visible
        assert "reference_first_model_panel_reference_candidate" not in visible
        self.seen_tasks.append(task)
        role_id = task.inputs["role_id"]
        decisions = []
        for item in task.inputs["items"]:
            if role_id == "OBJECT_GROUNDING":
                decision = {"conflict_id": item["conflict_id"], "selected_object": "NONE", "selection_basis": "NO_PREFERENCE", "support": "No fixture candidate is fixed.", "counterevidence": "Both remain available.", "confidence": 0.7}
            elif role_id == "PRAGMATIC_DEFAULT":
                decision = {"conflict_id": item["conflict_id"], "pragmatic_preference": "NONE", "default_advantage": "No fixture advantage.", "counterpressure": "Both remain available.", "confidence": 0.7}
            else:
                decision = {"conflict_id": item["conflict_id"], "assessment_completeness": "COMPLETE", "missing_information": [], "rationale": "A justified open fixture can be complete.", "confidence": 0.7}
            decisions.append(decision)
        return {
            "result": {"role_version": task.expected_schema["properties"]["role_version"]["enum"][0], "role_id": role_id, "batch_id": task.inputs["batch_id"], "decisions": decisions, "evidence_refs": list(task.allowed_evidence)},
            "usage": {"input_tokens": 100, "output_tokens": 50, "provider_calls": 1},
            "provenance_refs": list(task.allowed_evidence),
        }


def test_specialist_role_plan_is_balanced_and_reference_blind():
    corpus, reference, progress = artifacts()
    plan = build_specialist_role_plan(corpus_artifact=corpus, frozen_reference=reference, frozen_progress=progress)
    validate_specialist_role_plan(plan, corpus_artifact=corpus, frozen_reference=reference, frozen_progress=progress)
    assert plan["assignment_count"] == 72 and plan["batch_count"] == 18
    assert plan["reference_content_exposed_to_roles"] is False
    for model_id in MODEL_IDS:
        for role_id in plan["role_ids"]:
            assert sum(item["model_id"] == model_id and item["role_id"] == role_id for item in plan["assignments"]) == 8


def test_specialist_role_runtime_hides_reference_and_freezes_complete_receipts():
    corpus, reference, progress = artifacts()
    plan = build_specialist_role_plan(corpus_artifact=corpus, frozen_reference=reference, frozen_progress=progress)
    adapters = tuple(FixtureRoleAdapter(model_id, reference["artifact_hash"]) for model_id in MODEL_IDS)
    run = ReferenceFirstSpecialistRuntime(corpus_artifact=corpus, role_plan=plan).evaluate(experiment_id="fixture-specialists", adapters=adapters)
    validate_specialist_role_run(run, corpus_artifact=corpus, role_plan=plan)
    assert len(run["receipts"]) == 18 and not run["failures"]
    assert all(adapter.seen_tasks for adapter in adapters)
    analysis = build_specialist_role_analysis(corpus_artifact=corpus, frozen_reference=reference, role_plan=plan, role_run=run)
    validate_specialist_role_analysis(analysis, corpus_artifact=corpus, frozen_reference=reference, role_plan=plan, role_run=run)
    assert analysis["receipt_coverage"] == 1.0
    assert analysis["role_metrics"]["ASSESSMENT_SKEPTIC"]["accuracy"] == 1.0
    assert analysis["candidate_state"] == "LOCAL_SPECIALIST_RECEIPTS_FROZEN"
    assert analysis["coordinator_run_allowed"] is True


def test_specialist_role_payload_rejects_incoherent_object_pair():
    corpus, reference, progress = artifacts()
    plan = build_specialist_role_plan(corpus_artifact=corpus, frozen_reference=reference, frozen_progress=progress)
    batch = next(item for item in plan["batches"] if item["role_id"] == "OBJECT_GROUNDING")
    payload = {
        "role_version": plan["role_version"],
        "role_id": batch["role_id"],
        "batch_id": batch["batch_id"],
        "decisions": [
            {"conflict_id": item["conflict_id"], "selected_object": "NONE", "selection_basis": "COMPOSITIONAL_ENTAILMENT", "support": "Fixture.", "counterevidence": "Fixture.", "confidence": 0.5}
            for item in batch["items"]
        ],
        "evidence_refs": [*corpus["evidence_refs"], f"artifact://{corpus['artifact_hash']}", f"surface://{corpus['public_surface']['surface_hash']}"],
    }
    with pytest.raises(ValueError, match="specialist_object_pair_incoherent"):
        validate_specialist_role_payload(payload, batch=batch, evidence_refs=payload["evidence_refs"])


def test_specialist_role_plan_and_run_reject_tamper():
    corpus, reference, progress = artifacts()
    plan = build_specialist_role_plan(corpus_artifact=corpus, frozen_reference=reference, frozen_progress=progress)
    tampered_plan = deepcopy(plan)
    tampered_plan["assignments"][0]["role_id"] = "PRAGMATIC_DEFAULT"
    tampered_plan["plan_hash"] = hash_payload({key: value for key, value in tampered_plan.items() if key != "plan_hash"})
    with pytest.raises(ValueError, match="specialist_role_plan_invalid"):
        validate_specialist_role_plan(tampered_plan)
    adapters = tuple(FixtureRoleAdapter(model_id, reference["artifact_hash"]) for model_id in MODEL_IDS)
    run = ReferenceFirstSpecialistRuntime(corpus_artifact=corpus, role_plan=plan).evaluate(experiment_id="fixture-tamper", adapters=adapters)
    tampered_run = deepcopy(run)
    tampered_run["receipts"][0]["payload"]["decisions"][0]["confidence"] = 0.1
    with pytest.raises(ValueError, match="specialist_role_run_invalid"):
        validate_specialist_role_run(tampered_run, corpus_artifact=corpus, role_plan=plan)
