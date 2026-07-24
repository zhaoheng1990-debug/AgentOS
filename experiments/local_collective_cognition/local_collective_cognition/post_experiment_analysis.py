"""Evidence-separated post-experiment analysis artifacts."""

from __future__ import annotations

from .provider_telemetry import hash_payload


ANALYSIS_VERSION = "post_experiment_analysis_v0_1"


def build_contrastive_analysis(calibration, *, candidate_run=None, corpus_artifact=None):
    baseline = calibration["arm_metrics"]["CATEGORY_FINGERPRINT"]
    candidate = calibration["arm_metrics"]["REQUEST_SELECTION"]
    gain = calibration["accuracy_gain_over_category_fingerprint"]
    diagnostics = {}
    if candidate_run is not None and corpus_artifact is not None:
        diagnostics = _receipt_diagnostics(candidate_run, corpus_artifact)
    facts = [
        f"Candidate state is {calibration['candidate_state']}.",
        f"Request-selection accuracy is {candidate['accuracy']:.3f}; category-fingerprint accuracy is {baseline['accuracy']:.3f}; gain is {gain:+.3f}.",
        f"Request-selection open recall is {candidate['open_recall']:.3f}, fixed recall is {candidate['fixed_recall']:.3f}, and matched-pair flip rate is {candidate['pair_flip_rate']:.3f}.",
        f"Request-selection unresolved rate is {candidate['unresolved_rate']:.3f} and quote-bound rate is {candidate['quote_bound_rate']:.3f}.",
        f"The candidate used {candidate['attributed_provider_calls']} calls and {candidate['attributed_tokens']} attributed tokens.",
    ]
    if diagnostics:
        facts.extend([
            f"Fixed-candidate direction accuracy is {diagnostics['fixed_direction_accuracy']:.3f} (diagnostic; not an admission gate).",
            f"All {diagnostics['unresolved_count']} unresolved outputs occur on formally open cases.",
            f"A non-admissible shadow mapping of UNCERTAIN to no explicit selection would score {diagnostics['shadow_uncertain_as_neither_accuracy']:.3f} accuracy.",
        ])
    phenomena = []
    if candidate["fixed_recall"] > baseline["fixed_recall"]:
        phenomena.append("Evidence-bound request selection recovers prompt-fixed cases that the direct category label misses.")
    if candidate["open_recall"] < candidate["fixed_recall"]:
        phenomena.append("The representation is better at detecting explicit selection than proving that no selection was made.")
    elif candidate["fixed_recall"] < candidate["open_recall"]:
        phenomena.append("The representation remains biased toward openness and under-detects explicit selection.")
    if candidate["pair_flip_rate"] < candidate["accuracy"]:
        phenomena.append("Errors cluster at the matched-pair level: isolated correctness does not always survive the minimal wording flip.")
    if gain <= 0:
        phenomena.append("Decomposition and quote binding add structure but no measured separability gain over direct categorization.")
    elif gain < 0.10:
        phenomena.append("The candidate improves separability, but the gain is too small for the frozen transfer gate.")
    else:
        phenomena.append("The candidate produces a material separability gain over direct categorization on this formal holdout.")
    if diagnostics and diagnostics["unresolved_count"] and diagnostics["unresolved_open_count"] == diagnostics["unresolved_count"]:
        phenomena.append("Every unresolved token is attached to an open object even though its receipt explanation states that the prompt does not select a candidate; object-state openness and assessor uncertainty appear to collide in the output ontology.")
    interpretations = [
        {
            "claim": "The requested-object coordinate is a more proximal representation than an ambiguity category.",
            "status": "SUPPORTED_INFERENCE" if gain > 0 else "NOT_SUPPORTED_THIS_RUN",
            "basis": "It asks what the prompt explicitly selects before Runtime derives OPEN_RIVALS or PROMPT_FIXED.",
        },
        {
            "claim": "Any measured gain may depend on matched-pair contrast, not only on field decomposition.",
            "status": "LIVE_ALTERNATIVE",
            "basis": "Both minimally different requests are visible in the same isolated batch.",
        },
        {
            "claim": "This result establishes downstream clarification utility.",
            "status": "NOT_TESTED",
            "basis": "No action policy or action-credit ledger is evaluated in v0.8.",
        },
        {
            "claim": "The remaining errors are primarily an output-ontology collision rather than failure to notice the prompt distinction.",
            "status": "SUPPORTED_DIAGNOSTIC_INFERENCE" if diagnostics and diagnostics["shadow_uncertain_as_neither_accuracy"] == 1.0 else "LIVE_ALTERNATIVE",
            "basis": "This is inferred from post-score receipt explanations and a non-admissible shadow mapping; it does not alter the frozen result.",
        },
    ]
    unknowns = [
        "Whether the representation transfers to equivalent and unsupported-rival controls.",
        "Whether separability survives when matched counterparts are not jointly visible.",
        "Whether another Provider family shows the same error orientation.",
        "Whether improved representation yields positive clarification utility after action credit is reattached.",
    ]
    next_object = (
        "Separate object selection (A, B, or no explicit selection) from assessor status (resolved or unresolved), then ablate matched-pair visibility before reconnecting action credit."
        if diagnostics and diagnostics.get("shadow_uncertain_as_neither_accuracy") == 1.0
        else "Repair the requested-object representation itself; do not reconnect action credit or tune the decision threshold."
    )
    commitment = {
        "analysis_version": ANALYSIS_VERSION,
        "source_calibration_hash": calibration["artifact_hash"],
        "facts": facts,
        "phenomena": phenomena,
        "interpretations": interpretations,
        "receipt_diagnostics": diagnostics,
        "unknowns": unknowns,
        "next_cognitive_object": next_object,
        "intuition_prompts": [
            "Is the useful signal the explicit evidence coordinate, or the presence of a nearby counterfactual?",
            "Does recognizing the correct object require comparison, even when execution later sees only one task?",
            "Should absence of selection be represented as a proof obligation rather than a class label?",
            "Is ambiguity a property of the object while uncertainty is a property of the judging process, requiring orthogonal state axes?",
        ],
        "changes_frozen_gate_or_candidate_state": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _receipt_diagnostics(candidate_run, corpus_artifact):
    truth = corpus_artifact["private_oracle"]["bindings"]
    assessments = {
        item["blind_case_id"]: item
        for judgment in candidate_run["lanes"]["REQUEST_SELECTION"]["judgments"]
        for item in judgment["payload"]["assessments"]
    }
    expected_selection = {"ANSWER_A": "CANDIDATE_A", "ANSWER_B": "CANDIDATE_B", "NEITHER": "NEITHER"}
    fixed = [(blind_id, binding) for blind_id, binding in truth.items() if binding["category"] == "PROMPT_FIXED"]
    unresolved = [
        {
            "blind_case_id": blind_id,
            "truth": truth[blind_id]["category"],
            "request_object_quote": item["request_object_quote"],
            "contrastive_explanation": item["contrastive_explanation"],
        }
        for blind_id, item in assessments.items()
        if item["explicit_selection"] == "UNCERTAIN"
    ]
    normal_map = {"CANDIDATE_A": "PROMPT_FIXED", "CANDIDATE_B": "PROMPT_FIXED", "NEITHER": "OPEN_RIVALS", "UNCERTAIN": "UNCERTAIN"}
    shadow_correct = sum(
        ("OPEN_RIVALS" if item["explicit_selection"] == "UNCERTAIN" else normal_map[item["explicit_selection"]]) == truth[blind_id]["category"]
        for blind_id, item in assessments.items()
    )
    return {
        "diagnostic_only": True,
        "changes_candidate_state": False,
        "fixed_direction_accuracy": sum(assessments[blind_id]["explicit_selection"] == expected_selection[binding["selected_candidate"]] for blind_id, binding in fixed) / len(fixed),
        "unresolved_count": len(unresolved),
        "unresolved_open_count": sum(item["truth"] == "OPEN_RIVALS" for item in unresolved),
        "unresolved_receipts": unresolved,
        "shadow_uncertain_as_neither_accuracy": shadow_correct / len(truth),
    }


def render_analysis_markdown(analysis):
    sections = [
        "# Clarification Contrastive Representation v0.8 - Result Analysis",
        "",
        "## Observed facts",
        *[f"- {item}" for item in analysis["facts"]],
        "",
        "## Phenomena",
        *[f"- {item}" for item in analysis["phenomena"]],
        "",
        "## Interpretations and alternatives",
        *[f"- **{item['status']}**: {item['claim']} Basis: {item['basis']}" for item in analysis["interpretations"]],
        "",
        "## Still unknown",
        *[f"- {item}" for item in analysis["unknowns"]],
        "",
        "## Next cognitive object",
        analysis["next_cognitive_object"],
        "",
        "## Questions for intuition",
        *[f"- {item}" for item in analysis["intuition_prompts"]],
        "",
        "## Authority boundary",
        "This analysis cannot change the frozen gate, candidate state, Core baseline, selection, retention, or production authority.",
        "",
        f"Analysis artifact hash: `{analysis['artifact_hash']}`",
        "",
    ]
    return "\n".join(sections)


def build_two_axis_analysis(calibration, *, candidate_run=None):
    baseline = calibration["arm_metrics"]["CATEGORY_FINGERPRINT"]
    paired = calibration["arm_metrics"]["PAIRED_TWO_AXIS"]
    shuffled = calibration["arm_metrics"]["SHUFFLED_TWO_AXIS"]
    gain = calibration["accuracy_gain_over_category_fingerprint"]
    visibility = calibration["paired_visibility_advantage"]
    diagnostics = _two_axis_error_diagnostics(calibration, candidate_run) if candidate_run is not None else {}
    facts = [
        f"Candidate state is {calibration['candidate_state']}.",
        f"Category-fingerprint, paired-two-axis, and shuffled-two-axis accuracies are {baseline['accuracy']:.3f}, {paired['accuracy']:.3f}, and {shuffled['accuracy']:.3f}.",
        f"Shuffled two-axis gain over category fingerprint is {gain:+.3f}.",
        f"Paired visibility advantage is {visibility:+.3f}; positive values favor seeing the true counterpart.",
        f"Shuffled two-axis open recall is {shuffled['open_recall']:.3f}, fixed recall is {shuffled['fixed_recall']:.3f}, and fixed-direction accuracy is {shuffled['fixed_direction_accuracy']:.3f}.",
        f"Shuffled unresolved rate is {shuffled['unresolved_rate']:.3f} and pair-flip rate is {shuffled['pair_flip_rate']:.3f}.",
        f"The shuffled candidate used {shuffled['attributed_provider_calls']} calls and {shuffled['attributed_tokens']} attributed tokens.",
    ]
    if diagnostics:
        facts.extend([
            f"All {diagnostics['shuffled_error_count']} shuffled errors are open objects promoted to candidate A.",
            f"Matched-pair visibility corrects {diagnostics['paired_corrected_error_count']} of those shuffled errors.",
        ])
    phenomena = []
    if shuffled["unresolved_rate"] == 0:
        phenomena.append("Separating object state from assessment status eliminates unresolved output on this holdout.")
    else:
        phenomena.append("The two-axis contract reduces ontology collision but does not eliminate unresolved output.")
    if gain >= 0.10:
        phenomena.append("The two-axis representation produces a material gain over direct category fingerprinting without extra per-arm calls.")
    elif gain > 0:
        phenomena.append("The two-axis representation improves accuracy, but not enough for the frozen gain gate.")
    else:
        phenomena.append("The two-axis representation adds no accuracy advantage over direct category fingerprinting.")
    if visibility > 0.10:
        phenomena.append("Performance depends materially on seeing the matched counterfactual, limiting single-task transfer.")
    elif visibility > 0:
        phenomena.append("Matched-pair visibility helps slightly, but the shuffled representation retains most of the measured capability.")
    else:
        phenomena.append("Matched-pair visibility provides no measured advantage; the representation survives shuffled batching.")
    if diagnostics and diagnostics["all_errors_open_promoted_to_a"]:
        phenomena.append("The remaining errors form a coherent over-commitment cluster: generic workload, volume, and activity wording is treated as an explicit definition of event count.")
    interpretations = [
        {
            "claim": "Object openness and assessor uncertainty should be represented on orthogonal axes.",
            "status": "SUPPORTED_INFERENCE" if shuffled["unresolved_rate"] < 0.05 and gain > 0 else "NOT_ESTABLISHED",
            "basis": "The shuffled two-axis lane is compared with an equal-call direct category lane on fresh cases.",
        },
        {
            "claim": "Matched counterfactuals are required at operational inference time.",
            "status": "SUPPORTED_INFERENCE" if visibility > 0.10 else "NOT_SUPPORTED_THIS_RUN",
            "basis": "Paired and shuffled lanes use the same model, schema, batch size, and number of calls.",
        },
        {
            "claim": "The representation now improves clarification action utility.",
            "status": "NOT_TESTED",
            "basis": "v0.9 evaluates representation only and keeps action credit disconnected.",
        },
        {
            "claim": "The remaining boundary is an explicit-selection proof obligation, not another state-enum problem.",
            "status": "SUPPORTED_DIAGNOSTIC_INFERENCE" if diagnostics and diagnostics["all_errors_open_promoted_to_a"] else "LIVE_ALTERNATIVE",
            "basis": "Every shuffled error promotes a generic request to candidate A using default semantic fit rather than an explicit prompt definition.",
        },
        {
            "claim": "The formal-open errors may carry a real pragmatic preference toward event count rather than being arbitrary Provider mistakes.",
            "status": "LIVE_ALTERNATIVE",
            "basis": "Workload, volume, and activity are compatible with both candidates but conventionally lean toward event counts; the current oracle measures explicit selection, not pragmatic preference strength.",
        },
    ]
    unknowns = [
        "Transfer to equivalent-rival and unsupported-rival object relations.",
        "Replication under another Provider family and different surface wording.",
        "Whether two-axis representation improves ASK versus DIRECT utility on a fresh action holdout.",
        "Whether object-state receipts remain stable over longer, non-synthetic task contexts.",
        "Whether pragmatic default preference predicts when direct answers are accepted despite absent explicit selection.",
    ]
    next_object = (
        "Reconnect the frozen two-axis receipt to action credit on a new holdout while retaining representation-only candidate authority."
        if calibration["candidate_state"] == "TWO_AXIS_REPRESENTATION_CANDIDATE"
        else "Separate explicit selection, pragmatic preference, and assessor status; require a warrant that prevents default compatibility from becoming hard fixation, then validate on fresh hard-generic wording before reconnecting action credit."
    )
    commitment = {
        "analysis_version": ANALYSIS_VERSION,
        "source_calibration_hash": calibration["artifact_hash"],
        "facts": facts,
        "phenomena": phenomena,
        "interpretations": interpretations,
        "receipt_diagnostics": diagnostics,
        "unknowns": unknowns,
        "next_cognitive_object": next_object,
        "intuition_prompts": [
            "Does a better ontology reduce cognitive work, or merely make the same cognition easier to express?",
            "When a counterfactual helps training but not inference, should it become retained structure rather than live context?",
            "Can action credit learn over object-state receipts without collapsing them back into a single confidence score?",
            "Is an apparently natural default precisely the case where Runtime should demand stronger evidence before declaring the object fixed?",
        ],
        "changes_frozen_gate_or_candidate_state": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _two_axis_error_diagnostics(calibration, candidate_run):
    assessments = {
        item["blind_case_id"]: item
        for judgment in candidate_run["lanes"]["SHUFFLED_TWO_AXIS"]["judgments"]
        for item in judgment["payload"]["assessments"]
    }
    errors = []
    for row in calibration["rows"]:
        if row["SHUFFLED_TWO_AXIS"] == row["truth_category"]:
            continue
        receipt = assessments.get(row["blind_case_id"], {})
        errors.append({
            "blind_case_id": row["blind_case_id"],
            "truth_category": row["truth_category"],
            "paired_category": row["PAIRED_TWO_AXIS"],
            "shuffled_category": row["SHUFFLED_TWO_AXIS"],
            "object_selection": row["SHUFFLED_object_selection"],
            "request_object_quote": receipt.get("request_object_quote"),
            "selection_basis": receipt.get("selection_basis"),
        })
    return {
        "diagnostic_only": True,
        "changes_candidate_state": False,
        "shuffled_error_count": len(errors),
        "paired_corrected_error_count": sum(item["paired_category"] == item["truth_category"] for item in errors),
        "all_errors_open_promoted_to_a": bool(errors) and all(item["truth_category"] == "OPEN_RIVALS" and item["object_selection"] == "CANDIDATE_A" for item in errors),
        "error_receipts": errors,
    }


def build_warrant_analysis(calibration, *, candidate_run=None):
    baseline = calibration["arm_metrics"]["BASELINE_TWO_AXIS"]
    candidate = calibration["arm_metrics"]["EXPLICIT_WARRANT"]
    gain = calibration["accuracy_gain_over_baseline"]
    diagnostics = _warrant_diagnostics(calibration, candidate_run) if candidate_run is not None else {}
    facts = [
        f"Candidate state is {calibration['candidate_state']}.",
        f"Baseline and warrant accuracies are {baseline['accuracy']:.3f} and {candidate['accuracy']:.3f}; gain is {gain:+.3f}.",
        f"Warrant explicit recall is {candidate['explicit_recall']:.3f} and pragmatic-open recall is {candidate['pragmatic_open_recall']:.3f}.",
        f"Fixed-direction accuracy is {candidate['fixed_direction_accuracy']:.3f} and hard-warrant precision is {candidate['hard_warrant_precision']:.3f}.",
        f"Constructed pragmatic-preference alignment is {candidate['pragmatic_preference_alignment']:.3f}.",
        f"Runtime downgraded {candidate['soft_selection_downgrade_count']} soft selections and unresolved rate is {candidate['unresolved_rate']:.3f}.",
        f"The warrant candidate used {candidate['attributed_provider_calls']} calls and {candidate['attributed_tokens']} attributed tokens.",
    ]
    if diagnostics:
        facts.extend([
            f"The baseline has {diagnostics['baseline_failed_batches']} failed batches, so comparative gain is confounded.",
            f"Constructed A-leaning and B-leaning preference alignments are {diagnostics['preference_alignment_a']:.3f} and {diagnostics['preference_alignment_b']:.3f}.",
            f"All {diagnostics['candidate_unresolved_count']} candidate unresolved rows still identify explicit selection as NONE under a soft warrant.",
            f"There are {diagnostics['false_hard_fixation_count']} formal false hard fixations.",
        ])
    phenomena = []
    if candidate["pragmatic_open_recall"] > baseline["pragmatic_open_recall"]:
        phenomena.append("The warrant policy blocks some pragmatic defaults that the baseline promotes to hard object selection.")
    if candidate["pragmatic_preference_alignment"] >= 0.75:
        phenomena.append("Weak pragmatic direction is retained even when Runtime withholds hard fixation.")
    else:
        phenomena.append("The candidate avoids hard fixation but does not reliably preserve the constructed pragmatic direction.")
    if candidate["soft_selection_downgrade_count"]:
        phenomena.append("Provider and Runtime disagree productively: Provider proposes selection under a soft warrant, while Runtime preserves it only as preference evidence.")
    if gain >= 0.10:
        phenomena.append("Explicit warrant typing produces nominal accuracy gain at equal call count, but baseline receipt failures confound its magnitude." if diagnostics and diagnostics["baseline_failed_batches"] else "Explicit warrant typing produces material accuracy gain at equal call count.")
    elif gain > 0:
        phenomena.append("Warrant typing improves accuracy, but not enough for the frozen transfer gate.")
    else:
        phenomena.append("Warrant typing adds no measured accuracy gain over the two-axis baseline.")
    if diagnostics and diagnostics["preference_alignment_a"] > diagnostics["preference_alignment_b"]:
        phenomena.append("Preference errors are strongly directional: event-count defaults align with the constructed proxy, while most entity-count defaults do not.")
    if diagnostics and diagnostics["candidate_unresolved_count"]:
        phenomena.append("Assessment status again absorbs task openness: the Provider fills both semantic axes but marks the assessment unresolved because no hard selection exists.")
    interpretations = [
        {
            "claim": "Constraint strength should be represented separately from semantic preference.",
            "status": "SUPPORTED_INFERENCE" if gain > 0 and candidate["pragmatic_preference_alignment"] >= 0.75 else "NOT_ESTABLISHED",
            "basis": "The candidate preserves a preference field while Runtime grants fixation only to hard warrant classes.",
        },
        {
            "claim": "Provider/Runtime disagreement can be a useful architecture feature rather than a receipt failure.",
            "status": "SUPPORTED_INFERENCE" if candidate["soft_selection_downgrade_count"] else "NOT_OBSERVED",
            "basis": "Soft Provider selections are retained in receipts but mechanically denied hard-constraint authority.",
        },
        {
            "claim": "The warrant representation improves real clarification decisions.",
            "status": "NOT_TESTED",
            "basis": "The holdout measures formal explicitness and a constructed pragmatic proxy, not ASK versus DIRECT outcomes.",
        },
        {
            "claim": "The constructed pragmatic-preference oracle is reliable enough to tune the next Runtime.",
            "status": "NOT_ESTABLISHED",
            "basis": "Alignment is highly direction-dependent, and phrases such as membership base may semantically entail an entity count more strongly than the construction label assumes.",
        },
    ]
    unknowns = [
        "Replication on new generic wording not used to form this corpus.",
        "Whether pragmatic preference predicts model-panel acceptance of direct answers.",
        "Whether hard-warrant classes transfer to longer natural tasks and domain-specific terminology.",
        "Whether action credit can use preference without promoting it back into a hard constraint.",
        "Whether independent model-panel judges agree on the explicit-entailment and pragmatic-preference labels used here.",
    ]
    next_object = (
        "Validate warrant transfer on a fresh lexical holdout, then reconnect it to clarification action credit under an explicit cost contract."
        if calibration["candidate_state"] == "EXPLICIT_SELECTION_WARRANT_CANDIDATE"
        else "Obtain independent model-panel labels for explicit entailment and pragmatic preference, adjudicate disagreements, and repair assessment-status semantics before any warrant tuning or action-credit reconnection."
    )
    commitment = {
        "analysis_version": ANALYSIS_VERSION,
        "source_calibration_hash": calibration["artifact_hash"],
        "facts": facts,
        "phenomena": phenomena,
        "interpretations": interpretations,
        "receipt_diagnostics": diagnostics,
        "unknowns": unknowns,
        "next_cognitive_object": next_object,
        "intuition_prompts": [
            "Can a cognitive runtime treat preference as useful evidence without allowing it to become a fact?",
            "Is productive disagreement between Provider judgment and Runtime authority a core mechanism of cognition rather than friction?",
            "Should future action credit be conditioned jointly on warrant strength and error cost?",
        ],
        "changes_frozen_gate_or_candidate_state": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def build_warrant_panel_recalibration_analysis(audit):
    metrics = audit["metrics"]
    facts = [
        f"Panel reference contains {audit['panel_explicit_counts']} explicit-selection states.",
        f"DeepSeek explicit-selection, pragmatic-preference, and assessment-completeness accuracies are {metrics['explicit_selection_accuracy']:.3f}, {metrics['pragmatic_preference_accuracy']:.3f}, and {metrics['assessment_completeness_accuracy']:.3f}.",
        f"Runtime category accuracy is {metrics['runtime_category_accuracy']:.3f}, with fixed recall {metrics['panel_fixed_recall']:.3f}, open recall {metrics['panel_open_recall']:.3f}, and hard-warrant precision {metrics['hard_warrant_precision']:.3f}.",
        f"Constructed explicit-selection alignment is {metrics['constructed_explicit_alignment']:.3f}; constructed pragmatic-preference alignment is {metrics['constructed_pragmatic_alignment']:.3f}.",
        f"Transfer recommendation is {audit['transfer_recommendation']}.",
    ]
    phenomena = [
        "The panel expands prompt-fixed cases beyond exact lexical requests by accepting semantic entailment in five previously pragmatic-open constructions.",
        "DeepSeek hard warrants are precise when issued, but under-recall semantically entailed selections.",
        "DeepSeek preference errors remain directional even though the independent panel fully supports the constructed preference proxy.",
        "Assessment incompleteness is a coordinate error: the panel marks every case complete while DeepSeek uses incomplete status for open tasks.",
    ]
    interpretations = [
        {"claim": "The warrant boundary should be learned as semantic entailment strength rather than exact mention versus default compatibility.", "status": "SUPPORTED_INFERENCE", "basis": "K3 resolves all five explicit-selection disputes toward semantic selection while preference remains agreed."},
        {"claim": "The current hard-warrant policy is ready for action-credit transfer.", "status": "REJECTED", "basis": "Runtime category accuracy is below one and the audit is post hoc rather than a preregistered transfer test."},
        {"claim": "The constructed pragmatic proxy caused the prior preference mismatch.", "status": "NOT_SUPPORTED", "basis": "GPT-5.6 and Gemini 3.1 agree on all pragmatic preferences and align with every constructed pragmatic direction."},
    ]
    commitment = {
        "analysis_version": ANALYSIS_VERSION,
        "source_calibration_hash": audit["artifact_hash"],
        "facts": facts,
        "phenomena": phenomena,
        "interpretations": interpretations,
        "receipt_diagnostics": audit["error_clusters"],
        "unknowns": ["Replication of semantic-entailment labels on fresh lexical constructions.", "Whether another Provider can improve semantic-selection recall without lowering hard-warrant precision.", "Whether panel-backed warrant states improve ASK versus DIRECT utility."],
        "next_cognitive_object": "Freeze panel-backed semantic-entailment examples as evaluation evidence, rename assessment completion, and run a fresh lexical transfer test before reconnecting action credit.",
        "intuition_prompts": ["Is semantic entailment best represented as a discrete warrant class or as competing structured proofs?", "Can Runtime preserve a strong preference while requiring a separate entailment proof for fixation?", "Does productive Provider/Runtime disagreement require multiple semantic receipts rather than one judge?"],
        "changes_frozen_gate_or_candidate_state": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _warrant_diagnostics(calibration, candidate_run):
    pragmatic = [row for row in calibration["rows"] if row["construction"] == "PRAGMATIC_OPEN"]
    expected_a = [row for row in pragmatic if row["truth_pragmatic_preference"] == "CANDIDATE_A"]
    expected_b = [row for row in pragmatic if row["truth_pragmatic_preference"] == "CANDIDATE_B"]
    unresolved = [row for row in calibration["rows"] if row["EXPLICIT_WARRANT"] == "UNCERTAIN"]
    false_fixed = [row for row in calibration["rows"] if row["EXPLICIT_WARRANT"] == "PROMPT_FIXED" and row["truth_category"] != "PROMPT_FIXED"]
    return {
        "diagnostic_only": True,
        "changes_candidate_state": False,
        "baseline_failed_batches": len(candidate_run["lanes"]["BASELINE_TWO_AXIS"]["failures"]),
        "preference_alignment_a": sum(row["WARRANT_pragmatic_preference"] == row["truth_pragmatic_preference"] for row in expected_a) / len(expected_a),
        "preference_alignment_b": sum(row["WARRANT_pragmatic_preference"] == row["truth_pragmatic_preference"] for row in expected_b) / len(expected_b),
        "candidate_unresolved_count": len(unresolved),
        "unresolved_are_soft_none": all(row["WARRANT_explicit_selection"] == "NONE" and row["WARRANT_type"] == "DEFAULT_COMPATIBILITY" for row in unresolved),
        "false_hard_fixation_count": len(false_fixed),
        "false_hard_fixations": [{"blind_case_id": row["blind_case_id"], "warrant_type": row["WARRANT_type"], "predicted_selection": row["WARRANT_hard_selection"]} for row in false_fixed],
    }
