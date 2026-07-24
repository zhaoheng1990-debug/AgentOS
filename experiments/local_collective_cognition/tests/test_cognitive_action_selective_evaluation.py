from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_selective_evaluation import (  # noqa: E402
    build_selective_external_evaluation,
    build_selective_external_reference,
    validate_selective_external_evaluation,
    validate_selective_external_reference,
)
from local_collective_cognition.cognitive_action_selective_panel import (  # noqa: E402
    K3_SPEC,
    build_selective_external_adjudication,
    build_selective_external_panel,
)
from local_collective_cognition.cognitive_action_selective_runtime import (  # noqa: E402
    SOURCE_EVALUATION_HASH,
    SOURCE_REFERENCE_HASH,
    analyze_selective_run,
    build_admission_plan,
    build_selective_preregistration,
    run_local_preference_roles,
    run_selective_adjudication,
    run_selective_baseline,
)
from local_collective_cognition.tests_support import _Local, _Provider  # noqa: E402
from local_collective_cognition.cognitive_action_selective_holdout import build_selective_holdout  # noqa: E402
from tests.test_cognitive_action_selective_panel import response_for  # noqa: E402


def test_selective_reference_and_evaluation_are_deterministic():
    corpus = build_selective_holdout()
    source = {
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "anti_additive_gate": "REJECT",
        "candidate_state": "AXIS_ROUTING_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION",
    }
    prereg = build_selective_preregistration(source_evaluation=source)
    baseline = run_selective_baseline(corpus=corpus, preregistration=prereg, adapter=_Provider())
    admission = build_admission_plan(corpus=corpus, preregistration=prereg, baseline_run=baseline)
    local = run_local_preference_roles(corpus=corpus, admission_plan=admission, adapter=_Local())
    run = run_selective_adjudication(
        corpus=corpus,
        preregistration=prereg,
        baseline_run=baseline,
        admission_plan=admission,
        local_role_run=local,
        adapter=_Provider(),
    )
    analysis = analyze_selective_run(
        corpus=corpus,
        baseline_run=baseline,
        admission_plan=admission,
        local_role_run=local,
        run=run,
    )
    packs, panel_manifest = build_selective_external_panel(
        corpus=corpus,
        baseline_run=baseline,
        selective_run=run,
    )
    responses = (response_for(packs[0]), response_for(packs[1], alternate_first=True))
    adjudication_pack, adjudication_manifest = build_selective_external_adjudication(
        packs=packs,
        panel_manifest=panel_manifest,
        responses=responses,
        corpus=corpus,
    )
    item = adjudication_pack["items"][0]
    position = item["anonymous_full_tuple_positions"][0]
    adjudication_response = {
        "panel_version": adjudication_pack["panel_version"],
        "adjudication_version": adjudication_pack["adjudication_version"],
        "panel_id": adjudication_pack["panel_id"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudicator_provider": K3_SPEC[0],
        "adjudicator_model": K3_SPEC[1],
        "adjudication_session_ref": "fixture-evaluation",
        "blinding_attestation": adjudication_pack["response_contract"]["required_blinding_attestation"],
        "decisions": [{
            "adjudication_id": item["adjudication_id"],
            "criteria": position["criteria"],
            "decision_basis": position["position_id"],
            "confidence": 0.9,
            "rationale": "Fixture whole-tuple decision.",
        }],
    }
    reference = build_selective_external_reference(
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        adjudication_response=adjudication_response,
    )
    validate_selective_external_reference(reference)
    evaluation = build_selective_external_evaluation(
        reference=reference,
        baseline_run=baseline,
        admission_plan=admission,
        selective_run=run,
        runtime_analysis=analysis,
        preregistration=prereg,
    )
    validate_selective_external_evaluation(
        evaluation,
        reference=reference,
        baseline_run=baseline,
        admission_plan=admission,
        selective_run=run,
        runtime_analysis=analysis,
        preregistration=prereg,
    )
    assert reference["object_count"] == 24
    assert reference["criterion_count"] == 120
    assert evaluation["missing_outputs_scored_as_incorrect"] is True
    assert evaluation["retention_write_allowed"] is False
