"""Finalize the v0.16 overnight experiment without changing semantic evidence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_coordinator import analyze_blind_coordinator_arms  # noqa: E402
from local_collective_cognition.grammar_role_calibration import analyze_grammar_calibration, render_grammar_calibration_analysis  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


OUTPUT_NAMES = (
    "grammar_calibration_run.json", "grammar_calibration_analysis.json", "GRAMMAR_CALIBRATION_ANALYSIS.md",
    "context_calibrated_run.json", "context_calibrated_analysis.json", "CONTEXT_CALIBRATED_ANALYSIS.md",
    "staged_semantic_run.json", "staged_semantic_analysis.json", "STAGED_SEMANTIC_ANALYSIS.md",
    "fresh_action_corpus_frozen.json", "fresh_action_role_plan.json", "fresh_action_role_run.json",
    "fresh_action_role_analysis.json", "fresh_action_external_annotation_pack.json",
    "blind_coordinator_arms_run.json", "blind_coordinator_arms_analysis.json", "blind_coordinator_telemetry.json",
    "overnight_phase_ledger.json", "POST_EXPERIMENT_ANALYSIS.md", "replay_pointer.json", "rollback_pointer.json",
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    output = REPO_ROOT / "outputs" / "cognitive_action_overnight_v0_16"
    source = REPO_ROOT / "outputs" / "clarification_reference_first_v0_15"
    corpus = read(source / "private_reference_first_corpus.json")
    reference = read(source / "reference_first_model_panel_reference_candidate.json")
    role_plan = read(source / "local_specialist_role_plan.json")
    analyses = {}
    for prefix, title in (("grammar_calibration", "Grammar-Backed"), ("context_calibrated", "Context-Calibrated"), ("staged_semantic", "Staged Semantic")):
        run = read(output / f"{prefix}_run.json")
        analysis = analyze_grammar_calibration(corpus=corpus, reference=reference, role_plan=role_plan, run=run)
        analyses[prefix] = analysis
        write(output / f"{prefix}_analysis.json", analysis)
        (output / {"grammar_calibration": "GRAMMAR_CALIBRATION_ANALYSIS.md", "context_calibrated": "CONTEXT_CALIBRATED_ANALYSIS.md", "staged_semantic": "STAGED_SEMANTIC_ANALYSIS.md"}[prefix]).write_text(render_grammar_calibration_analysis(analysis).replace("Grammar-Backed", title), encoding="utf-8")
    fresh_corpus = read(output / "fresh_action_corpus_frozen.json")
    fresh_role_run = read(output / "fresh_action_role_run.json")
    fresh_role_analysis = read(output / "fresh_action_role_analysis.json")
    coordinator_run = read(output / "blind_coordinator_arms_run.json")
    coordinator_analysis = analyze_blind_coordinator_arms(corpus=fresh_corpus, role_run=fresh_role_run, role_analysis=fresh_role_analysis, run=coordinator_run)
    write(output / "blind_coordinator_arms_analysis.json", coordinator_analysis)

    phase_commitment = {
        "ledger_version": "cognitive_action_overnight_phase_ledger_v0_16",
        "methodology_kernel": "v1.1",
        "phases": [
            {"phase": "G0_BASELINE", "status": "PASS", "evidence": "248 tests passed with workspace-local basetemp; CUDA and four local models available"},
            {"phase": "G1_ANONYMOUS_GRAMMAR", "status": "REVISED", "coverage": analyses["grammar_calibration"]["overall_coverage"], "semantic_gate": analyses["grammar_calibration"]["semantic_viability_gate_passed"], "finding": "syntax bottleneck removed but arbitrary code binding harmed semantics"},
            {"phase": "G1_CONTEXT_DESCRIPTION_SCORING", "status": "FAIL", "coverage": analyses["context_calibrated"]["overall_coverage"], "semantic_gate": analyses["context_calibrated"]["semantic_viability_gate_passed"], "finding": "description likelihood measured continuation preference rather than classification"},
            {"phase": "G2_STAGED_SEMANTIC_SCORING", "status": "PASS_EXPLORATORY", "pooled_gate": analyses["staged_semantic"]["pooled_semantic_viability_gate_passed"], "routed_gate": analyses["staged_semantic"]["semantic_viability_gate_passed"], "routing": analyses["staged_semantic"]["selected_bijective_routing"]},
            {"phase": "G3_FRESH_BLIND_ROLES", "status": "PASS_STRUCTURAL_PENDING_SEMANTIC", "coverage": fresh_role_analysis["strict_receipt_coverage"], "semantic_accuracy_available": False},
            {"phase": "G4_BLIND_COORDINATOR_ARMS", "status": "PASS_STRUCTURAL_PENDING_EXTERNAL_PANEL", "arm_coverage": coordinator_analysis["arm_coverage"], "full_tuple_disagreement_count": coordinator_analysis["full_tuple_disagreement_count"], "collective_gain_claim_allowed": False},
        ],
        "accepted_objects": ["canonical cognitive action receipts", "Harness-owned grammar compilation", "model-role capability routing as an exploratory calibration object"],
        "revised_objects": ["rich JSON generation -> finite or scored semantic choice plus mechanical lifting", "pooled interchangeability gate -> separately reported routed specialization gate"],
        "failed_objects": ["anonymous action-code binding for small models", "long-description continuation likelihood as semantic classifier", "unqualified action interpretation in the coordinator schema"],
        "pending_objects": ["fresh semantic correctness", "collective gain over single-model baseline", "Cbit per token", "completeness-axis generalization", "action transition preconditions"],
        "evidence_coordinate": ["Internal Project Evidence", "Model Inference"],
        "baseline_insertion": "No Baseline Object Update; experiment candidate only",
    }
    ledger = {**phase_commitment, "artifact_hash": hash_payload(phase_commitment)}
    write(output / "overnight_phase_ledger.json", ledger)

    replay_commitment = {
        "pointer_version": "cognitive_action_overnight_replay_v0_16",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python -m pytest -q --basetemp=.pytest_tmp_overnight_replay",
            "conda run -n dhrf_4080s python examples/run_grammar_role_calibration.py",
            "conda run -n dhrf_4080s python examples/run_context_calibrated_role_calibration.py",
            "conda run -n dhrf_4080s python examples/run_staged_semantic_role_calibration.py",
            "conda run -n dhrf_4080s python examples/run_cognitive_action_fresh_roles.py",
            "conda run -n dhrf_4080s python examples/run_cognitive_action_coordinator.py",
            "python examples/finalize_cognitive_action_overnight.py",
        ],
        "external_panel_next": "Submit fresh_action_external_annotation_pack.json independently to GPT-5.6 and Gemini 3.1, then adjudicate disagreements with Kimi K3.",
        "reference_revision_allowed": False,
    }
    replay = {**replay_commitment, "artifact_hash": hash_payload(replay_commitment)}
    write(output / "replay_pointer.json", replay)

    rollback_commitment = {
        "pointer_version": "cognitive_action_overnight_rollback_v0_16",
        "scope": "experiment-only; AgentOS CoreSlim was not modified by this window",
        "output_directory": str(output),
        "code_prefixes": ["cognitive_action_", "grammar_backed_role_adapter.py", "grammar_role_calibration.py", "context_calibrated_role_adapter.py", "staged_semantic_role_adapter.py"],
        "rollback_action": "quarantine the listed v0.16 experiment files and output directory after verifying hashes; do not alter pre-existing experiment or CoreSlim files",
        "automatic_rollback_executed": False,
        "retention_authority": False,
    }
    rollback = {**rollback_commitment, "artifact_hash": hash_payload(rollback_commitment)}
    write(output / "rollback_pointer.json", rollback)

    post = render_post_analysis(analyses, fresh_role_analysis, coordinator_analysis, ledger)
    (output / "POST_EXPERIMENT_ANALYSIS.md").write_text(post, encoding="utf-8")

    inventory_items = []
    for name in OUTPUT_NAMES:
        path = output / name
        if path.is_file():
            inventory_items.append({"path": name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    inventory_commitment = {"inventory_version": "cognitive_action_overnight_hash_inventory_v0_16", "items": inventory_items}
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(output / "hash_inventory.json", inventory)
    manifest_commitment = {
        "manifest_version": "cognitive_action_overnight_manifest_v0_16",
        "phase_ledger_hash": ledger["artifact_hash"],
        "fresh_corpus_hash": fresh_corpus["artifact_hash"],
        "fresh_role_run_hash": fresh_role_run["run_hash"],
        "coordinator_run_hash": coordinator_run["run_hash"],
        "coordinator_analysis_hash": coordinator_analysis["artifact_hash"],
        "annotation_pack_hash": read(output / "fresh_action_external_annotation_pack.json")["pack_hash"],
        "hash_inventory_hash": inventory["artifact_hash"],
        "candidate_state": coordinator_analysis["candidate_state"],
        "external_panel_required": True,
        "collective_gain_claim_allowed": False,
    }
    manifest = {**manifest_commitment, "artifact_hash": hash_payload(manifest_commitment)}
    write(output / "manifest.json", manifest)
    print(json.dumps({"ledger_hash": ledger["artifact_hash"], "inventory_hash": inventory["artifact_hash"], "manifest_hash": manifest["artifact_hash"], "candidate_state": manifest["candidate_state"]}, indent=2, sort_keys=True))


def render_post_analysis(analyses, fresh, coordinator, ledger):
    anonymous, context, staged = analyses["grammar_calibration"], analyses["context_calibrated"], analyses["staged_semantic"]
    role_agreement = coordinator["role_receipt_agreement_counts"]
    ratios = coordinator["coordinator_to_baseline_cost_ratios"]
    return f"""# Cognitive Action Overnight v0.16 Analysis

## Observations

- Baseline verification passed: 248 tests with a workspace-local pytest base directory; CUDA, three small models, and local DeepSeek R1 32B were available.
- Anonymous finite grammar raised strict receipt coverage to {anonymous['overall_coverage']:.3f} and reduced generated-token transport cost, but failed routed semantic viability.
- Long-description context scoring retained {context['overall_coverage']:.3f} coverage but further reduced semantic accuracy; it behaved like continuation scoring rather than classification.
- Staged short-label scoring reached {staged['overall_coverage']:.3f} coverage. Pooled viability remained {staged['pooled_semantic_viability_gate_passed']}, while the frozen one-to-one routed gate passed with object {staged['routed_role_metrics']['OBJECT_GROUNDING']['accuracy']:.3f}, preference {staged['routed_role_metrics']['PRAGMATIC_DEFAULT']['accuracy']:.3f}, and skeptic {staged['routed_role_metrics']['ASSESSMENT_SKEPTIC']['accuracy']:.3f} on the burned calibration set.
- Fresh blind role collection produced {fresh['strict_receipt_coverage']:.3f} coverage. The skeptic returned COMPLETE for all 24 objects, including deliberately underspecified surfaces; correctness is unknown.
- Both DeepSeek arms produced full structural coverage. Their full tuples differed on {coordinator['full_tuple_disagreement_count']}/24 objects; axis disagreements were {coordinator['axis_disagreement_counts']}.
- The role-informed coordinator matched local role receipts on object-plus-basis {role_agreement['ROLE_INFORMED_COORDINATOR']['object_plus_basis']}/24, preference {role_agreement['ROLE_INFORMED_COORDINATOR']['pragmatic_preference']}/24, and completeness {role_agreement['ROLE_INFORMED_COORDINATOR']['assessment_completeness']}/24. Baseline agreement was {role_agreement['SINGLE_MODEL_BASELINE']['object_plus_basis']}/24, {role_agreement['SINGLE_MODEL_BASELINE']['pragmatic_preference']}/24, and {role_agreement['SINGLE_MODEL_BASELINE']['assessment_completeness']}/24.
- Coordinator-to-baseline cost ratios were input tokens {ratios['input_tokens']:.3f}, output tokens {ratios['output_tokens']:.3f}, and latency {ratios['latency_ms']:.3f}. Small-role scoring cost is reported separately and is not hidden inside these ratios.

## Interpretations

- Harness compilation can remove small-model syntax failures without transferring semantic authority away from Runtime.
- Anonymous code binding and natural-description likelihood are different failure modes. The successful transport representation was staged semantic classification with null and orientation controls.
- The coordinator demonstrably consumed role evidence: its outputs closely track all three receipts. This establishes influence, not benefit.
- Strong receipt influence creates an amplification risk. The unanimous fresh skeptic output propagated to 24/24 coordinator completeness decisions, so role credibility and dissent must be calibrated before promotion.
- The coordinator action field is a construction failure for this run because ACCEPT, CLARIFY, and ABSTAIN preconditions were not specified tightly enough. Action counts cannot support a caution or utility claim.

## Unknowns

- Fresh semantic correctness and collective gain remain unknown until GPT-5.6 and Gemini 3.1 labels are frozen and Kimi K3 adjudicates their disagreements.
- The current evidence cannot determine whether the 21 changed tuples are corrections or negative transfer.
- Cbit per token cannot be calculated before semantic outcomes exist.
- Completeness-axis transfer is especially uncertain because calibration labels were degenerate and the fresh specialist emitted COMPLETE uniformly.

## Intuition Triggers

- The useful unit of collaboration is not a free-form message but a typed cognitive action with explicit preconditions, evidence scope, and failure boundaries.
- A coordinator needs calibrated receipt credibility and contradiction handling, not just access to more opinions.
- Role specialization may exist even when models are not interchangeable, but it must survive a fresh panel before entering reputation or retention memory.
- Communication cost includes scored alternatives and coordinator rereading, not only generated tokens. Future anti-additive accounting should model both semantic gain and branch-evaluation work.

## Closure

- ACCEPT: canonical cognitive action receipts and experiment-local Harness compilation.
- REVISED: structured JSON generation into staged semantic scoring plus mechanical lifting.
- FAIL: anonymous code binding, description-likelihood classification, and unqualified action interpretation.
- PENDING: fresh correctness, collective gain, Cbit efficiency, role reputation, and action transition policy.
- Evidence coordinate: Internal Project Evidence plus Model Inference.
- Baseline insertion: No Baseline Object Update; experiment candidate only.

State: BLIND_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL
Phase ledger hash: {ledger['artifact_hash']}
"""


if __name__ == "__main__":
    main()

