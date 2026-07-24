from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_ROOT = REPO_ROOT / "agentos_core_slim_v0"
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(EXPERIMENT_ROOT))

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.benchmark_routing_calibration import routing_calibration_receipt_from_dict  # noqa: E402
from local_collective_cognition.calibrated_protocol import CalibratedCollaborationProtocol  # noqa: E402
from local_collective_cognition.calibrated_policy import CalibratedCandidateSignal, CalibratedModelPlan  # noqa: E402
from local_collective_cognition.calibrated_resolution_protocol import CalibratedResolutionProtocol  # noqa: E402
from local_collective_cognition.context_resolution_lifecycle import ContextResolutionLifecycle  # noqa: E402
from local_collective_cognition.context_resolution_policy import (  # noqa: E402
    ContextAwareResolutionPolicy,
    build_context_exploration_schedule,
)
from local_collective_cognition.context_resolution_protocol import ContextResolutionProtocol  # noqa: E402
from local_collective_cognition.iterated_context_protocol import IteratedContextResolutionProtocol  # noqa: E402
from local_collective_cognition.case_adjudication_policy import CaseAdjudicationPolicy  # noqa: E402
from local_collective_cognition.case_adjudication_protocol import CaseAdjudicationProtocol  # noqa: E402
from local_collective_cognition.argument_verification_receipt import MechanicalArgumentVerifier  # noqa: E402
from local_collective_cognition.verified_case_protocol import VerifiedCaseAdjudicationProtocol  # noqa: E402
from local_collective_cognition.verified_case_policy import VerifiedCaseAdjudicationPolicy  # noqa: E402
from local_collective_cognition.single_expression_protocol import SingleExpressionAdjudicationProtocol  # noqa: E402
from local_collective_cognition.single_expression_receipt import SingleExpressionVerifier  # noqa: E402
from local_collective_cognition.candidate_revision_policy import CandidateRevisionPolicy  # noqa: E402
from local_collective_cognition.candidate_revision_protocol import CandidateRevisionProtocol  # noqa: E402
from local_collective_cognition.candidate_revision_receipt import CandidateRevisionVerifier  # noqa: E402
from local_collective_cognition.typed_derivation_contracts import validate_typed_derivation  # noqa: E402
from local_collective_cognition.typed_derivation_protocol import TypedDerivationProtocol  # noqa: E402
from local_collective_cognition.typed_derivation_receipt import TypedDerivationVerifier  # noqa: E402
from local_collective_cognition.iterative_derivation_protocol import IterativeDerivationProtocol  # noqa: E402
from local_collective_cognition.staged_derivation_protocol import StagedDerivationProtocol  # noqa: E402
from local_collective_cognition.constrained_tool_protocol import ConstrainedToolProtocol  # noqa: E402
from local_collective_cognition.contextual_arbitration_policy import ContextualDisagreementPolicy  # noqa: E402
from local_collective_cognition.collective_protocol import PILOT_TASK_KINDS, LocalCollectiveCognitionProtocol  # noqa: E402
from local_collective_cognition.disagreement_resolution_lifecycle import DisagreementResolutionLifecycle  # noqa: E402
from local_collective_cognition.evidence_gated_policy import EvidenceSupportedReviewPolicy  # noqa: E402
from local_collective_cognition.evidence_gated_protocol import EvidenceGatedCollaborationProtocol  # noqa: E402
from local_collective_cognition.holdout_benchmark import HOLDOUT_ITEM_DOMAINS, build_holdout_harness  # noqa: E402
from local_collective_cognition.holdout_v2_benchmark import build_holdout_v2_harness  # noqa: E402
from local_collective_cognition.holdout_v3_benchmark import HOLDOUT_V3_QUESTIONS, build_holdout_v3_harness  # noqa: E402
from local_collective_cognition.holdout_v3_benchmark import HOLDOUT_V3_ITEM_DOMAINS  # noqa: E402
from local_collective_cognition.holdout_v4_benchmark import (  # noqa: E402
    HOLDOUT_V4_ITEM_DOMAINS,
    HOLDOUT_V4_QUESTIONS,
    build_holdout_v4_harness,
)
from local_collective_cognition.holdout_v5_benchmark import (  # noqa: E402
    HOLDOUT_V5_ITEM_DOMAINS,
    HOLDOUT_V5_QUESTIONS,
    build_holdout_v5_harness,
)
from local_collective_cognition.holdout_v6_benchmark import (  # noqa: E402
    HOLDOUT_V6_ITEM_DOMAINS,
    HOLDOUT_V6_ITEM_FINGERPRINTS,
    HOLDOUT_V6_QUESTIONS,
    build_holdout_v6_harness,
)
from local_collective_cognition.holdout_v7_benchmark import (  # noqa: E402
    HOLDOUT_V7_ITEM_DOMAINS,
    HOLDOUT_V7_ITEM_FINGERPRINTS,
    HOLDOUT_V7_QUESTIONS,
    build_holdout_v7_harness,
)
from local_collective_cognition.holdout_v8_benchmark import (  # noqa: E402
    HOLDOUT_V8_ITEM_FINGERPRINTS,
    HOLDOUT_V8_QUESTIONS,
    build_holdout_v8_harness,
)
from local_collective_cognition.holdout_v9_benchmark import (  # noqa: E402
    HOLDOUT_V9_ITEM_FINGERPRINTS,
    HOLDOUT_V9_QUESTIONS,
    build_holdout_v9_harness,
)
from local_collective_cognition.holdout_v10_benchmark import (  # noqa: E402
    HOLDOUT_V10_ITEM_DOMAINS,
    HOLDOUT_V10_ITEM_FINGERPRINTS,
    HOLDOUT_V10_QUESTIONS,
    build_holdout_v10_harness,
)
from local_collective_cognition.holdout_v11_benchmark import (  # noqa: E402
    HOLDOUT_V11_ITEM_FINGERPRINTS,
    HOLDOUT_V11_QUESTIONS,
    build_holdout_v11_harness,
)
from local_collective_cognition.holdout_v12_benchmark import (  # noqa: E402
    HOLDOUT_V12_ITEM_FINGERPRINTS,
    HOLDOUT_V12_QUESTIONS,
    build_holdout_v12_harness,
)
from local_collective_cognition.holdout_v13_benchmark import (  # noqa: E402
    HOLDOUT_V13_ITEM_FINGERPRINTS,
    HOLDOUT_V13_ROUTING_FINGERPRINTS,
    HOLDOUT_V13_QUESTIONS,
    build_holdout_v13_harness,
)
from local_collective_cognition.holdout_v14_benchmark import (  # noqa: E402
    HOLDOUT_V14_ITEM_FINGERPRINTS,
    HOLDOUT_V14_QUESTIONS,
    HOLDOUT_V14_ROUTING_FINGERPRINTS,
    build_holdout_v14_harness,
)
from local_collective_cognition.holdout_v15_benchmark import (  # noqa: E402
    HOLDOUT_V15_ITEM_FINGERPRINTS,
    HOLDOUT_V15_QUESTIONS,
    HOLDOUT_V15_ROUTING_FINGERPRINTS,
    build_holdout_v15_harness,
)
from local_collective_cognition.holdout_v16_benchmark import (  # noqa: E402
    HOLDOUT_V16_QUESTIONS,
    HOLDOUT_V16_ROUTING_FINGERPRINTS,
    build_holdout_v16_harness,
)
from local_collective_cognition.holdout_v17_benchmark import (  # noqa: E402
    HOLDOUT_V17_ROUTING_FINGERPRINTS,
    build_holdout_v17_harness,
)
from local_collective_cognition.holdout_v18_benchmark import (  # noqa: E402
    HOLDOUT_V18_QUESTIONS,
    HOLDOUT_V18_ROUTING_FINGERPRINTS,
    build_holdout_v18_harness,
)
from local_collective_cognition.holdout_v19_benchmark import (  # noqa: E402
    HOLDOUT_V19_QUESTIONS,
    HOLDOUT_V19_ROUTING_FINGERPRINTS,
    build_holdout_v19_harness,
)
from local_collective_cognition.hierarchical_fingerprint_credit import (  # noqa: E402
    HierarchicalFingerprintCreditLedger,
    build_micro_probe_schedule,
)
from local_collective_cognition.independent_resolution_policy import IndependentDisagreementResolutionPolicy  # noqa: E402
from local_collective_cognition.independent_resolution_protocol import IndependentDisagreementResolutionProtocol  # noqa: E402
from local_collective_cognition.multi_cycle_resolution import MultiCycleResolutionLifecycle  # noqa: E402
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    ProviderInvocationTelemetry,
    ProviderTelemetryLedger,
    hash_payload,
)
from local_collective_cognition.routing_calibration import build_calibrated_profiles  # noqa: E402
from local_collective_cognition.reliability_lifecycle import (  # noqa: E402
    ReliabilityLifecycleLedger,
    build_shadow_exploration_schedule,
)
from local_collective_cognition.reliability_lifecycle_protocol import ReliabilityLifecycleCollaborationProtocol  # noqa: E402
from local_collective_cognition.resolution_exploration_policy import (  # noqa: E402
    ResolutionExplorationPolicy,
    build_resolution_exploration_schedule,
)
from local_collective_cognition.structural_fingerprint_protocol import StructuralFingerprintCollaborationProtocol  # noqa: E402
from local_collective_cognition.structural_operator_credit import build_structural_operator_credit  # noqa: E402
from local_collective_cognition.structural_operator_policy import (  # noqa: E402
    StructuralOperatorCompetitionPolicy,
    build_second_ranked_model_map,
    build_structural_operator_schedule,
)
from local_collective_cognition.structural_operator_protocol import StructuralOperatorCompetitionProtocol  # noqa: E402
from local_collective_cognition.structured_provider_json import schema_failures  # noqa: E402
from local_collective_cognition.task_fingerprints import build_item_fingerprints  # noqa: E402
from local_collective_cognition.task_fingerprints import FINGERPRINT_TO_DOMAIN  # noqa: E402


CALIBRATION_TRUTH = {
    "logic-2": "A", "schedule-2": "C", "implication-2": "B", "modular-2": "D",
    "probability-2": "B", "sets-2": "C", "sequence-2": "D", "rate-2": "B",
    "bayes-2": "C", "code-2": "A", "string-2": "D", "causal-2": "B",
}
HOLDOUT_V2_TRUTH = {
    "logic-3": "A", "schedule-3": "C", "implication-3": "B", "modular-3": "D",
    "probability-3": "B", "sets-3": "C", "sequence-3": "D", "rate-3": "B",
    "bayes-3": "A", "code-3": "A", "string-3": "B", "causal-3": "C",
}
HOLDOUT_V3_TRUTH = {
    "logic-4": "A", "schedule-4": "B", "implication-4": "C", "modular-4": "C",
    "probability-4": "C", "sets-4": "D", "sequence-4": "C", "rate-4": "B",
    "bayes-4": "B", "code-4": "D", "string-4": "B", "causal-4": "B",
}
HOLDOUT_V4_TRUTH = {
    "logic-5": "A", "schedule-5": "B", "implication-5": "C", "modular-5": "B",
    "probability-5": "C", "sets-5": "B", "sequence-5": "D", "rate-5": "C",
    "bayes-5": "B", "code-5": "D", "string-5": "B", "causal-5": "B",
}
HOLDOUT_V5_TRUTH = {
    "logic-6": "A", "schedule-6": "B", "implication-6": "C", "modular-6": "B",
    "probability-6": "C", "sets-6": "C", "sequence-6": "D", "rate-6": "B",
    "bayes-6": "B", "code-6": "C", "string-6": "D", "causal-6": "B",
}
HOLDOUT_V6_TRUTH = {
    "logic-7": "A", "schedule-7": "B", "implication-7": "C", "modular-7": "A",
    "probability-7": "C", "sets-7": "B", "sequence-7": "D", "rate-7": "C",
    "bayes-7": "B", "code-7": "D", "string-7": "B", "causal-7": "B",
}
HOLDOUT_V7_TRUTH = {
    "logic-8": "A", "schedule-8": "B", "implication-8": "D", "modular-8": "B",
    "probability-8": "C", "sets-8": "D", "sequence-8": "B", "rate-8": "C",
    "bayes-8": "B", "code-8": "D", "string-8": "A", "causal-8": "C",
}
HOLDOUT_V8_TRUTH = {
    "logic-9": "A", "schedule-9": "B", "implication-9": "C", "modular-9": "D",
    "probability-9": "C", "sets-9": "C", "sequence-9": "D", "rate-9": "B",
    "bayes-9": "B", "code-9": "D", "string-9": "B", "causal-9": "C",
}
HOLDOUT_V9_TRUTH = {
    "logic-10": "B", "schedule-10": "C", "implication-10": "D", "modular-10": "A",
    "probability-10": "C", "sets-10": "D", "sequence-10": "B", "rate-10": "C",
    "bayes-10": "B", "code-10": "A", "string-10": "C", "causal-10": "D",
}
HOLDOUT_V10_TRUTH = {
    "logic-11": "C", "schedule-11": "D", "implication-11": "A", "modular-11": "B",
    "probability-11": "D", "sets-11": "A", "sequence-11": "C", "rate-11": "D",
    "bayes-11": "A", "code-11": "B", "string-11": "D", "causal-11": "A",
}
HOLDOUT_V11_TRUTH = {
    "logic-12": "C", "schedule-12": "D", "implication-12": "A", "modular-12": "B",
    "probability-12": "C", "sets-12": "A", "sequence-12": "D", "rate-12": "C",
    "bayes-12": "B", "code-12": "A", "string-12": "C", "causal-12": "D",
}
HOLDOUT_V12_TRUTH = {
    "logic-13": "C", "schedule-13": "A", "implication-13": "D", "modular-13": "D",
    "probability-13": "B", "sets-13": "C", "sequence-13": "A", "rate-13": "B",
    "bayes-13": "C", "code-13": "D", "string-13": "A", "causal-13": "B",
}
HOLDOUT_V13_TRUTH = {
    "arithmetic-14": "C", "rate-14": "B", "percent-14": "C", "sets-14": "C",
    "probability-14": "C", "bayes-14": "B", "modular-14": "C", "ratio-14": "B",
    "average-14": "C", "code-14": "D", "string-14": "A", "unit-14": "B",
}
HOLDOUT_V14_TRUTH = {
    "arithmetic-15": "C", "rate-15": "B", "percent-15": "C", "sets-15": "B",
    "probability-15": "C", "bayes-15": "B", "modular-15": "B", "ratio-15": "B",
    "average-15": "B", "code-15": "C", "string-15": "A", "unit-15": "B",
}
HOLDOUT_V15_TRUTH = {
    "arithmetic-16": "C", "rate-16": "C", "percent-16": "C", "sets-16": "B",
    "probability-16": "C", "bayes-16": "C", "modular-16": "A", "ratio-16": "B",
    "average-16": "C", "code-16": "C", "string-16": "A", "unit-16": "B",
}
HOLDOUT_V16_TRUTH = {
    "arithmetic-17": "C", "rate-17": "B", "percent-17": "B", "sets-17": "C",
    "probability-17": "B", "bayes-17": "B", "modular-17": "C", "ratio-17": "B",
    "average-17": "C", "code-17": "C", "string-17": "A", "unit-17": "C",
}
HOLDOUT_V17_TRUTH = {
    "arithmetic-18": "B", "rate-18": "C", "percent-18": "B", "sets-18": "C",
    "probability-18": "B", "bayes-18": "B", "modular-18": "C", "ratio-18": "B",
    "average-18": "C", "code-18": "C", "string-18": "A", "unit-18": "C",
}
HOLDOUT_V18_TRUTH = {
    "arithmetic-19": "B", "rate-19": "B", "percent-19": "C", "sets-19": "C",
    "probability-19": "B", "bayes-19": "C", "modular-19": "C", "ratio-19": "B",
    "average-19": "C", "code-19": "C", "string-19": "A", "unit-19": "C",
}
HOLDOUT_V19_TRUTH = {
    "arithmetic-20": "B", "rate-20": "B", "percent-20": "C", "sets-20": "C",
    "probability-20": "B", "bayes-20": "C", "modular-20": "B", "ratio-20": "B",
    "average-20": "C", "code-20": "C", "string-20": "A", "unit-20": "C",
}


def _wrong(truth):
    return {item_id: "D" if answer != "D" else "A" for item_id, answer in truth.items()}


def _candidate(model_id, answers, confidence, source, calls=12, tokens=1200):
    return {
        "model_id": model_id,
        "answers": [
            {"item_id": item_id, "answer": answer, "confidence": confidence, "had_structured_retry": False}
            for item_id, answer in answers.items()
        ],
        "source_harness_receipt_hash": source * 64,
        "provider_calls": calls,
        "total_tokens": tokens,
    }


def _calibration_receipt():
    return build_holdout_harness().calibrate_routing(
        calibration_id="calibrated-fixture",
        item_domains=HOLDOUT_ITEM_DOMAINS,
        candidates=(
            _candidate("small-a", _wrong(CALIBRATION_TRUTH), 0.9, "a", calls=20, tokens=1800),
            _candidate("small-b", CALIBRATION_TRUTH, 0.7, "b", tokens=1000),
            _candidate("small-c", _wrong(CALIBRATION_TRUTH), 0.6, "c", tokens=800),
        ),
    )


class FixtureAdapter:
    def __init__(self, model_id, ledger, answers, confidence=0.9):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + model_id,
            model_id=model_id,
            task_kinds=PILOT_TASK_KINDS,
            max_timeout_seconds=600,
        )
        self.ledger = ledger
        self.answers = answers
        self.confidence = confidence

    def invoke(self, task):
        item_id = task.inputs["benchmark_item_ids"][0]
        result = {
            "item_id": item_id,
            "answer": self.answers[item_id],
            "confidence": self.confidence,
            "evidence_refs": list(task.allowed_evidence),
        }
        self.ledger.record(ProviderInvocationTelemetry.create(
            telemetry_id=f"fixture-{self.profile.model_id}-{task.task_id}",
            provider_id=self.profile.provider_id,
            model_id=self.profile.model_id,
            backend="fixture",
            task_id=task.task_id,
            task_kind=task.task_kind,
            task_contract_hash=task.contract_hash(),
            status="COMPLETED",
            input_tokens=10,
            output_tokens=5,
            cached_tokens=0,
            latency_ms=10,
            api_cost=0.0,
            tool_calls=0,
            tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence),
            output_hash=hash_payload(result),
            thinking_present=False,
            thinking_char_count=0,
            thinking_hash="",
            error_type="",
        ))
        return {"result": result, "usage": {}, "provenance_refs": list(task.allowed_evidence)}


class CaseFixtureAdapter(FixtureAdapter):
    def __init__(
        self, *args, judge_label="", malformed_argument=False, malformed_judgment=False,
        verified_argument_by_label=None, single_expression_by_label=None,
        candidate_revision_by_label=None, typed_derivation_by_label=None,
        iterative_actions_by_label=None, staged_actions_by_label=None,
        constrained_actions_by_label=None, **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.judge_label = judge_label
        self.malformed_argument = malformed_argument
        self.malformed_judgment = malformed_judgment
        self.verified_argument_by_label = verified_argument_by_label
        self.single_expression_by_label = single_expression_by_label
        self.candidate_revision_by_label = candidate_revision_by_label
        self.typed_derivation_by_label = typed_derivation_by_label
        self.iterative_actions_by_label = iterative_actions_by_label
        self.staged_actions_by_label = staged_actions_by_label
        self.constrained_actions_by_label = constrained_actions_by_label
        self.observed_tasks = []

    def invoke(self, task):
        self.observed_tasks.append(task)
        context = task.inputs["round_context"]
        if task.task_kind == "pilot_constrained_tool_action":
            actions = self.constrained_actions_by_label[context["original_candidate"]]
            selected = actions[min(context["turn"] - 1, len(actions) - 1)]
            options = context["constrained_tool_channel"]["options"]
            result = next(
                item["result"] for item in options
                if all(item["result"].get(key) == value for key, value in selected.items())
            )
        elif task.task_kind == "pilot_disagreement_argument":
            if self.staged_actions_by_label is not None:
                actions = self.staged_actions_by_label[context["original_candidate"]]
                selected = actions[min(context["control_turn"] - 1, len(actions) - 1)]
                identity = {"item_id": task.inputs["benchmark_item_ids"][0],
                            "candidate_id": context["candidate_id"]}
                if context["role"] == "staged_action_selection":
                    result = {**identity, "action": selected["action"],
                              "evidence_refs": list(task.allowed_evidence)}
                elif selected["action"] == "APPLY":
                    result = {**identity, "operator": selected["operator"],
                              "inputs": selected["inputs"],
                              "evidence_refs": list(task.allowed_evidence)}
                else:
                    result = {**identity, "selected_step": selected["inputs"][0],
                              "proposed_candidate": selected["proposed_candidate"],
                              "evidence_refs": list(task.allowed_evidence)}
            elif self.iterative_actions_by_label is not None:
                actions = self.iterative_actions_by_label[context["original_candidate"]]
                selected = actions[min(context["turn"] - 1, len(actions) - 1)]
                result = {"item_id": task.inputs["benchmark_item_ids"][0],
                          "candidate_id": context["candidate_id"], **selected,
                          "evidence_refs": list(task.allowed_evidence)}
            elif self.typed_derivation_by_label is not None:
                original = context["original_candidate"]
                steps, proposed = self.typed_derivation_by_label[original]
                result = {
                    "item_id": task.inputs["benchmark_item_ids"][0],
                    "candidate_id": context["candidate_id"], "proposed_candidate": proposed,
                    "steps": steps, "result_step": steps[-1]["step_id"] if steps else "NONE",
                    "evidence_refs": list(task.allowed_evidence),
                }
            elif self.candidate_revision_by_label is not None:
                original = context["original_candidate"]
                expression, proposed = self.candidate_revision_by_label[original]
                result = {
                    "item_id": task.inputs["benchmark_item_ids"][0],
                    "candidate_id": context["candidate_id"], "expression": expression,
                    "proposed_candidate": proposed, "evidence_refs": list(task.allowed_evidence),
                }
            elif self.single_expression_by_label is not None:
                result = {
                    "item_id": task.inputs["benchmark_item_ids"][0],
                    "candidate_id": context["candidate_id"],
                    "expression": self.single_expression_by_label[context["candidate_label"]],
                    "evidence_refs": list(task.allowed_evidence),
                }
            elif self.verified_argument_by_label is not None:
                expression, claimed = self.verified_argument_by_label[context["candidate_label"]]
                result = {
                    "item_id": task.inputs["benchmark_item_ids"][0],
                    "candidate_id": context["candidate_id"],
                    "argument": "The expression derives the assigned choice from public values.",
                    "derived_facts": [{"fact_id": "f1", "expression": expression,
                                       "claimed_result": claimed}],
                    "conclusion_value": claimed, "uncertainty": "low",
                    "evidence_refs": list(task.allowed_evidence),
                }
            else:
                result = {
                    "item_id": task.inputs["benchmark_item_ids"][0],
                    "candidate_id": context["candidate_id"],
                    "argument": "The assigned choice follows from the stated constraints.",
                    "reasoning_steps": ["Apply the public rule", "Check the assigned choice"],
                    "uncertainty": "low", "evidence_refs": list(task.allowed_evidence),
                }
            if self.malformed_argument:
                result["argument"] = ""
        elif task.task_kind == "pilot_disagreement_adjudication":
            selected = next(
                item["candidate_id"] for item in context["candidate_records"]
                if item["candidate_label"] == self.judge_label
            )
            result = {
                "item_id": task.inputs["benchmark_item_ids"][0],
                "selected_candidate": selected, "adjudicability": "ADJUDICABLE",
                "confidence": 0.95, "decisive_reason": "One argument satisfies the public rule.",
                "evidence_refs": list(task.allowed_evidence),
            }
            if self.malformed_judgment:
                result.pop("selected_candidate")
        else:
            return super().invoke(task)
        self.ledger.record(ProviderInvocationTelemetry.create(
            telemetry_id=f"case-fixture-{self.profile.model_id}-{task.task_id}",
            provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            backend="fixture", task_id=task.task_id, task_kind=task.task_kind,
            task_contract_hash=task.contract_hash(), status="COMPLETED",
            input_tokens=10, output_tokens=5, cached_tokens=0, latency_ms=10,
            api_cost=0.0, tool_calls=0, tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence), output_hash=hash_payload(result),
            thinking_present=False, thinking_char_count=0, thinking_hash="", error_type="",
        ))
        return {"result": result, "usage": {}, "provenance_refs": list(task.allowed_evidence)}


def test_harness_calibration_shrinks_sparse_scores_and_hides_truths():
    receipt = _calibration_receipt()
    strong = next(item for item in receipt.model_records if item.model_id == "small-b")
    causal = next(item for item in strong.domain_scores if item[0] == "causal")

    assert strong.global_posterior < 1.0
    assert 0.0 < causal[3] < 1.0
    assert strong.brier_score > 0.0
    assert len(receipt.reviewer_records) == 24
    rendered = json.dumps(receipt.as_dict(), sort_keys=True)
    assert "expected_answer" not in rendered
    assert "ground_truth" not in rendered
    assert routing_calibration_receipt_from_dict(receipt.as_dict()).receipt_hash == receipt.receipt_hash


def test_review_outcome_receipt_separates_corrections_from_harms():
    receipt = _calibration_receipt()
    decisions = []
    for index, (item_id, truth) in enumerate(CALIBRATION_TRUTH.items()):
        wrong = "D" if truth != "D" else "A"
        primary, final, action = truth, truth, "STOP_LOW_VALUE_PER_COST"
        if index == 0:
            primary, final, action = wrong, truth, "REVIEW_RESOLVED"
        elif index == 1:
            primary, final, action = truth, wrong, "REVIEW_RESOLVED"
        decisions.append({
            "item_id": item_id, "primary_model_id": "small-a", "reviewer_model_id": "small-b",
            "action": action, "primary_answer": primary, "final_answer": final,
            "expected_net_cbit": 0.1,
        })
    outcome = build_holdout_harness().calibrate_routing(
        experiment_id="review-outcome-fixture",
        calibration_receipt_hash=receipt.receipt_hash,
        route_decisions=tuple(decisions),
        item_domains=HOLDOUT_ITEM_DOMAINS,
    )

    assert outcome.reviewed_count == 2
    assert outcome.corrected_count == 1
    assert outcome.harmed_count == 1
    assert outcome.observed_net_cbit == 0.0


def test_calibrated_protocol_preserves_best_member_with_operational_route():
    receipt = _calibration_receipt()
    profiles, reviewer_ledger = build_calibrated_profiles(receipt)
    ledger = ProviderTelemetryLedger()
    wrong = _wrong(HOLDOUT_V2_TRUTH)
    adapters = {
        "small-a": FixtureAdapter("small-a", ledger, wrong),
        "small-b": FixtureAdapter("small-b", ledger, HOLDOUT_V2_TRUTH),
        "small-c": FixtureAdapter("small-c", ledger, wrong),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v2_harness(),
        small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", ledger, HOLDOUT_V2_TRUTH),
        telemetry_ledger=ledger,
        reviewer_model_id="small-b",
        synthesizer_model_id="small-c",
    )
    report = CalibratedCollaborationProtocol(
        base=base,
        calibration_receipt=receipt,
        profiles=profiles,
        reviewer_ledger=reviewer_ledger,
    ).run("calibrated-fixture")

    assert report["calibrated_arm"]["score"] == 1.0
    assert report["calibrated_arm"]["provider_calls"] == 12
    assert report["majority_arm"]["provider_calls"] == 36
    assert {item["primary_model_id"] for item in report["route_decisions"]} == {"small-b"}
    assert report["protocol"]["operational_route_replayable_without_peer_outputs"] is True
    assert report["review_outcome_receipt"]["reviewed_count"] == 0
    assert report["review_outcome_receipt"]["harness_owned"] is True
    assert report["comparisons"]["calibrated_improvement_status"] == "BEST_MEMBER_PRESERVED_WITH_LOWER_GROUP_WORK"


def test_evidence_gate_blocks_unsupported_review_and_allows_supported_pair():
    receipt = _calibration_receipt()
    profiles, reviewer_ledger = build_calibrated_profiles(receipt)
    policy = EvidenceSupportedReviewPolicy(confidence_threshold=0.95)
    plans = tuple(
        CalibratedModelPlan(model_id=item.model_id, predicted_success=item.global_posterior, expected_work=item.expected_work())
        for item in profiles.values()
    )
    unsupported = policy.route(
        CalibratedCandidateSignal("small-b", "q", "A", 0.5, 0.6, profiles["small-b"].expected_work()),
        plans=plans, domain="quantitative", reviewer_ledger=reviewer_ledger,
    )
    supported = policy.route(
        CalibratedCandidateSignal("small-a", "q", "A", 0.5, 0.2, profiles["small-a"].expected_work()),
        plans=plans, domain="quantitative", reviewer_ledger=reviewer_ledger,
    )

    assert unsupported.action == "STOP_REVIEW_EVIDENCE_UNSUPPORTED"
    assert unsupported.evidence_eligible is False
    assert supported.action == "REVIEW"
    assert supported.evidence_eligible is True


def test_evidence_gated_protocol_runs_on_third_holdout_without_reviews():
    receipt = _calibration_receipt()
    profiles, reviewer_ledger = build_calibrated_profiles(receipt)
    ledger = ProviderTelemetryLedger()
    wrong = _wrong(HOLDOUT_V3_TRUTH)
    adapters = {
        "small-a": FixtureAdapter("small-a", ledger, wrong),
        "small-b": FixtureAdapter("small-b", ledger, HOLDOUT_V3_TRUTH),
        "small-c": FixtureAdapter("small-c", ledger, wrong),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v3_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", ledger, HOLDOUT_V3_TRUTH),
        telemetry_ledger=ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    report = EvidenceGatedCollaborationProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles, reviewer_ledger=reviewer_ledger,
    ).run("evidence-gated-fixture")

    assert report["evidence_gated_arm"]["score"] == 1.0
    assert report["evidence_gated_arm"]["provider_calls"] == 12
    assert report["comparisons"]["reviewed_items"] == 0
    assert report["protocol"]["holdout_benchmark"] == "local-reasoning-holdout-v0-3"
    assert report["posthoc_domain_diagnostics"]["candidate_only"] is True
    assert report["posthoc_domain_diagnostics"]["routing_authority"] is False
    assert len(report["posthoc_domain_diagnostics"]["receipts"]) == 3


def test_holdout_v3_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V3_QUESTIONS}
    x = 3
    for n in (1, 2, 3):
        x = 2 * x + n
    swapped = "".join("ABCDEF"[index + 1] + "ABCDEF"[index] for index in range(0, 6, 2))
    rotated = swapped[1:] + swapped[0]

    assert x == 35 and questions["code-4"].choices[3] == "D: 35"
    assert rotated == "ADCFEB" and questions["string-4"].choices[1] == "B: ADCFEB"
    assert 80 - (45 + 38 - 18) == 15
    assert 180 / 2.25 * 3.5 == 280
    assert abs((0.05 * 0.9) / (0.05 * 0.9 + 0.95 * 0.05) - 0.5) < 0.02
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V3_TRUTH.items()],
        "evidence_refs": list(build_holdout_v3_harness().evidence_refs),
    }
    assert build_holdout_v3_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def test_reliability_lifecycle_promotes_candidate_and_accounts_shadow_exploration():
    receipt = _calibration_receipt()
    base_profiles, reviewer_ledger = build_calibrated_profiles(receipt)
    holdout_v3 = build_holdout_v3_harness()
    diagnostics = []
    for index, (model_id, answers) in enumerate((
        ("small-a", _wrong(HOLDOUT_V3_TRUTH)),
        ("small-b", HOLDOUT_V3_TRUTH),
        ("small-c", _wrong(HOLDOUT_V3_TRUTH)),
    )):
        diagnostics.append(holdout_v3.calibrate_reliability(
            calibration_id="lifecycle-fixture-v3", model_id=model_id,
            candidate_output={
                "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in answers.items()],
                "evidence_refs": list(holdout_v3.evidence_refs),
            },
            item_domains=HOLDOUT_V3_ITEM_DOMAINS,
            source_harness_receipt_hash=str(index + 1) * 64,
        ).as_dict())
    ledger = ReliabilityLifecycleLedger(calibration_receipt=receipt, base_profiles=base_profiles)
    candidate = ledger.ingest_candidate(
        cycle_id="lifecycle-fixture-v3", sequence=1,
        diagnostics={"candidate_only": True, "routing_authority": False, "receipts": diagnostics},
    )
    promotion = ledger.promote(candidate_hash=candidate.candidate_hash, validation_ref="d" * 64)
    profiles, snapshot = ledger.snapshot()
    schedule = build_shadow_exploration_schedule(
        item_domains=HOLDOUT_V4_ITEM_DOMAINS, profiles=profiles, budget=2,
    )

    provider_ledger = ProviderTelemetryLedger()
    wrong = _wrong(HOLDOUT_V4_TRUTH)
    adapters = {
        "small-a": FixtureAdapter("small-a", provider_ledger, wrong),
        "small-b": FixtureAdapter("small-b", provider_ledger, HOLDOUT_V4_TRUTH),
        "small-c": FixtureAdapter("small-c", provider_ledger, wrong),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v4_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V4_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    report = ReliabilityLifecycleCollaborationProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles,
        reviewer_ledger=reviewer_ledger, lifecycle_snapshot=snapshot,
        cycle_candidate=candidate, promotion_receipt=promotion,
        profile_receipt_hash=snapshot["snapshot_hash"], exploration_schedule=schedule,
    ).run("lifecycle-fixture-v4")

    assert promotion.status == "PROMOTED_FOR_EXPERIMENT"
    assert snapshot["core_baseline_authority"] is False
    assert report["reliability_lifecycle_arm"]["score"] == 1.0
    assert report["reliability_lifecycle_arm"]["provider_calls"] == 14
    assert report["comparisons"]["exploration_items"] == 2
    assert all(item["used_for_current_answer"] is False for item in report["exploration_events"])


def test_holdout_v4_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V4_QUESTIONS}
    x = 2
    for n in (1, 2, 3):
        x = 2 * (x + n)
    rotated = "ABCDE"[-2:] + "ABCDE"[:-2]
    transformed = rotated[-1] + rotated[1:-1] + rotated[0]

    assert x == 38 and questions["code-5"].choices[3] == "D: 38"
    assert transformed == "CEABD" and questions["string-5"].choices[1] == "B: CEABD"
    assert 100 - (55 + 48 - 25) == 22
    assert 240 / 3.2 * 4.5 == 337.5
    assert abs((0.02 * 0.95) / (0.02 * 0.95 + 0.98 * 0.02) - 0.5) < 0.02
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V4_TRUTH.items()],
        "evidence_refs": list(build_holdout_v4_harness().evidence_refs),
    }
    assert build_holdout_v4_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def test_contextual_majority_arbitrates_only_supported_domain():
    source_primary = dict(HOLDOUT_V4_TRUTH)
    for item_id, domain in HOLDOUT_V4_ITEM_DOMAINS.items():
        if domain == "formal":
            source_primary[item_id] = _wrong({item_id: HOLDOUT_V4_TRUTH[item_id]})[item_id]
    source_harness = build_holdout_v4_harness()
    operator_receipt = source_harness.calibrate_routing(
        experiment_id="operator-source-v4", source_report_hash="e" * 64,
        route_decisions=tuple({"item_id": item_id, "primary_answer": answer} for item_id, answer in source_primary.items()),
        majority_answer_vector=HOLDOUT_V4_TRUTH,
        solo_answer_vectors=(source_primary, HOLDOUT_V4_TRUTH, _wrong(HOLDOUT_V4_TRUTH)),
        item_domains=HOLDOUT_V4_ITEM_DOMAINS,
    )
    receipt = _calibration_receipt()
    profiles, reviewer_ledger = build_calibrated_profiles(receipt)
    profiles = {
        model_id: replace(
            profile,
            global_posterior=0.6 if model_id == "small-b" else 0.1,
            domain_scores=tuple(
                (domain, correct, total, 0.6 if model_id == "small-b" else 0.1)
                for domain, correct, total, _ in profile.domain_scores
            ),
            confidence_bins=tuple((label, correct, total, mean, 0.2) for label, correct, total, mean, _ in profile.confidence_bins),
            retry_scores=tuple((label, correct, total, 0.2) for label, correct, total, _ in profile.retry_scores),
        )
        for model_id, profile in profiles.items()
    }
    provider_ledger = ProviderTelemetryLedger()
    peer_a = _wrong(HOLDOUT_V5_TRUTH)
    peer_c = _wrong(HOLDOUT_V5_TRUTH)
    for item_id, domain in HOLDOUT_V5_ITEM_DOMAINS.items():
        if domain == "formal":
            peer_c[item_id] = HOLDOUT_V5_TRUTH[item_id]
    adapters = {
        "small-a": FixtureAdapter("small-a", provider_ledger, peer_a),
        "small-b": FixtureAdapter("small-b", provider_ledger, HOLDOUT_V5_TRUTH, confidence=0.5),
        "small-c": FixtureAdapter("small-c", provider_ledger, peer_c),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v5_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V5_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    report = CalibratedCollaborationProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles,
        reviewer_ledger=reviewer_ledger,
        policy=ContextualDisagreementPolicy(operator_receipt=operator_receipt),
        item_domains=HOLDOUT_V5_ITEM_DOMAINS, arm_namespace="HOLDOUT_V5_FIXTURE",
    ).run("contextual-arbitration-fixture")

    assert report["calibrated_arm"]["score"] == 1.0
    assert report["calibrated_arm"]["provider_calls"] == 18
    assert report["comparisons"]["arbitrated_items"] == 3
    assert sum(item["action"] == "STOP_OPERATOR_LOW_VALUE" for item in report["route_decisions"]) == 9


def test_holdout_v5_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V5_QUESTIONS}
    x = 1
    for n in (1, 2, 3):
        x = (x + n) * n
    blocked = "ABC"[::-1] + "DEF"[::-1]
    rotated = blocked[-1] + blocked[:-1]

    assert x == 33 and questions["code-6"].choices[2] == "C: 33"
    assert rotated == "DCBAFE" and questions["string-6"].choices[3] == "D: DCBAFE"
    assert 120 - (70 + 65 - 40) == 25
    assert 360 / 4.8 * 2.6 == 195
    assert abs((0.10 * 0.85) / (0.10 * 0.85 + 0.90 * 0.10) - 0.5) < 0.02
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V5_TRUTH.items()],
        "evidence_refs": list(build_holdout_v5_harness().evidence_refs),
    }
    assert build_holdout_v5_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def _fingerprint_profiles_fixture():
    calibration_receipt = _calibration_receipt()
    base_profiles, reviewer_ledger = build_calibrated_profiles(calibration_receipt)
    ledger = HierarchicalFingerprintCreditLedger(base_profiles=base_profiles)
    cycles = (
        (build_holdout_harness(), CALIBRATION_TRUTH),
        (build_holdout_v2_harness(), HOLDOUT_V2_TRUTH),
        (build_holdout_v3_harness(), HOLDOUT_V3_TRUTH),
        (build_holdout_v4_harness(), HOLDOUT_V4_TRUTH),
        (build_holdout_v5_harness(), HOLDOUT_V5_TRUTH),
    )
    for sequence, (harness, truth) in enumerate(cycles, start=1):
        receipts = []
        for index, model_id in enumerate(("small-a", "small-b", "small-c"), start=1):
            answers = truth if model_id == "small-b" else _wrong(truth)
            receipts.append(harness.calibrate_reliability(
                calibration_id=f"fingerprint-fixture-{sequence}",
                model_id=model_id,
                candidate_output={
                    "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in answers.items()],
                    "evidence_refs": list(harness.evidence_refs),
                },
                item_domains=build_item_fingerprints(tuple(truth)),
                source_harness_receipt_hash=str(index) * 64,
            ))
        source_hash = f"{sequence:x}" * 64
        candidate = ledger.ingest_candidate(
            cycle_id=f"fingerprint-cycle-{sequence}", sequence=sequence,
            source_report_hash=source_hash, receipts=tuple(receipts),
        )
        ledger.promote(candidate_hash=candidate.candidate_hash, source_report_hash=source_hash)
    profiles, snapshot = ledger.snapshot()
    return calibration_receipt, reviewer_ledger, profiles, snapshot


def test_hierarchical_fingerprint_credit_is_promoted_bound_and_budgeted():
    _, _, profiles, snapshot = _fingerprint_profiles_fixture()
    schedule = build_micro_probe_schedule(
        item_domains=HOLDOUT_V6_ITEM_DOMAINS,
        item_fingerprints=HOLDOUT_V6_ITEM_FINGERPRINTS,
        profiles=profiles,
        budget=3,
    )

    assert snapshot["harness_owned_receipts_only"] is True
    assert snapshot["core_baseline_authority"] is False
    assert len(snapshot["promotion_receipt_hashes"]) == 5
    assert len(schedule) <= 3
    assert profiles["small-b"].context_reliability("implication_chain", "formal") > 0.5
    assert profiles["small-a"].context_reliability("implication_chain", "formal") < 0.5
    with pytest.raises(ValueError, match="fingerprint_credit_promotion_candidate_missing"):
        HierarchicalFingerprintCreditLedger(base_profiles={"a": object(), "b": object()}).promote(
            candidate_hash="a" * 64, source_report_hash="b" * 64,
        )


def test_structural_fingerprint_protocol_accounts_one_peer_probe():
    receipt, reviewer_ledger, profiles, snapshot = _fingerprint_profiles_fixture()
    provider_ledger = ProviderTelemetryLedger()
    wrong = _wrong(HOLDOUT_V6_TRUTH)
    adapters = {
        "small-a": FixtureAdapter("small-a", provider_ledger, wrong),
        "small-b": FixtureAdapter("small-b", provider_ledger, HOLDOUT_V6_TRUTH),
        "small-c": FixtureAdapter("small-c", provider_ledger, wrong),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v6_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V6_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    report = StructuralFingerprintCollaborationProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles,
        reviewer_ledger=reviewer_ledger, fingerprint_credit_snapshot=snapshot,
        probe_schedule={"logic-7": "small-a"},
    ).run("structural-fingerprint-fixture")

    assert report["structural_fingerprint_arm"]["score"] == 1.0
    assert report["structural_fingerprint_arm"]["provider_calls"] == 13
    assert report["comparisons"]["micro_probe_items"] == 1
    assert report["micro_probe_outcome_receipt"]["unchanged_count"] == 1
    assert report["protocol"]["v08_outcomes_used_for_current_route"] is False


def test_holdout_v6_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V6_QUESTIONS}
    x = 2
    for n in (1, 2, 3):
        x = x * n + n
    transformed = ("ABCDEF"[2:] + "ABCDEF"[:2])[::-1]

    assert x == 27 and questions["code-7"].choices[3] == "D: 27"
    assert transformed == "BAFEDC" and questions["string-7"].choices[1] == "B: BAFEDC"
    assert 150 - (90 + 80 - 50) == 30
    assert 420 / 5.6 * 3.4 == 255
    assert 1 - (7 / 10) * (6 / 9) == pytest.approx(8 / 15)
    assert (0.04 * 0.90) / (0.04 * 0.90 + 0.96 * 0.04) == pytest.approx(0.5, abs=0.02)
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V6_TRUTH.items()],
        "evidence_refs": list(build_holdout_v6_harness().evidence_refs),
    }
    assert build_holdout_v6_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def _operator_credit_fixture():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot = _fingerprint_profiles_fixture()
    primary_answers = dict(HOLDOUT_V6_TRUTH)
    for item_id in ("modular-7", "sets-7", "rate-7", "string-7"):
        primary_answers[item_id] = _wrong({item_id: HOLDOUT_V6_TRUTH[item_id]})[item_id]
    route_decisions = tuple({
        "item_id": item_id, "primary_model_id": "small-b", "primary_answer": answer,
    } for item_id, answer in primary_answers.items())
    operator_receipt = build_holdout_v6_harness().calibrate_routing(
        experiment_id="operator-credit-fixture",
        source_report_hash="d" * 64,
        source_profile_hash=fingerprint_snapshot["snapshot_hash"],
        route_decisions=route_decisions,
        second_model_by_item={item_id: "small-c" for item_id in HOLDOUT_V6_TRUTH},
        majority_answer_vector=HOLDOUT_V6_TRUTH,
        solo_answer_vectors={
            "small-a": HOLDOUT_V6_TRUTH,
            "small-b": primary_answers,
            "small-c": HOLDOUT_V6_TRUTH,
        },
        item_fingerprints=HOLDOUT_V6_ITEM_FINGERPRINTS,
    )
    operator_credit = build_structural_operator_credit(
        receipt=operator_receipt, fingerprint_domains=FINGERPRINT_TO_DOMAIN,
    )
    schedule = build_structural_operator_schedule(
        profiles=profiles, operator_credit=operator_credit,
        item_domains=HOLDOUT_V7_ITEM_DOMAINS,
        item_fingerprints=HOLDOUT_V7_ITEM_FINGERPRINTS,
        budget=4,
    )
    return receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, schedule


def test_structural_operator_credit_separates_outcome_and_information_value():
    _, _, _, _, operator_receipt, operator_credit, schedule = _operator_credit_fixture()
    rendered = json.dumps(operator_receipt.as_dict(), sort_keys=True)

    assert sum(item.peer_corrections for item in operator_receipt.records) == 4
    assert sum(item.peer_harms for item in operator_receipt.records) == 0
    assert "expected_answer" not in rendered and "ground_truth" not in rendered
    assert operator_credit.core_baseline_authority is False
    assert all(item.future_information_cbit >= 0.0 for item in operator_credit.records)
    assert len(schedule) <= 4


def test_structural_operator_protocol_executes_only_positive_scheduled_work():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, schedule = _operator_credit_fixture()
    schedule = {"modular-8": "PEER_SECOND"}
    provider_ledger = ProviderTelemetryLedger()
    adapters = {
        model_id: FixtureAdapter(model_id, provider_ledger, HOLDOUT_V7_TRUTH, confidence=0.45)
        for model_id in ("small-a", "small-b", "small-c")
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v7_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V7_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    report = StructuralOperatorCompetitionProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles, reviewer_ledger=reviewer_ledger,
        fingerprint_credit_snapshot=fingerprint_snapshot,
        operator_evidence_receipt=operator_receipt,
        operator_credit_snapshot=operator_credit,
        operator_schedule=schedule,
        policy=StructuralOperatorCompetitionPolicy(
            operator_credit=operator_credit, operator_schedule=schedule,
            item_fingerprints=HOLDOUT_V7_ITEM_FINGERPRINTS,
            information_value_weight=20.0, work_cost_weight=0.0,
        ),
    ).run("structural-operator-fixture")

    assert report["structural_operator_arm"]["score"] == 1.0
    assert report["structural_operator_arm"]["provider_calls"] >= 12
    assert report["comparisons"]["scheduled_paid_operators"] == len(schedule)
    assert report["comparisons"]["peer_harms"] == 0
    assert report["peer_override_counterfactual_receipt"]["reviewed_count"] == 1
    assert report["protocol"]["immediate_and_future_cbit_separated"] is True


def test_holdout_v7_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V7_QUESTIONS}
    x = 3
    for n in (1, 2, 3):
        x = (x + n) * 2
    swapped = "".join("ABCDEF"[index + 1] + "ABCDEF"[index] for index in range(0, 6, 2))
    transformed = swapped[1:] + swapped[0]

    assert x == 46 and questions["code-8"].choices[3] == "D: 46"
    assert transformed == "ADCFEB" and questions["string-8"].choices[0] == "A: ADCFEB"
    assert 200 - (110 + 95 - 60) == 55
    assert 525 / 7 * 4.4 == 330
    assert (2 * 5 * 4) / (9 * 8) == pytest.approx(5 / 9)
    assert (0.05 * 0.90) / (0.05 * 0.90 + 0.95 * 0.05) == pytest.approx(0.5, abs=0.02)
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V7_TRUTH.items()],
        "evidence_refs": list(build_holdout_v7_harness().evidence_refs),
    }
    assert build_holdout_v7_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def _resolution_lifecycle_fixture():
    peer_answers = {"logic-8": "A", "sets-8": "A", "code-8": "D"}
    routes = tuple({
        "item_id": item_id, "action": "PEER_VERIFICATION_RESOLVED",
        "primary_answer": "C", "final_answer": "C",
    } for item_id in peer_answers)
    evidence = build_holdout_v7_harness().calibrate_routing(
        experiment_id="resolution-evidence-fixture",
        source_report_hash="a" * 64,
        source_operator_credit_hash="b" * 64,
        route_decisions=routes,
        resolver_peer_answer_by_item=peer_answers,
        item_fingerprints=HOLDOUT_V7_ITEM_FINGERPRINTS,
    )
    lifecycle = DisagreementResolutionLifecycle(receipt=evidence)
    candidate = lifecycle.ingest_candidate()
    promotion = lifecycle.promote(candidate_hash=candidate.candidate_hash, validation_ref="c" * 64)
    return evidence, lifecycle, candidate, promotion, lifecycle.snapshot()


def test_disagreement_resolution_evidence_is_hidden_and_promotion_bound():
    evidence, _, candidate, promotion, snapshot = _resolution_lifecycle_fixture()
    rendered = json.dumps(evidence.as_dict(), sort_keys=True)

    assert sum(item.peer_corrections for item in evidence.records) == 2
    assert sum(item.peer_harms for item in evidence.records) == 0
    assert "expected_answer" not in rendered and "ground_truth" not in rendered
    assert candidate.routing_authority is False
    assert promotion.status == "PROMOTED_FOR_EXPERIMENT"
    assert snapshot.get("quantifier_syllogism").evidence_level == "FINGERPRINT"
    assert snapshot.get("implication_chain").evidence_level == "DOMAIN"
    assert snapshot.get("causal_identification").evidence_level == "GLOBAL"

    unpromoted = DisagreementResolutionLifecycle(receipt=evidence)
    unpromoted.ingest_candidate()
    with pytest.raises(ValueError, match="resolution_snapshot_promotion_required"):
        unpromoted.snapshot()


def test_independent_resolver_ignores_primary_selection_confidence():
    _, _, _, _, snapshot = _resolution_lifecycle_fixture()
    _, _, _, _, _, operator_credit, _ = _operator_credit_fixture()
    policy = IndependentDisagreementResolutionPolicy(
        operator_credit=operator_credit,
        operator_schedule={"implication-9": "PEER_SECOND"},
        item_fingerprints=HOLDOUT_V8_ITEM_FINGERPRINTS,
        resolution_credit=snapshot,
    )
    decision = policy.route(
        CalibratedCandidateSignal("small-b", "implication-9", "A", 0.99, 0.99, 10.0),
        plans=(
            CalibratedModelPlan("small-b", 0.99, 10.0),
            CalibratedModelPlan("small-c", 0.01, 10.0),
            CalibratedModelPlan("small-a", 0.01, 10.0),
        ),
        domain="formal", reviewer_ledger=object(),
    )
    resolved = policy.resolve_probe(
        replace(decision, action="VERIFY_PEER", reviewer_model_id="small-c"),
        CalibratedCandidateSignal("small-b", "implication-9", "A", 0.99, 0.99, 10.0),
        CalibratedCandidateSignal("small-c", "implication-9", "C", 0.01, 0.01, 10.0),
    )

    assert resolved.action == "PEER_OVERRIDE_RESOLVED"
    assert resolved.final_answer == "C"
    assert resolved.resolution_evidence_level == "DOMAIN"


def test_independent_resolution_protocol_corrects_fixture_disagreement():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    evidence, _, candidate, promotion, resolution_credit = _resolution_lifecycle_fixture()
    schedule = {"implication-9": "PEER_SECOND"}
    provider_ledger = ProviderTelemetryLedger()
    primary_answers = dict(HOLDOUT_V8_TRUTH)
    primary_answers["implication-9"] = "A"
    peer_answers = _wrong(HOLDOUT_V8_TRUTH)
    peer_answers["implication-9"] = "C"
    adapters = {
        "small-a": FixtureAdapter("small-a", provider_ledger, _wrong(HOLDOUT_V8_TRUTH), confidence=0.1),
        "small-b": FixtureAdapter("small-b", provider_ledger, primary_answers, confidence=0.99),
        "small-c": FixtureAdapter("small-c", provider_ledger, peer_answers, confidence=0.1),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v8_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V8_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    policy = IndependentDisagreementResolutionPolicy(
        operator_credit=operator_credit, operator_schedule=schedule,
        item_fingerprints=HOLDOUT_V8_ITEM_FINGERPRINTS, resolution_credit=resolution_credit,
        information_value_weight=20.0, work_cost_weight=0.0,
    )
    report = IndependentDisagreementResolutionProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles, reviewer_ledger=reviewer_ledger,
        fingerprint_credit_snapshot=fingerprint_snapshot,
        operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
        operator_schedule=schedule, resolution_evidence_receipt=evidence,
        resolution_candidate=candidate, resolution_promotion=promotion,
        resolution_credit_snapshot=resolution_credit, policy=policy,
    ).run("independent-resolution-fixture")

    assert report["resolution_lifecycle_arm"]["score"] == 1.0
    assert report["comparisons"]["resolution_overrides"] == 1
    assert report["comparisons"]["resolution_corrections"] == 1
    assert report["comparisons"]["resolution_harms"] == 0
    assert report["protocol"]["primary_selection_credit_used_for_resolution"] is False
    assert "v09_outcomes_used_for_current_route" not in report["protocol"]
    assert "structural_operator_improvement_status" not in report["comparisons"]


def test_holdout_v8_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V8_QUESTIONS}
    x = 1
    for n in (1, 2, 3):
        x = 3 * x + n
    swapped = "".join("ABCDEF"[index + 1] + "ABCDEF"[index] for index in range(0, 6, 2))
    transformed = swapped[-2:] + swapped[:-2]

    assert x == 45 and questions["code-9"].choices[3] == "D: 45"
    assert transformed == "FEBADC" and questions["string-9"].choices[1] == "B: FEBADC"
    assert 180 - (100 + 90 - 55) == 45
    assert 640 / 8 * 3.75 == 300
    assert 1 - (8 / 10) * (7 / 9) * (6 / 8) == pytest.approx(8 / 15)
    assert (0.02 * 0.95) / (0.02 * 0.95 + 0.98 * 0.02) == pytest.approx(0.5, abs=0.02)
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V8_TRUTH.items()],
        "evidence_refs": list(build_holdout_v8_harness().evidence_refs),
    }
    assert build_holdout_v8_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def _multi_cycle_resolution_fixture():
    v09_evidence, _, _, _, _ = _resolution_lifecycle_fixture()
    peer_answers = {"sets-9": "A", "rate-9": "A"}
    routes = (
        {"item_id": "sets-9", "action": "PRIMARY_KEEP_RESOLVED", "primary_answer": "C",
         "final_answer": "C", "resolution_expected_net_cbit": -0.2},
        {"item_id": "rate-9", "action": "PRIMARY_KEEP_RESOLVED", "primary_answer": "B",
         "final_answer": "B", "resolution_expected_net_cbit": -0.05},
    )
    v10_evidence = build_holdout_v8_harness().calibrate_routing(
        experiment_id="multi-cycle-v10-fixture", source_report_hash="d" * 64,
        source_operator_credit_hash="e" * 64, route_decisions=routes,
        resolver_peer_answer_by_item=peer_answers,
        item_fingerprints=HOLDOUT_V8_ITEM_FINGERPRINTS,
        source_actions=("PRIMARY_KEEP_RESOLVED",),
    )
    lifecycle = MultiCycleResolutionLifecycle()
    candidates = []
    promotions = []
    for index, evidence in enumerate((v09_evidence, v10_evidence), start=1):
        candidate = lifecycle.ingest_candidate(evidence)
        candidates.append(candidate)
        promotions.append(lifecycle.promote(
            candidate_hash=candidate.candidate_hash, validation_ref=str(index + 4) * 64,
        ))
    return (v09_evidence, v10_evidence), tuple(candidates), tuple(promotions), lifecycle.snapshot()


def test_multi_cycle_resolution_calibrates_predictions_and_requires_all_promotions():
    evidence, _, _, snapshot = _multi_cycle_resolution_fixture()

    assert snapshot.prediction_count == 2
    assert snapshot.mean_predicted_override_net == -0.125
    assert snapshot.mean_observed_override_net == -1.0
    assert snapshot.mean_absolute_error == 0.875
    assert snapshot.get("inclusion_exclusion").expected_override_net_cbit < 0.0
    assert len(snapshot.source_receipt_hashes) == 2

    incomplete = MultiCycleResolutionLifecycle()
    incomplete.ingest_candidate(evidence[0])
    with pytest.raises(ValueError, match="multi_cycle_resolution_promotions_incomplete"):
        incomplete.snapshot()


def test_resolution_exploration_is_sparse_budgeted_and_nonoverlapping():
    _, _, _, snapshot = _multi_cycle_resolution_fixture()
    existing = {"sets-10": "PEER_SECOND"}
    schedule = build_resolution_exploration_schedule(
        resolution_credit=snapshot, item_fingerprints=HOLDOUT_V9_ITEM_FINGERPRINTS,
        existing_schedule=existing, budget=2,
    )

    assert len(schedule) == 2
    assert not set(schedule) & set(existing)
    assert "causal-10" in schedule
    assert set(schedule.values()) == {"PEER_SECOND"}


def test_calibrated_resolution_protocol_explores_without_harming_current_answer():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    evidence, candidates, promotions, resolution_credit = _multi_cycle_resolution_fixture()
    exploration = {"causal-10": "PEER_SECOND"}
    provider_ledger = ProviderTelemetryLedger()
    peer_answers = _wrong(HOLDOUT_V9_TRUTH)
    adapters = {
        "small-a": FixtureAdapter("small-a", provider_ledger, _wrong(HOLDOUT_V9_TRUTH), confidence=0.1),
        "small-b": FixtureAdapter("small-b", provider_ledger, HOLDOUT_V9_TRUTH, confidence=0.99),
        "small-c": FixtureAdapter("small-c", provider_ledger, peer_answers, confidence=0.1),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v9_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V9_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    report = CalibratedResolutionProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles, reviewer_ledger=reviewer_ledger,
        fingerprint_credit_snapshot=fingerprint_snapshot,
        operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
        operator_schedule=exploration, acquisition_schedule={},
        resolution_exploration_schedule=exploration,
        resolution_evidence_receipts=evidence, resolution_candidates=candidates,
        resolution_promotions=promotions, resolution_credit_snapshot=resolution_credit,
        policy=ResolutionExplorationPolicy(
            operator_credit=operator_credit, operator_schedule=exploration,
            item_fingerprints=HOLDOUT_V9_ITEM_FINGERPRINTS,
            resolution_credit=resolution_credit, exploration_items=("causal-10",),
            work_cost_weight=0.0,
        ),
    ).run("calibrated-resolution-fixture")

    assert report["calibrated_resolution_arm"]["score"] == 1.0
    assert report["comparisons"]["executed_resolution_explorations"] == 1
    assert report["comparisons"]["resolution_primary_keeps"] == 1
    assert report["comparisons"]["resolution_harms"] == 0
    assert report["peer_override_counterfactual_receipt"]["harmed_count"] == 1
    assert report["comparisons"]["resolver_gate_status"] == "SAFE_ABSTENTION_PREVENTED_HARM"
    assert report["comparisons"]["resolver_prevented_harms"] == 1
    assert report["protocol"]["current_exploration_outcomes_used_for_current_route"] is False


def test_holdout_v9_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V9_QUESTIONS}
    x = 2
    for n in (1, 2, 3):
        x = 2 * x + n
    rotated = "ABCDEF"[2:] + "ABCDEF"[:2]
    transformed = "".join(rotated[index + 1] + rotated[index] for index in range(0, 6, 2))

    assert x == 27 and questions["code-10"].choices[0] == "A: 27"
    assert transformed == "DCFEBA" and questions["string-10"].choices[2] == "C: DCFEBA"
    assert 220 - (130 + 120 - 70) == 40
    assert 720 / 9 * 4.25 == 340
    assert 1 - (9 / 12) * (8 / 11) == pytest.approx(5 / 11)
    assert (0.10 * 0.80) / (0.10 * 0.80 + 0.90 * 0.10) == pytest.approx(8 / 17)
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V9_TRUTH.items()],
        "evidence_refs": list(build_holdout_v9_harness().evidence_refs),
    }
    assert build_holdout_v9_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def _context_resolution_fixture():
    primary_answers = dict(HOLDOUT_V10_TRUTH)
    primary_answers["implication-11"] = "D"
    vectors = {
        "small-a": HOLDOUT_V10_TRUTH,
        "small-b": primary_answers,
        "small-c": HOLDOUT_V10_TRUTH,
    }
    route = ({
        "item_id": "implication-11", "action": "PRIMARY_KEEP_RESOLVED",
        "primary_model_id": "small-b", "reviewer_model_id": "small-c",
        "primary_answer": "D", "final_answer": "D",
    },)
    lifecycle = ContextResolutionLifecycle()
    receipts, candidates, promotions = [], [], []
    for index in range(5):
        receipt = build_holdout_v10_harness().calibrate_routing(
            experiment_id=f"context-cycle-{index}", source_report_hash=str(index + 1) * 64,
            source_credit_hash=str(index + 4) * 64, route_decisions=route,
            solo_answer_vectors=vectors, item_fingerprints=HOLDOUT_V10_ITEM_FINGERPRINTS,
            context_source_actions=("PRIMARY_KEEP_RESOLVED",),
        )
        receipts.append(receipt)
        candidate = lifecycle.ingest_candidate(receipt)
        candidates.append(candidate)
        promotions.append(lifecycle.promote(
            candidate_hash=candidate.candidate_hash, validation_ref=format(index + 7, "x") * 64,
        ))
    return tuple(receipts), tuple(candidates), tuple(promotions), lifecycle.snapshot()


def test_context_resolution_receipt_hides_answers_truth_and_requires_promotions():
    receipts, _, _, snapshot = _context_resolution_fixture()
    rendered = json.dumps(receipts[0].as_dict(), sort_keys=True)

    assert "expected_answer" not in rendered and "ground_truth" not in rendered
    assert '"answer"' not in rendered and '"truth"' not in rendered
    assert snapshot.pair_credit("small-b", "small-c").corrections == 5
    assert snapshot.resolve(
        fingerprint="implication_chain", primary_model_id="small-b",
        peer_model_id="small-c", support_topology="THIRD_SUPPORTS_PEER",
    ).override_evidence_eligible is True

    incomplete = ContextResolutionLifecycle()
    incomplete.ingest_candidate(receipts[0])
    with pytest.raises(ValueError, match="context_resolution_promotions_incomplete"):
        incomplete.snapshot()


def test_context_exploration_is_sparse_budgeted_and_nonoverlapping():
    _, _, profiles, _, _, _, _ = _operator_credit_fixture()
    _, _, _, context_credit = _context_resolution_fixture()
    existing = {"sets-11": "PEER_SECOND"}
    schedule = build_context_exploration_schedule(
        context_credit=context_credit, profiles=profiles,
        item_domains=HOLDOUT_V10_ITEM_DOMAINS,
        item_fingerprints=HOLDOUT_V10_ITEM_FINGERPRINTS,
        existing_schedule=existing, budget=2,
    )

    assert len(schedule) == 2
    assert not set(schedule) & set(existing)
    assert set(schedule.values()) == {"PEER_SECOND"}


def test_context_resolution_protocol_charges_witness_and_corrects_disagreement():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"implication-11": "PEER_SECOND"}
    provider_ledger = ProviderTelemetryLedger()
    primary_answers = dict(HOLDOUT_V10_TRUTH)
    primary_answers["implication-11"] = "D"
    adapters = {
        "small-a": FixtureAdapter("small-a", provider_ledger, HOLDOUT_V10_TRUTH, confidence=0.1),
        "small-b": FixtureAdapter("small-b", provider_ledger, primary_answers, confidence=0.99),
        "small-c": FixtureAdapter("small-c", provider_ledger, HOLDOUT_V10_TRUTH, confidence=0.1),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v10_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V10_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    policy = ContextAwareResolutionPolicy(
        operator_credit=operator_credit, operator_schedule=schedule,
        item_fingerprints=HOLDOUT_V10_ITEM_FINGERPRINTS,
        resolution_credit=resolution_credit, exploration_items=(),
        context_credit=context_credit, model_ids=tuple(profiles),
        information_value_weight=20.0, work_cost_weight=0.0,
    )
    report = ContextResolutionProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles, reviewer_ledger=reviewer_ledger,
        fingerprint_credit_snapshot=fingerprint_snapshot,
        operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
        operator_schedule=schedule, acquisition_schedule=schedule,
        resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
        resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
        resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
        context_candidates=context_candidates, context_promotions=context_promotions,
        context_credit_snapshot=context_credit, policy=policy,
    ).run("context-resolution-fixture")

    assert report["context_resolution_arm"]["score"] == 1.0
    assert report["context_resolution_arm"]["rounds"] == 3
    assert report["comparisons"]["context_witness_items"] == 1
    assert report["comparisons"]["context_peer_overrides"] == 1
    assert report["comparisons"]["resolution_corrections"] == 1
    assert report["comparisons"]["resolution_harms"] == 0
    assert report["comparisons"]["context_positive_heldout_net_cbit"] is True


def test_holdout_v10_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V10_QUESTIONS}
    x = 1
    for n in (1, 2, 3):
        x = 2 * (x + n)
    transformed = "".join("ABCDEF"[::-1][index + 1] + "ABCDEF"[::-1][index] for index in range(0, 6, 2))

    assert x == 30 and questions["code-11"].choices[1] == "B: 30"
    assert transformed == "EFCDAB" and questions["string-11"].choices[3] == "D: EFCDAB"
    assert 160 - (95 + 85 - 50) == 30
    assert 840 / 12 * 5.5 == 385
    assert 1 - (7 / 10) * (6 / 9) == pytest.approx(8 / 15)
    assert (0.05 * 0.90) / (0.05 * 0.90 + 0.95 * 0.05) == pytest.approx(18 / 37)
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V10_TRUTH.items()],
        "evidence_refs": list(build_holdout_v10_harness().evidence_refs),
    }
    assert build_holdout_v10_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def test_iterated_context_protocol_transfers_promoted_pair_credit():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"implication-12": "PEER_SECOND"}
    provider_ledger = ProviderTelemetryLedger()
    primary_answers = dict(HOLDOUT_V11_TRUTH)
    primary_answers["implication-12"] = "D"
    adapters = {
        "small-a": FixtureAdapter("small-a", provider_ledger, HOLDOUT_V11_TRUTH, confidence=0.1),
        "small-b": FixtureAdapter("small-b", provider_ledger, primary_answers, confidence=0.99),
        "small-c": FixtureAdapter("small-c", provider_ledger, HOLDOUT_V11_TRUTH, confidence=0.1),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v11_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V11_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    policy = ContextAwareResolutionPolicy(
        operator_credit=operator_credit, operator_schedule=schedule,
        item_fingerprints=HOLDOUT_V11_ITEM_FINGERPRINTS,
        resolution_credit=resolution_credit, exploration_items=(),
        context_credit=context_credit, model_ids=tuple(profiles),
        information_value_weight=20.0, work_cost_weight=0.0,
    )
    report = IteratedContextResolutionProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles, reviewer_ledger=reviewer_ledger,
        fingerprint_credit_snapshot=fingerprint_snapshot,
        operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
        operator_schedule=schedule, acquisition_schedule=schedule,
        resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
        resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
        resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
        context_candidates=context_candidates, context_promotions=context_promotions,
        context_credit_snapshot=context_credit, policy=policy,
    ).run("iterated-context-fixture")

    assert report["iterated_context_resolution_arm"]["score"] == 1.0
    assert report["comparisons"]["context_peer_overrides"] == 1
    assert report["comparisons"]["resolution_corrections"] == 1
    assert report["protocol"]["v09_v10_v11_v12_context_outcomes_used_for_v13_route"] is True
    assert report["protocol"]["v13_outcomes_used_for_current_route"] is False


def test_holdout_v11_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V11_QUESTIONS}
    x = 2
    for n in (1, 2, 3):
        x = 3 * (x + n)
    rotated = "ABCDEF"[-2:] + "ABCDEF"[:-2]
    transformed = "".join(rotated[index + 1] + rotated[index] for index in range(0, 6, 2))

    assert x == 108 and questions["code-12"].choices[0] == "A: 108"
    assert transformed == "FEBADC" and questions["string-12"].choices[2] == "C: FEBADC"
    assert 180 - (110 + 90 - 55) == 35
    assert 960 / 16 * 6.25 == 375
    assert 1 - (8 / 12) * (7 / 11) == pytest.approx(19 / 33)
    assert (0.10 * 0.85) / (0.10 * 0.85 + 0.90 * 0.10) == pytest.approx(17 / 35)
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V11_TRUTH.items()],
        "evidence_refs": list(build_holdout_v11_harness().evidence_refs),
    }
    assert build_holdout_v11_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def test_case_adjudication_protocol_uses_isolated_arguments_and_corrects():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"implication-13": "PEER_SECOND"}
    provider_ledger = ProviderTelemetryLedger()
    primary_answers = dict(HOLDOUT_V12_TRUTH)
    primary_answers["implication-13"] = "A"
    adapters = {
        "small-a": CaseFixtureAdapter("small-a", provider_ledger, HOLDOUT_V12_TRUTH, confidence=0.1, judge_label="D"),
        "small-b": CaseFixtureAdapter("small-b", provider_ledger, primary_answers, confidence=0.99),
        "small-c": CaseFixtureAdapter("small-c", provider_ledger, HOLDOUT_V12_TRUTH, confidence=0.1),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v12_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V12_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    policy = CaseAdjudicationPolicy(
        operator_credit=operator_credit, operator_schedule=schedule,
        item_fingerprints=HOLDOUT_V12_ITEM_FINGERPRINTS,
        resolution_credit=resolution_credit, exploration_items=(),
        context_credit=context_credit, model_ids=tuple(profiles),
        information_value_weight=20.0, work_cost_weight=0.0,
    )
    report = CaseAdjudicationProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles, reviewer_ledger=reviewer_ledger,
        fingerprint_credit_snapshot=fingerprint_snapshot,
        operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
        operator_schedule=schedule, acquisition_schedule=schedule,
        resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
        resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
        resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
        context_candidates=context_candidates, context_promotions=context_promotions,
        context_credit_snapshot=context_credit, policy=policy,
    ).run("case-adjudication-fixture")

    assert report["case_adjudication_arm"]["score"] == 1.0
    assert report["case_adjudication_arm"]["rounds"] == 5
    assert report["comparisons"]["case_peer_overrides"] == 1
    assert report["comparisons"]["case_corrections"] == 1
    assert report["comparisons"]["case_harms"] == 0
    assert report["protocol"]["historical_pair_credit_has_decision_authority"] is False
    rendered = json.dumps(report["case_adjudication_outcome_receipt"], sort_keys=True)
    assert '"answer"' not in rendered and '"truth"' not in rendered
    advocate_tasks = [
        task for adapter in adapters.values() for task in adapter.observed_tasks
        if task.task_kind == "pilot_disagreement_argument"
    ]
    assert len(advocate_tasks) == 2
    assert all("candidate_records" not in task.inputs["round_context"] for task in advocate_tasks)
    judge_tasks = [
        task for adapter in adapters.values() for task in adapter.observed_tasks
        if task.task_kind == "pilot_disagreement_adjudication"
    ]
    assert len(judge_tasks) == 1 and len(judge_tasks[0].inputs["round_context"]["candidate_records"]) == 2


def test_case_adjudication_abstains_on_ambiguous_or_low_confidence_judgment():
    _, _, _, _, _, operator_credit, _ = _operator_credit_fixture()
    _, _, _, resolution_credit = _multi_cycle_resolution_fixture()
    _, _, _, context_credit = _context_resolution_fixture()
    policy = CaseAdjudicationPolicy(
        operator_credit=operator_credit, operator_schedule={"implication-13": "PEER_SECOND"},
        item_fingerprints=HOLDOUT_V12_ITEM_FINGERPRINTS,
        resolution_credit=resolution_credit, exploration_items=(),
        context_credit=context_credit, model_ids=("small-a", "small-b", "small-c"),
        information_value_weight=20.0, work_cost_weight=0.0,
    )
    primary = CalibratedCandidateSignal("small-b", "implication-13", "A", 0.9, 0.9, 10.0)
    peer = CalibratedCandidateSignal("small-c", "implication-13", "D", 0.1, 0.1, 10.0)
    witness = CalibratedCandidateSignal("small-a", "implication-13", "D", 0.1, 0.1, 10.0)
    decision = policy.route(
        primary,
        plans=(
            CalibratedModelPlan("small-b", 0.9, 10.0),
            CalibratedModelPlan("small-c", 0.1, 10.0),
            CalibratedModelPlan("small-a", 0.1, 10.0),
        ),
        domain="formal", reviewer_ledger=object(),
    )
    decision = policy.resolve_probe(
        replace(decision, action="VERIFY_PEER", reviewer_model_id="small-c"), primary, peer,
    )

    def bundle(adjudicability, confidence):
        return SimpleNamespace(
            item_id="implication-13", primary_model_id="small-b", peer_model_id="small-c",
            judge_model_id="small-a", primary_candidate_id="CANDIDATE_1",
            peer_candidate_id="CANDIDATE_2", argument_hashes=("a" * 64, "b" * 64),
            judgment_hash="c" * 64,
            judgment={"selected_candidate": "CANDIDATE_2", "adjudicability": adjudicability,
                      "confidence": confidence, "decisive_reason": "fixture"},
        )

    assert policy.resolve_case(decision, primary, peer, witness, bundle("ADJUDICABLE", 0.69)).final_answer == "A"
    assert policy.resolve_case(decision, primary, peer, witness, bundle("AMBIGUOUS", 0.95)).final_answer == "A"


def test_case_adjudication_provider_failure_keeps_primary_and_charges_work():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"implication-13": "PEER_SECOND"}
    provider_ledger = ProviderTelemetryLedger()
    primary_answers = dict(HOLDOUT_V12_TRUTH)
    primary_answers["implication-13"] = "A"
    adapters = {
        "small-a": CaseFixtureAdapter("small-a", provider_ledger, HOLDOUT_V12_TRUTH, confidence=0.1),
        "small-b": CaseFixtureAdapter(
            "small-b", provider_ledger, primary_answers, confidence=0.99,
            malformed_argument=True,
        ),
        "small-c": CaseFixtureAdapter("small-c", provider_ledger, HOLDOUT_V12_TRUTH, confidence=0.1),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v12_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V12_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    policy = CaseAdjudicationPolicy(
        operator_credit=operator_credit, operator_schedule=schedule,
        item_fingerprints=HOLDOUT_V12_ITEM_FINGERPRINTS,
        resolution_credit=resolution_credit, exploration_items=(),
        context_credit=context_credit, model_ids=tuple(profiles),
        information_value_weight=20.0, work_cost_weight=0.0,
    )
    report = CaseAdjudicationProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles, reviewer_ledger=reviewer_ledger,
        fingerprint_credit_snapshot=fingerprint_snapshot,
        operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
        operator_schedule=schedule, acquisition_schedule=schedule,
        resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
        resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
        resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
        context_candidates=context_candidates, context_promotions=context_promotions,
        context_credit_snapshot=context_credit, policy=policy,
    ).run("case-adjudication-provider-failure-fixture")

    decision = next(item for item in report["route_decisions"] if item["item_id"] == "implication-13")
    assert decision["final_answer"] == "A"
    assert decision["resolution_policy"] == "CASE_PROVIDER_FAILED_KEEP"
    assert decision["case_adjudicability"] == "PROVIDER_FAILED"
    assert report["comparisons"]["case_adjudication_provider_failures"] == 1
    assert report["comparisons"]["case_primary_keeps"] == 1
    assert report["case_adjudication_failures"][0]["provider_calls"] >= 1
    assert report["case_adjudication_arm"]["provider_calls"] > report["best_small_model"]["provider_calls"]


def test_structured_schema_rejects_shallow_empty_case_evidence():
    schema = {
        "required": ["argument", "steps", "confidence"],
        "properties": {
            "argument": {"type": "string", "minLength": 1},
            "steps": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
    }

    failures = schema_failures(schema, {"argument": "", "steps": [], "confidence": 1.2})

    assert set(failures) == {"minLength:argument", "minItems:steps", "maximum:confidence"}


def test_holdout_v12_reference_answers_match_mechanical_calculations():
    questions = {item.item_id: item for item in HOLDOUT_V12_QUESTIONS}
    x = 2
    for n in (1, 2, 3):
        x = 2 * x + n
    swapped = "ABCDEF"[3:] + "ABCDEF"[:3]
    transformed = "".join(swapped[index + 1] + swapped[index] for index in range(0, 6, 2))

    assert x == 27 and questions["code-13"].choices[3] == "D: 27"
    assert transformed == "EDAFCB" and questions["string-13"].choices[0] == "A: EDAFCB"
    assert 200 - (120 + 105 - 65) == 40
    assert 1080 / 18 * 7.25 == 435
    assert 1 - (9 / 12) * (8 / 11) == pytest.approx(5 / 11)
    assert (0.08 * 0.90) / (0.08 * 0.90 + 0.92 * 0.08) == pytest.approx(45 / 91)
    candidate = {
        "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in HOLDOUT_V12_TRUTH.items()],
        "evidence_refs": list(build_holdout_v12_harness().evidence_refs),
    }
    assert build_holdout_v12_harness().candidate_union_ceiling((candidate,))["score"] == 1.0


def test_holdout_v13_argument_replay_verifies_truth_derivations_without_truth_access():
    harness = build_holdout_v13_harness()
    verifier = MechanicalArgumentVerifier(harness)
    derivations = {
        "arithmetic-14": ("C", "18*7-35", "91"),
        "rate-14": ("B", "1260/21*6.5", "390"),
        "percent-14": ("C", "15/100*860", "129"),
        "sets-14": ("C", "240-(150+125-80)", "45"),
        "probability-14": ("C", "1-(8/(8+4))*((8-1)/(8+4-1))", "19/33"),
        "bayes-14": ("B", "(10/100*85/100)/((10/100*85/100)+(1-10/100)*(1-90/100))", "17/35"),
        "modular-14": ("C", "347%13", "9"),
        "ratio-14": ("B", "360*5/(5+7)", "150"),
        "average-14": ("C", "(14+18+23+25+30)/5", "22"),
        "code-14": ("D", "2*(2*(2*3+2)+4)+6", "46"),
        "unit-14": ("B", "72*2.75", "198"),
    }

    def argument(item_id, expression, result):
        return {
            "item_id": item_id, "candidate_id": "CANDIDATE_1", "argument": "fixture",
            "derived_facts": [{"fact_id": "f1", "expression": expression,
                               "claimed_result": result}],
            "conclusion_value": result, "uncertainty": "low",
            "evidence_refs": list(harness.evidence_refs),
        }

    receipts = [
        verifier.verify(item_id=item_id, candidate_id="CANDIDATE_1", candidate_label=label,
                        argument=argument(item_id, expression, result))
        for item_id, (label, expression, result) in derivations.items()
    ]
    string_argument = {
        "item_id": "string-14", "candidate_id": "CANDIDATE_1", "argument": "fixture",
        "derived_facts": [
            {"fact_id": "f1", "expression": "SWAP_HALVES(ABCDEFGH)",
             "claimed_result": "EFGHABCD"},
            {"fact_id": "f2", "expression": "REVERSE_PAIRS(EFGHABCD)",
             "claimed_result": "FEHGBADC"},
        ],
        "conclusion_value": "FEHGBADC", "uncertainty": "low",
        "evidence_refs": list(harness.evidence_refs),
    }
    receipts.append(verifier.verify(
        item_id="string-14", candidate_id="CANDIDATE_1", candidate_label="A",
        argument=string_argument,
    ))

    assert len(receipts) == len(HOLDOUT_V13_QUESTIONS)
    assert all(item.status == "VERIFIED" and not item.hidden_truth_used for item in receipts)
    rendered = json.dumps([item.as_dict() for item in receipts], sort_keys=True)
    assert "expected_answer" not in rendered and "ground_truth" not in rendered
    bad = verifier.verify(
        item_id="arithmetic-14", candidate_id="CANDIDATE_2", candidate_label="A",
        argument=argument("arithmetic-14", "87+0", "87") | {"candidate_id": "CANDIDATE_2"},
    )
    assert bad.status == "FAILED" and bad.failed_fact_ids == ("f1",)


def test_verified_case_protocol_requires_replay_and_provider_judgment_for_override():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"arithmetic-14": "PEER_SECOND"}
    provider_ledger = ProviderTelemetryLedger()
    primary_answers = dict(HOLDOUT_V13_TRUTH)
    primary_answers["arithmetic-14"] = "A"
    arguments = {
        "A": ("87+0", "87"), "B": ("89+0", "89"),
        "C": ("18*7-35", "91"), "D": ("93+0", "93"),
    }
    adapters = {
        "small-a": CaseFixtureAdapter(
            "small-a", provider_ledger, HOLDOUT_V13_TRUTH, confidence=0.1,
            judge_label="C", verified_argument_by_label=arguments,
        ),
        "small-b": CaseFixtureAdapter(
            "small-b", provider_ledger, primary_answers, confidence=0.99,
            verified_argument_by_label=arguments,
        ),
        "small-c": CaseFixtureAdapter(
            "small-c", provider_ledger, HOLDOUT_V13_TRUTH, confidence=0.1,
            verified_argument_by_label=arguments,
        ),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v13_harness(), small_adapters=adapters,
        baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V13_TRUTH),
        telemetry_ledger=provider_ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    policy = VerifiedCaseAdjudicationPolicy(
        operator_credit=operator_credit, operator_schedule=schedule,
        item_fingerprints=HOLDOUT_V13_ROUTING_FINGERPRINTS,
        resolution_credit=resolution_credit, exploration_items=(),
        context_credit=context_credit, model_ids=tuple(profiles),
        information_value_weight=20.0, work_cost_weight=0.0,
    )
    report = VerifiedCaseAdjudicationProtocol(
        base=base, calibration_receipt=receipt, profiles=profiles, reviewer_ledger=reviewer_ledger,
        fingerprint_credit_snapshot=fingerprint_snapshot,
        operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
        operator_schedule=schedule, acquisition_schedule=schedule,
        resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
        resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
        resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
        context_candidates=context_candidates, context_promotions=context_promotions,
        context_credit_snapshot=context_credit, policy=policy,
    ).run("verified-case-fixture")

    decision = next(item for item in report["route_decisions"] if item["item_id"] == "arithmetic-14")
    assert decision["final_answer"] == "C"
    assert decision["resolution_policy"] == "VERIFIED_CASE_PEER_OVERRIDE"
    assert report["comparisons"]["case_corrections"] == 1
    assert report["comparisons"]["case_harms"] == 0
    assert report["comparisons"]["verified_arguments"] == 1
    assert report["comparisons"]["failed_argument_replays"] == 1
    assert report["protocol"]["argument_fact_replay_hidden_truth_access"] is False


def test_holdout_v14_single_expression_replay_derives_results_and_nested_string():
    harness = build_holdout_v14_harness()
    verifier = SingleExpressionVerifier(harness)
    cases = {
        "arithmetic-15": ("C", "24*6-47"), "rate-15": ("B", "1470/21*5.5"),
        "percent-15": ("C", "18/100*750"), "sets-15": ("B", "260-(155+130-75)"),
        "probability-15": ("C", "1-(7/(7+5))*((7-1)/(7+5-1))"),
        "bayes-15": ("B", "(12/100*80/100)/((12/100*80/100)+(1-12/100)*(1-90/100))"),
        "modular-15": ("B", "529%17"), "ratio-15": ("B", "420*3/(3+4)"),
        "average-15": ("B", "(16+19+21+24+30)/5"),
        "code-15": ("C", "2*(2*(2*4+1)+3)+5"),
        "string-15": ("A", "REVERSE_PAIRS(SWAP_HALVES(IJKLMNOP))"),
        "unit-15": ("B", "84*2.25"),
    }
    receipts = [
        verifier.verify(item_id=item_id, candidate_id="CANDIDATE_1",
                        candidate_label=label, expression=expression)
        for item_id, (label, expression) in cases.items()
    ]

    assert len(receipts) == len(HOLDOUT_V14_QUESTIONS)
    assert all(item.status == "VERIFIED" and item.derived_result for item in receipts)
    bad = verifier.verify(
        item_id="arithmetic-15", candidate_id="CANDIDATE_2",
        candidate_label="A", expression="95+0",
    )
    assert bad.status == "FAILED" and bad.hidden_truth_used is False


def test_single_expression_protocol_gates_work_on_aggregate_correction_opportunity():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"arithmetic-15": "PEER_SECOND"}
    expressions = {"A": "95+0", "B": "96+0", "C": "24*6-47", "D": "98+0"}

    def run(peer_correct):
        provider_ledger = ProviderTelemetryLedger()
        primary_answers = dict(HOLDOUT_V14_TRUTH)
        primary_answers["arithmetic-15"] = "A"
        peer_answers = dict(HOLDOUT_V14_TRUTH)
        peer_answers["arithmetic-15"] = "C" if peer_correct else "B"
        adapters = {
            "small-a": CaseFixtureAdapter(
                "small-a", provider_ledger, HOLDOUT_V14_TRUTH, confidence=0.1,
                judge_label="C", single_expression_by_label=expressions,
            ),
            "small-b": CaseFixtureAdapter(
                "small-b", provider_ledger, primary_answers, confidence=0.99,
                single_expression_by_label=expressions,
            ),
            "small-c": CaseFixtureAdapter(
                "small-c", provider_ledger, peer_answers, confidence=0.1,
                single_expression_by_label=expressions,
            ),
        }
        base = LocalCollectiveCognitionProtocol(
            harness=build_holdout_v14_harness(), small_adapters=adapters,
            baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V14_TRUTH),
            telemetry_ledger=provider_ledger, reviewer_model_id="small-b",
            synthesizer_model_id="small-c",
        )
        policy = VerifiedCaseAdjudicationPolicy(
            operator_credit=operator_credit, operator_schedule=schedule,
            item_fingerprints=HOLDOUT_V14_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit, exploration_items=(),
            context_credit=context_credit, model_ids=tuple(profiles),
            information_value_weight=20.0, work_cost_weight=0.0,
        )
        report = SingleExpressionAdjudicationProtocol(
            base=base, calibration_receipt=receipt, profiles=profiles,
            reviewer_ledger=reviewer_ledger, fingerprint_credit_snapshot=fingerprint_snapshot,
            operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
            operator_schedule=schedule, acquisition_schedule=schedule,
            resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
            resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
            resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
            context_candidates=context_candidates, context_promotions=context_promotions,
            context_credit_snapshot=context_credit, policy=policy,
        ).run("single-expression-fixture-" + str(peer_correct))
        return report, adapters

    passed, _ = run(True)
    blocked, blocked_adapters = run(False)
    assert passed["pre_route_audit"]["gate_passed"] is True
    assert passed["comparisons"]["case_corrections"] == 1
    assert passed["comparisons"]["verified_arguments"] == 1
    assert "item_id" not in passed["pre_route_audit"]
    assert blocked["pre_route_audit"]["gate_passed"] is False
    assert blocked["comparisons"]["opportunity_gate_keeps"] == 1
    assert blocked["comparisons"]["single_expression_improvement_status"].startswith("NOT_ESTIMABLE")
    assert not [
        task for adapter in blocked_adapters.values() for task in adapter.observed_tasks
        if task.task_kind in {"pilot_disagreement_argument", "pilot_disagreement_adjudication"}
    ]


def test_holdout_v15_candidate_revision_replay_binds_proposed_options():
    verifier = CandidateRevisionVerifier(build_holdout_v15_harness())
    cases = {
        "arithmetic-16": ("C", "37*4-59"), "rate-16": ("C", "1848/28*6.5"),
        "percent-16": ("C", "22/100*650"), "sets-16": ("B", "310-(190+165-95)"),
        "probability-16": ("C", "1-(8/(8+4))*((8-1)/(8+4-1))"),
        "bayes-16": ("C", "(15/100*90/100)/((15/100*90/100)+(1-15/100)*(1-85/100))"),
        "modular-16": ("A", "647%19"), "ratio-16": ("B", "528*5/(5+6)"),
        "average-16": ("C", "(14+18+23+27+33)/5"),
        "code-16": ("C", "2*(2*(2*5+2)+4)+6"),
        "string-16": ("A", "REVERSE_PAIRS(SWAP_HALVES(ABCDEFGH))"),
        "unit-16": ("B", "96*1.75"),
    }
    receipts = [
        verifier.verify(item_id=item_id, candidate_id="CANDIDATE_1", candidate_label="D",
                        expression=expression, proposed_candidate=label)
        for item_id, (label, expression) in cases.items()
    ]
    invalid = verifier.verify(
        item_id="arithmetic-16", candidate_id="CANDIDATE_2", candidate_label="A",
        expression="37*4-59", proposed_candidate="B",
    )
    retracted = verifier.verify(
        item_id="arithmetic-16", candidate_id="CANDIDATE_2", candidate_label="A",
        proposed_candidate="ABSTAIN",
    )

    assert len(receipts) == len(HOLDOUT_V15_QUESTIONS)
    assert all(item.status == "VERIFIED" and item.disposition == "REVISE" for item in receipts)
    assert invalid.status == "FAILED" and invalid.disposition == "INVALID"
    assert retracted.status == "RETRACTED" and retracted.hidden_truth_used is False


def test_candidate_revision_protocol_corrects_self_belief_and_gates_no_error_work():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"arithmetic-16": "PEER_SECOND"}

    def run(primary_wrong):
        provider_ledger = ProviderTelemetryLedger()
        primary_answers = dict(HOLDOUT_V15_TRUTH)
        primary_answers["arithmetic-16"] = "A" if primary_wrong else "C"
        peer_answers = dict(HOLDOUT_V15_TRUTH)
        peer_answers["arithmetic-16"] = "B"
        revisions = {
            "A": ("37*4-59", "C"), "B": ("88+0", "B"),
            "C": ("37*4-59", "C"), "D": ("90+0", "D"),
        }
        adapters = {
            "small-a": CaseFixtureAdapter(
                "small-a", provider_ledger, HOLDOUT_V15_TRUTH, confidence=0.1,
                judge_label="C", candidate_revision_by_label=revisions,
            ),
            "small-b": CaseFixtureAdapter(
                "small-b", provider_ledger, primary_answers, confidence=0.99,
                candidate_revision_by_label=revisions,
            ),
            "small-c": CaseFixtureAdapter(
                "small-c", provider_ledger, peer_answers, confidence=0.1,
                candidate_revision_by_label=revisions,
            ),
        }
        base = LocalCollectiveCognitionProtocol(
            harness=build_holdout_v15_harness(), small_adapters=adapters,
            baseline_adapter=FixtureAdapter("deepseek-32b", provider_ledger, HOLDOUT_V15_TRUTH),
            telemetry_ledger=provider_ledger, reviewer_model_id="small-b",
            synthesizer_model_id="small-c",
        )
        policy = CandidateRevisionPolicy(
            operator_credit=operator_credit, operator_schedule=schedule,
            item_fingerprints=HOLDOUT_V15_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit, exploration_items=(),
            context_credit=context_credit, model_ids=tuple(profiles),
            information_value_weight=20.0, work_cost_weight=0.0,
        )
        report = CandidateRevisionProtocol(
            base=base, calibration_receipt=receipt, profiles=profiles,
            reviewer_ledger=reviewer_ledger, fingerprint_credit_snapshot=fingerprint_snapshot,
            operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
            operator_schedule=schedule, acquisition_schedule=schedule,
            resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
            resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
            resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
            context_candidates=context_candidates, context_promotions=context_promotions,
            context_credit_snapshot=context_credit, policy=policy,
        ).run("candidate-revision-fixture-" + str(primary_wrong))
        return report, adapters

    passed, _ = run(True)
    blocked, blocked_adapters = run(False)
    decision = next(item for item in passed["route_decisions"] if item["item_id"] == "arithmetic-16")
    assert passed["pre_route_audit"]["gate_basis"] == "PRIMARY_ERROR_OPPORTUNITY"
    assert decision["final_answer"] == "C"
    assert decision["resolution_policy"] == "PROVIDER_BACKED_CANDIDATE_REVISION"
    assert passed["comparisons"]["case_corrections"] == 1
    assert passed["comparisons"]["candidate_revision_adoptions"] == 1
    assert blocked["pre_route_audit"]["gate_passed"] is False
    assert blocked["comparisons"]["revision_opportunity_gate_keeps"] == 1
    assert not [
        task for adapter in blocked_adapters.values() for task in adapter.observed_tasks
        if task.task_kind in {"pilot_disagreement_argument", "pilot_disagreement_adjudication"}
    ]


def _typed_steps(*values):
    return [
        {"step_id": f"STEP_{index}", "operator": operator, "inputs": list(inputs)}
        for index, (operator, inputs) in enumerate(values, 1)
    ]


def test_holdout_v16_typed_derivations_execute_all_reference_families():
    harness = build_holdout_v16_harness()
    verifier = TypedDerivationVerifier(harness)
    plans = {
        "arithmetic-17": ("C", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("STEP_1", "VALUE_3")))),
        "rate-17": ("B", _typed_steps(("DIVIDE", ("VALUE_1", "VALUE_2")), ("MULTIPLY", ("STEP_1", "VALUE_3")))),
        "percent-17": ("B", _typed_steps(("DIVIDE", ("VALUE_1", "CONST_100")), ("MULTIPLY", ("STEP_1", "VALUE_2")))),
        "sets-17": ("C", _typed_steps(("ADD", ("VALUE_2", "VALUE_3")), ("SUBTRACT", ("STEP_1", "VALUE_4")), ("SUBTRACT", ("VALUE_1", "STEP_2")))),
        "probability-17": ("B", _typed_steps(("ADD", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("VALUE_1", "STEP_1")), ("SUBTRACT", ("VALUE_1", "CONST_1")), ("SUBTRACT", ("STEP_1", "CONST_1")), ("DIVIDE", ("STEP_3", "STEP_4")), ("MULTIPLY", ("STEP_2", "STEP_5")), ("SUBTRACT", ("CONST_1", "STEP_6")))),
        "bayes-17": ("B", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("CONST_100", "VALUE_1")), ("SUBTRACT", ("CONST_100", "VALUE_3")), ("MULTIPLY", ("STEP_2", "STEP_3")), ("ADD", ("STEP_1", "STEP_4")), ("DIVIDE", ("STEP_1", "STEP_5")))),
        "modular-17": ("C", _typed_steps(("MODULO", ("VALUE_1", "VALUE_2")))),
        "ratio-17": ("B", _typed_steps(("ADD", ("VALUE_2", "VALUE_3")), ("MULTIPLY", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("STEP_2", "STEP_1")))),
        "average-17": ("C", _typed_steps(("ADD", ("VALUE_1", "VALUE_2")), ("ADD", ("STEP_1", "VALUE_3")), ("ADD", ("STEP_2", "VALUE_4")), ("ADD", ("STEP_3", "VALUE_5")), ("DIVIDE", ("STEP_4", "VALUE_6")))),
        "code-17": ("C", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_5")), ("ADD", ("STEP_1", "VALUE_2")), ("MULTIPLY", ("STEP_2", "VALUE_5")), ("ADD", ("STEP_3", "VALUE_3")), ("MULTIPLY", ("STEP_4", "VALUE_5")), ("ADD", ("STEP_5", "VALUE_4")))),
        "string-17": ("A", _typed_steps(("SWAP_HALVES", ("VALUE_1",)), ("REVERSE_PAIRS", ("STEP_1",)))),
        "unit-17": ("C", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")))),
    }
    receipts = []
    for item_id, (label, steps) in plans.items():
        argument = {"item_id": item_id, "candidate_id": "CANDIDATE_1",
                    "proposed_candidate": label, "steps": steps,
                    "result_step": steps[-1]["step_id"],
                    "evidence_refs": list(harness.evidence_refs)}
        validate_typed_derivation(
            argument, item_id=item_id, candidate_id="CANDIDATE_1",
            evidence_refs=list(harness.evidence_refs),
            scaffold=harness.derivation_scaffold(item_id),
        )
        receipts.append(verifier.verify(
            item_id=item_id, candidate_id="CANDIDATE_1", candidate_label="D", argument=argument,
        ))

    assert len(receipts) == len(HOLDOUT_V16_QUESTIONS)
    assert all(item.status == "VERIFIED" and item.disposition == "REVISE" for item in receipts)
    assert "145" not in harness.derivation_scaffold("arithmetic-17").values()


def test_typed_derivation_protocol_adopts_verified_self_revision_and_blocks_no_error_cycle():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"arithmetic-17": "PEER_SECOND"}
    correct = _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")),
                           ("SUBTRACT", ("STEP_1", "VALUE_3")))
    option_b = [*correct, {"step_id": "STEP_3", "operator": "SUBTRACT",
                           "inputs": ["STEP_2", "CONST_1"]}]
    plans = {"A": (correct, "C"), "B": (option_b, "B"), "C": (correct, "C"),
             "D": ([], "ABSTAIN")}

    def run(primary_wrong):
        ledger = ProviderTelemetryLedger()
        primary = dict(HOLDOUT_V16_TRUTH)
        primary["arithmetic-17"] = "A" if primary_wrong else "C"
        peer = dict(HOLDOUT_V16_TRUTH)
        peer["arithmetic-17"] = "B"
        adapters = {
            "small-a": CaseFixtureAdapter("small-a", ledger, HOLDOUT_V16_TRUTH, confidence=0.1,
                                           judge_label="C", typed_derivation_by_label=plans),
            "small-b": CaseFixtureAdapter("small-b", ledger, primary, confidence=0.99,
                                           typed_derivation_by_label=plans),
            "small-c": CaseFixtureAdapter("small-c", ledger, peer, confidence=0.1,
                                           typed_derivation_by_label=plans),
        }
        base = LocalCollectiveCognitionProtocol(
            harness=build_holdout_v16_harness(), small_adapters=adapters,
            baseline_adapter=FixtureAdapter("deepseek-32b", ledger, HOLDOUT_V16_TRUTH),
            telemetry_ledger=ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
        )
        policy = CandidateRevisionPolicy(
            operator_credit=operator_credit, operator_schedule=schedule,
            item_fingerprints=HOLDOUT_V16_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit, exploration_items=(),
            context_credit=context_credit, model_ids=tuple(profiles),
            information_value_weight=20.0, work_cost_weight=0.0,
        )
        report = TypedDerivationProtocol(
            base=base, calibration_receipt=receipt, profiles=profiles,
            reviewer_ledger=reviewer_ledger, fingerprint_credit_snapshot=fingerprint_snapshot,
            operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
            operator_schedule=schedule, acquisition_schedule=schedule,
            resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
            resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
            resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
            context_candidates=context_candidates, context_promotions=context_promotions,
            context_credit_snapshot=context_credit, policy=policy,
        ).run("typed-derivation-fixture-" + str(primary_wrong))
        return report, adapters

    passed, _ = run(True)
    blocked, blocked_adapters = run(False)
    decision = next(item for item in passed["route_decisions"] if item["item_id"] == "arithmetic-17")
    assert decision["final_answer"] == "C"
    assert decision["resolution_policy"] == "PROVIDER_BACKED_CANDIDATE_REVISION"
    assert passed["comparisons"]["typed_derivation_verified"] == 2
    assert passed["comparisons"]["case_corrections"] == 1
    assert blocked["pre_route_audit"]["gate_passed"] is False
    assert not [task for adapter in blocked_adapters.values() for task in adapter.observed_tasks
                if task.task_kind in {"pilot_disagreement_argument", "pilot_disagreement_adjudication"}]


def test_holdout_v19_constrained_algebra_replays_all_reference_families():
    harness = build_holdout_v19_harness()
    plans = {
        "arithmetic-20": ("B", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("STEP_1", "VALUE_3")))),
        "rate-20": ("B", _typed_steps(("DIVIDE", ("VALUE_1", "VALUE_2")), ("MULTIPLY", ("STEP_1", "VALUE_3")))),
        "percent-20": ("C", _typed_steps(("DIVIDE", ("VALUE_1", "CONST_100")), ("MULTIPLY", ("STEP_1", "VALUE_2")))),
        "sets-20": ("C", _typed_steps(("ADD", ("VALUE_2", "VALUE_3")), ("SUBTRACT", ("STEP_1", "VALUE_4")), ("SUBTRACT", ("VALUE_1", "STEP_2")))),
        "probability-20": ("B", _typed_steps(("ADD", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("VALUE_1", "STEP_1")), ("SUBTRACT", ("VALUE_1", "CONST_1")), ("SUBTRACT", ("STEP_1", "CONST_1")), ("DIVIDE", ("STEP_3", "STEP_4")), ("MULTIPLY", ("STEP_2", "STEP_5")), ("SUBTRACT", ("CONST_1", "STEP_6")))),
        "bayes-20": ("C", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("CONST_100", "VALUE_1")), ("SUBTRACT", ("CONST_100", "VALUE_3")), ("MULTIPLY", ("STEP_2", "STEP_3")), ("ADD", ("STEP_1", "STEP_4")), ("DIVIDE", ("STEP_1", "STEP_5")))),
        "modular-20": ("B", _typed_steps(("MODULO", ("VALUE_1", "VALUE_2")))),
        "ratio-20": ("B", _typed_steps(("ADD", ("VALUE_2", "VALUE_3")), ("MULTIPLY", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("STEP_2", "STEP_1")))),
        "average-20": ("C", _typed_steps(("ADD", ("VALUE_1", "VALUE_2")), ("ADD", ("STEP_1", "VALUE_3")), ("ADD", ("STEP_2", "VALUE_4")), ("ADD", ("STEP_3", "VALUE_5")), ("DIVIDE", ("STEP_4", "VALUE_6")))),
        "code-20": ("C", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_5")), ("ADD", ("STEP_1", "VALUE_2")), ("MULTIPLY", ("STEP_2", "VALUE_5")), ("ADD", ("STEP_3", "VALUE_3")), ("MULTIPLY", ("STEP_4", "VALUE_5")), ("ADD", ("STEP_5", "VALUE_4")))),
        "string-20": ("A", _typed_steps(("SWAP_HALVES", ("VALUE_1",)), ("REVERSE_PAIRS", ("STEP_1",)))),
        "unit-20": ("C", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")))),
    }
    receipts = []
    for item_id, (label, plan) in plans.items():
        symbols, steps = dict(harness.derivation_scaffold(item_id)), []
        for spec in plan:
            action = {"action": "APPLY", "operator": spec["operator"],
                      "inputs": spec["inputs"], "proposed_candidate": "PENDING",
                      "evidence_refs": list(harness.evidence_refs)}
            step = harness.execute_derivation_step(
                item_id=item_id, candidate_id="CANDIDATE_1", step_id=spec["step_id"],
                action=action, symbol_values=symbols,
            )
            steps.append(step)
            symbols[step.step_id] = step.result
        receipts.append(harness.finalize_derivation_session(
            item_id=item_id, candidate_id="CANDIDATE_1", original_candidate="D",
            action={"action": "FINALIZE", "operator": "NONE", "inputs": [steps[-1].step_id],
                    "proposed_candidate": label, "evidence_refs": list(harness.evidence_refs)},
            step_receipts=tuple(steps), provider_turns=len(steps) + 1, invalid_actions=0,
        ))

    assert len(receipts) == len(HOLDOUT_V19_QUESTIONS)
    assert all(item.status == "VERIFIED" and item.disposition == "REVISE" for item in receipts)
    assert "173" not in harness.derivation_scaffold("arithmetic-20").values()


def test_constrained_tool_protocol_completes_and_adopts_verified_revision():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"arithmetic-20": "PEER_SECOND"}
    multiply = {"action": "APPLY", "operator": "MULTIPLY",
                "inputs": ["VALUE_1", "VALUE_2"], "proposed_candidate": "PENDING"}
    subtract = {"action": "APPLY", "operator": "SUBTRACT",
                "inputs": ["STEP_1", "VALUE_3"], "proposed_candidate": "PENDING"}
    finalize = {"action": "FINALIZE", "operator": "NONE", "inputs": ["STEP_2"],
                "proposed_candidate": "B"}
    abstain = {"action": "ABSTAIN", "operator": "NONE", "inputs": [],
               "proposed_candidate": "ABSTAIN"}
    actions = {"A": [multiply, subtract, finalize],
               "B": [abstain], "C": [abstain], "D": [abstain]}

    def run(primary_wrong, judge_fail=False):
        ledger = ProviderTelemetryLedger()
        primary = dict(HOLDOUT_V19_TRUTH)
        primary["arithmetic-20"] = "A" if primary_wrong else "B"
        peer = dict(HOLDOUT_V19_TRUTH)
        peer["arithmetic-20"] = "D"
        adapters = {
            "small-a": CaseFixtureAdapter("small-a", ledger, HOLDOUT_V19_TRUTH, confidence=0.1,
                                           judge_label="B", malformed_judgment=judge_fail,
                                           constrained_actions_by_label=actions),
            "small-b": CaseFixtureAdapter("small-b", ledger, primary, confidence=0.99,
                                           constrained_actions_by_label=actions),
            "small-c": CaseFixtureAdapter("small-c", ledger, peer, confidence=0.1,
                                           constrained_actions_by_label=actions),
        }
        base = LocalCollectiveCognitionProtocol(
            harness=build_holdout_v19_harness(), small_adapters=adapters,
            baseline_adapter=FixtureAdapter("deepseek-32b", ledger, HOLDOUT_V19_TRUTH),
            telemetry_ledger=ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
        )
        policy = CandidateRevisionPolicy(
            operator_credit=operator_credit, operator_schedule=schedule,
            item_fingerprints=HOLDOUT_V19_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit, exploration_items=(),
            context_credit=context_credit, model_ids=tuple(profiles),
            information_value_weight=20.0, work_cost_weight=0.0,
        )
        report = ConstrainedToolProtocol(
            base=base, calibration_receipt=receipt, profiles=profiles,
            reviewer_ledger=reviewer_ledger, fingerprint_credit_snapshot=fingerprint_snapshot,
            operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
            operator_schedule=schedule, acquisition_schedule=schedule,
            resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
            resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
            resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
            context_candidates=context_candidates, context_promotions=context_promotions,
            context_credit_snapshot=context_credit, policy=policy,
        ).run("constrained-tool-fixture-" + str(primary_wrong))
        return report, adapters

    passed, _ = run(True)
    blocked, blocked_adapters = run(False)
    judge_failed, _ = run(True, judge_fail=True)
    decision = next(item for item in passed["route_decisions"] if item["item_id"] == "arithmetic-20")
    assert decision["final_answer"] == "B"
    assert decision["resolution_policy"] == "PROVIDER_BACKED_CANDIDATE_REVISION"
    assert passed["comparisons"]["constrained_tool_receipts"] == 2
    assert passed["comparisons"]["constrained_tool_verified"] == 1
    assert passed["comparisons"]["constrained_tool_turns"] == 4
    assert passed["comparisons"]["constrained_applied_steps"] == 2
    assert passed["comparisons"]["constrained_invalid_actions"] == 0
    assert passed["comparisons"]["constrained_registry_options"] > 0
    assert passed["comparisons"]["case_corrections"] == 1
    assert judge_failed["comparisons"]["case_adjudication_provider_failures"] == 1
    assert judge_failed["comparisons"]["constrained_tool_failure_path_receipts"] == 2
    assert judge_failed["comparisons"]["constrained_tool_receipts"] == 2
    assert judge_failed["comparisons"]["constrained_tool_channel_completion_rate"] == 1.0
    assert blocked["pre_route_audit"]["gate_passed"] is False
    assert not [task for adapter in blocked_adapters.values() for task in adapter.observed_tasks
                if task.task_kind in {"pilot_constrained_tool_action", "pilot_disagreement_adjudication"}]


def test_iterative_harness_executes_steps_and_finalizes_without_choice_scaffold_leak():
    harness = build_holdout_v17_harness()
    symbols = harness.derivation_scaffold("arithmetic-18")
    first_action = {"item_id": "arithmetic-18", "candidate_id": "CANDIDATE_1",
                    "action": "APPLY", "operator": "MULTIPLY",
                    "inputs": ["VALUE_1", "VALUE_2"], "proposed_candidate": "PENDING",
                    "evidence_refs": list(harness.evidence_refs)}
    first = harness.execute_derivation_step(
        item_id="arithmetic-18", candidate_id="CANDIDATE_1", step_id="STEP_1",
        action=first_action, symbol_values=symbols,
    )
    symbols[first.step_id] = first.result
    second_action = {**first_action, "operator": "SUBTRACT", "inputs": ["STEP_1", "VALUE_3"]}
    second = harness.execute_derivation_step(
        item_id="arithmetic-18", candidate_id="CANDIDATE_1", step_id="STEP_2",
        action=second_action, symbol_values=symbols,
    )
    final = harness.finalize_derivation_session(
        item_id="arithmetic-18", candidate_id="CANDIDATE_1", original_candidate="A",
        action={**first_action, "action": "FINALIZE", "operator": "NONE",
                "inputs": ["STEP_2"], "proposed_candidate": "B"},
        step_receipts=(first, second), provider_turns=3, invalid_actions=0,
    )

    assert first.result == "156" and second.result == "109"
    assert final.status == "VERIFIED" and final.disposition == "REVISE"
    assert "99" not in harness.derivation_scaffold("arithmetic-18").values()


def test_iterative_protocol_uses_error_feedback_then_adopts_self_revision():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"arithmetic-18": "PEER_SECOND"}
    apply_invalid = {"action": "APPLY", "operator": "ADD", "inputs": ["VALUE_1"],
                     "proposed_candidate": "PENDING"}
    apply_multiply = {"action": "APPLY", "operator": "MULTIPLY",
                      "inputs": ["VALUE_1", "VALUE_2"], "proposed_candidate": "PENDING"}
    apply_subtract = {"action": "APPLY", "operator": "SUBTRACT",
                      "inputs": ["STEP_1", "VALUE_3"], "proposed_candidate": "PENDING"}
    finalize = {"action": "FINALIZE", "operator": "NONE", "inputs": ["STEP_2"],
                "proposed_candidate": "B"}
    abstain = {"action": "ABSTAIN", "operator": "NONE", "inputs": [],
               "proposed_candidate": "ABSTAIN"}
    actions = {"A": [apply_invalid, apply_multiply, apply_subtract, finalize],
               "B": [finalize], "C": [abstain], "D": [abstain]}

    def run(primary_wrong, action_plan=actions):
        ledger = ProviderTelemetryLedger()
        primary = dict(HOLDOUT_V17_TRUTH)
        primary["arithmetic-18"] = "A" if primary_wrong else "B"
        peer = dict(HOLDOUT_V17_TRUTH)
        peer["arithmetic-18"] = "D"
        adapters = {
            "small-a": CaseFixtureAdapter("small-a", ledger, HOLDOUT_V17_TRUTH, confidence=0.1,
                                           judge_label="B", iterative_actions_by_label=action_plan),
            "small-b": CaseFixtureAdapter("small-b", ledger, primary, confidence=0.99,
                                           iterative_actions_by_label=action_plan),
            "small-c": CaseFixtureAdapter("small-c", ledger, peer, confidence=0.1,
                                           iterative_actions_by_label=action_plan),
        }
        base = LocalCollectiveCognitionProtocol(
            harness=build_holdout_v17_harness(), small_adapters=adapters,
            baseline_adapter=FixtureAdapter("deepseek-32b", ledger, HOLDOUT_V17_TRUTH),
            telemetry_ledger=ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
        )
        policy = CandidateRevisionPolicy(
            operator_credit=operator_credit, operator_schedule=schedule,
            item_fingerprints=HOLDOUT_V17_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit, exploration_items=(),
            context_credit=context_credit, model_ids=tuple(profiles),
            information_value_weight=20.0, work_cost_weight=0.0,
        )
        report = IterativeDerivationProtocol(
            base=base, calibration_receipt=receipt, profiles=profiles,
            reviewer_ledger=reviewer_ledger, fingerprint_credit_snapshot=fingerprint_snapshot,
            operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
            operator_schedule=schedule, acquisition_schedule=schedule,
            resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
            resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
            resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
            context_candidates=context_candidates, context_promotions=context_promotions,
            context_credit_snapshot=context_credit, policy=policy,
        ).run("iterative-derivation-fixture-" + str(primary_wrong))
        return report, adapters

    passed, _ = run(True)
    blocked, blocked_adapters = run(False)
    failed, _ = run(True, {key: [apply_invalid, apply_invalid] for key in actions})
    decision = next(item for item in passed["route_decisions"] if item["item_id"] == "arithmetic-18")
    assert decision["final_answer"] == "B"
    assert decision["resolution_policy"] == "PROVIDER_BACKED_CANDIDATE_REVISION"
    assert passed["comparisons"]["iterative_derivation_verified"] == 1
    assert passed["comparisons"]["iterative_invalid_actions"] == 1
    assert passed["comparisons"]["iterative_provider_turns"] == 5
    assert passed["comparisons"]["case_corrections"] == 1
    assert blocked["pre_route_audit"]["gate_passed"] is False
    assert failed["comparisons"]["iterative_derivation_verified"] == 0
    assert failed["comparisons"]["iterative_failed_provider_turns"] == 2
    assert failed["comparisons"]["iterative_failed_applied_steps"] == 0
    assert failed["comparisons"]["iterative_failed_invalid_actions"] == 2
    assert failed["comparisons"]["iterative_provider_turns"] == 2
    assert not [task for adapter in blocked_adapters.values() for task in adapter.observed_tasks
                if task.task_kind in {"pilot_disagreement_argument", "pilot_disagreement_adjudication"}]


def test_holdout_v18_staged_algebra_replays_all_reference_families():
    harness = build_holdout_v18_harness()
    plans = {
        "arithmetic-19": ("B", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("STEP_1", "VALUE_3")))),
        "rate-19": ("B", _typed_steps(("DIVIDE", ("VALUE_1", "VALUE_2")), ("MULTIPLY", ("STEP_1", "VALUE_3")))),
        "percent-19": ("C", _typed_steps(("DIVIDE", ("VALUE_1", "CONST_100")), ("MULTIPLY", ("STEP_1", "VALUE_2")))),
        "sets-19": ("C", _typed_steps(("ADD", ("VALUE_2", "VALUE_3")), ("SUBTRACT", ("STEP_1", "VALUE_4")), ("SUBTRACT", ("VALUE_1", "STEP_2")))),
        "probability-19": ("B", _typed_steps(("ADD", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("VALUE_1", "STEP_1")), ("SUBTRACT", ("VALUE_1", "CONST_1")), ("SUBTRACT", ("STEP_1", "CONST_1")), ("DIVIDE", ("STEP_3", "STEP_4")), ("MULTIPLY", ("STEP_2", "STEP_5")), ("SUBTRACT", ("CONST_1", "STEP_6")))),
        "bayes-19": ("C", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("CONST_100", "VALUE_1")), ("SUBTRACT", ("CONST_100", "VALUE_3")), ("MULTIPLY", ("STEP_2", "STEP_3")), ("ADD", ("STEP_1", "STEP_4")), ("DIVIDE", ("STEP_1", "STEP_5")))),
        "modular-19": ("C", _typed_steps(("MODULO", ("VALUE_1", "VALUE_2")))),
        "ratio-19": ("B", _typed_steps(("ADD", ("VALUE_2", "VALUE_3")), ("MULTIPLY", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("STEP_2", "STEP_1")))),
        "average-19": ("C", _typed_steps(("ADD", ("VALUE_1", "VALUE_2")), ("ADD", ("STEP_1", "VALUE_3")), ("ADD", ("STEP_2", "VALUE_4")), ("ADD", ("STEP_3", "VALUE_5")), ("DIVIDE", ("STEP_4", "VALUE_6")))),
        "code-19": ("C", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_5")), ("ADD", ("STEP_1", "VALUE_2")), ("MULTIPLY", ("STEP_2", "VALUE_5")), ("ADD", ("STEP_3", "VALUE_3")), ("MULTIPLY", ("STEP_4", "VALUE_5")), ("ADD", ("STEP_5", "VALUE_4")))),
        "string-19": ("A", _typed_steps(("SWAP_HALVES", ("VALUE_1",)), ("REVERSE_PAIRS", ("STEP_1",)))),
        "unit-19": ("C", _typed_steps(("MULTIPLY", ("VALUE_1", "VALUE_2")))),
    }
    receipts = []
    for item_id, (label, plan) in plans.items():
        symbols, steps = dict(harness.derivation_scaffold(item_id)), []
        for spec in plan:
            action = {"action": "APPLY", "operator": spec["operator"],
                      "inputs": spec["inputs"], "proposed_candidate": "PENDING",
                      "evidence_refs": list(harness.evidence_refs)}
            step = harness.execute_derivation_step(
                item_id=item_id, candidate_id="CANDIDATE_1", step_id=spec["step_id"],
                action=action, symbol_values=symbols,
            )
            steps.append(step)
            symbols[step.step_id] = step.result
        receipts.append(harness.finalize_derivation_session(
            item_id=item_id, candidate_id="CANDIDATE_1", original_candidate="D",
            action={"action": "FINALIZE", "operator": "NONE", "inputs": [steps[-1].step_id],
                    "proposed_candidate": label, "evidence_refs": list(harness.evidence_refs)},
            step_receipts=tuple(steps), provider_turns=len(steps) * 2 + 2, invalid_actions=0,
        ))

    assert len(receipts) == len(HOLDOUT_V18_QUESTIONS)
    assert all(item.status == "VERIFIED" and item.disposition == "REVISE" for item in receipts)
    assert "217" not in harness.derivation_scaffold("arithmetic-19").values()


def test_staged_protocol_separates_control_cost_and_action_arguments():
    receipt, reviewer_ledger, profiles, fingerprint_snapshot, operator_receipt, operator_credit, _ = _operator_credit_fixture()
    resolution_evidence, resolution_candidates, resolution_promotions, resolution_credit = _multi_cycle_resolution_fixture()
    context_evidence, context_candidates, context_promotions, context_credit = _context_resolution_fixture()
    schedule = {"arithmetic-19": "PEER_SECOND"}
    invalid = {"action": "APPLY", "operator": "ADD", "inputs": ["VALUE_1"],
               "proposed_candidate": "PENDING"}
    multiply = {"action": "APPLY", "operator": "MULTIPLY",
                "inputs": ["VALUE_1", "VALUE_2"], "proposed_candidate": "PENDING"}
    subtract = {"action": "APPLY", "operator": "SUBTRACT",
                "inputs": ["STEP_1", "VALUE_3"], "proposed_candidate": "PENDING"}
    finalize = {"action": "FINALIZE", "operator": "NONE", "inputs": ["STEP_2"],
                "proposed_candidate": "B"}
    abstain = {"action": "ABSTAIN", "operator": "NONE", "inputs": [],
               "proposed_candidate": "ABSTAIN"}
    actions = {"A": [invalid, multiply, subtract, finalize],
               "B": [abstain], "C": [abstain], "D": [abstain]}

    def run(primary_wrong, action_plan=actions):
        ledger = ProviderTelemetryLedger()
        primary = dict(HOLDOUT_V18_TRUTH)
        primary["arithmetic-19"] = "A" if primary_wrong else "B"
        peer = dict(HOLDOUT_V18_TRUTH)
        peer["arithmetic-19"] = "D"
        adapters = {
            "small-a": CaseFixtureAdapter("small-a", ledger, HOLDOUT_V18_TRUTH, confidence=0.1,
                                           judge_label="B", staged_actions_by_label=action_plan),
            "small-b": CaseFixtureAdapter("small-b", ledger, primary, confidence=0.99,
                                           staged_actions_by_label=action_plan),
            "small-c": CaseFixtureAdapter("small-c", ledger, peer, confidence=0.1,
                                           staged_actions_by_label=action_plan),
        }
        base = LocalCollectiveCognitionProtocol(
            harness=build_holdout_v18_harness(), small_adapters=adapters,
            baseline_adapter=FixtureAdapter("deepseek-32b", ledger, HOLDOUT_V18_TRUTH),
            telemetry_ledger=ledger, reviewer_model_id="small-b", synthesizer_model_id="small-c",
        )
        policy = CandidateRevisionPolicy(
            operator_credit=operator_credit, operator_schedule=schedule,
            item_fingerprints=HOLDOUT_V18_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit, exploration_items=(),
            context_credit=context_credit, model_ids=tuple(profiles),
            information_value_weight=20.0, work_cost_weight=0.0,
        )
        report = StagedDerivationProtocol(
            base=base, calibration_receipt=receipt, profiles=profiles,
            reviewer_ledger=reviewer_ledger, fingerprint_credit_snapshot=fingerprint_snapshot,
            operator_evidence_receipt=operator_receipt, operator_credit_snapshot=operator_credit,
            operator_schedule=schedule, acquisition_schedule=schedule,
            resolution_exploration_schedule={}, resolution_evidence_receipts=resolution_evidence,
            resolution_candidates=resolution_candidates, resolution_promotions=resolution_promotions,
            resolution_credit_snapshot=resolution_credit, context_evidence_receipts=context_evidence,
            context_candidates=context_candidates, context_promotions=context_promotions,
            context_credit_snapshot=context_credit, policy=policy,
        ).run("staged-derivation-fixture-" + str(primary_wrong))
        return report, adapters

    passed, _ = run(True)
    blocked, blocked_adapters = run(False)
    failed, _ = run(True, {key: [invalid, invalid] for key in actions})
    decision = next(item for item in passed["route_decisions"] if item["item_id"] == "arithmetic-19")
    assert decision["final_answer"] == "B"
    assert decision["resolution_policy"] == "PROVIDER_BACKED_CANDIDATE_REVISION"
    assert passed["comparisons"]["staged_derivation_verified"] == 1
    assert passed["comparisons"]["staged_control_turns"] == 5
    assert passed["comparisons"]["staged_argument_turns"] == 4
    assert passed["comparisons"]["staged_provider_turns"] == 9
    assert passed["comparisons"]["staged_applied_steps"] == 2
    assert passed["comparisons"]["staged_invalid_arguments"] == 1
    assert passed["comparisons"]["case_corrections"] == 1
    assert failed["comparisons"]["staged_failed_control_turns"] == 2
    assert failed["comparisons"]["staged_failed_argument_turns"] == 2
    assert failed["comparisons"]["staged_failed_provider_turns"] == 4
    assert failed["comparisons"]["staged_failed_invalid_arguments"] == 2
    assert blocked["pre_route_audit"]["gate_passed"] is False
    assert not [task for adapter in blocked_adapters.values() for task in adapter.observed_tasks
                if task.task_kind in {"pilot_disagreement_argument", "pilot_disagreement_adjudication"}]
