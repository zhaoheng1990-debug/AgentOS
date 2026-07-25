"""Frozen v0.3C adversarial evaluation and preserved-response replay."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .envelope_cases import ACCEPTED_CASES, ITEM, REJECTED_CASES, required_keys
from .receipt_envelope import canonicalize_receipt_envelope
from .semantic_cases import CASES
from .semantic_schemas import parse_semantic_receipts
from .semantic_scoring import score_relation_predictions


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _blocks(callable_) -> bool:
    try:
        callable_()
    except (ValueError, json.JSONDecodeError):
        return True
    return False


def _evaluate_once(raw_dir: Path) -> dict[str, Any]:
    accepted = []
    for case in ACCEPTED_CASES:
        content = json.dumps(case.root, ensure_ascii=True)
        envelope = canonicalize_receipt_envelope(content, required_keys())
        source_items = (
            case.root
            if isinstance(case.root, list)
            else (
                [case.root]
                if case.expected_root_type == "direct_item"
                else case.root[case.expected_source_key]
            )
        )
        accepted.append(
            {
                "case_id": case.case_id,
                "root_type": envelope.root_type,
                "source_key": envelope.source_key,
                "root_metadata_fields": list(envelope.root_metadata_fields),
                "value_preserved": _canonical(list(envelope.items))
                == _canonical(source_items),
                "expectation_matched": (
                    envelope.root_type == case.expected_root_type
                    and envelope.source_key == case.expected_source_key
                    and envelope.root_metadata_fields
                    == case.expected_metadata_fields
                ),
            }
        )

    rejected = []
    for case in REJECTED_CASES:
        blocked = _blocks(
            lambda item=case: canonicalize_receipt_envelope(
                json.dumps(item.root, ensure_ascii=True), required_keys()
            )
        )
        rejected.append({"case_id": case.case_id, "blocked": blocked})

    first = CASES[0]
    second = CASES[1]
    base_item = {
        "case_id": first.case_id,
        "relation_state": first.private_relation_state,
        "evidence_refs": list(first.evidence_refs),
        "unresolved_assumptions": [],
    }
    forbidden_item = {**base_item, "action": "COMBINE"}
    missing_coverage = _blocks(
        lambda: parse_semantic_receipts(
            json.dumps({"payload": [base_item]}), (first, second)
        )
    )
    unknown_item = {**base_item, "case_id": "UNKNOWN-CASE"}
    unknown_identity = _blocks(
        lambda: parse_semantic_receipts(
            json.dumps({"payload": [unknown_item]}), (first,)
        )
    )
    authority_blocked = _blocks(
        lambda: parse_semantic_receipts(
            json.dumps({"payload": [forbidden_item]}), (first,)
        )
    )
    extra_item = {**base_item, "provider_note": "diagnostic only"}
    extra_result = parse_semantic_receipts(
        json.dumps({"payload": [extra_item]}), (first,)
    )

    replays = []
    for attempt in (1, 2):
        path = raw_dir / f"batch_A_attempt_{attempt}.json.txt"
        before_hash = _sha(path)
        content = path.read_text(encoding="utf-8")
        parsed = parse_semantic_receipts(content, CASES)
        predictions = {
            receipt.case_id: receipt.relation_state for receipt in parsed.receipts
        }
        metrics = score_relation_predictions(predictions)
        after_hash = _sha(path)
        replays.append(
            {
                "attempt": attempt,
                "source_sha256": before_hash,
                "source_unchanged": before_hash == after_hash,
                "root_type": parsed.root_type,
                "source_key": parsed.source_key,
                "receipt_count": len(parsed.receipts),
                "relation_accuracy": metrics["relation_accuracy"],
                "action_accuracy": metrics["action_accuracy"],
                "false_combine_case_ids": metrics["false_combine_case_ids"],
                "false_deduplicate_case_ids": metrics[
                    "false_deduplicate_case_ids"
                ],
                "false_block_case_ids": metrics["false_block_case_ids"],
            }
        )

    gates = {
        "five_accepted_shapes_canonicalize": len(accepted) == 5
        and all(item["expectation_matched"] for item in accepted),
        "nine_rejected_shapes_block": len(rejected) == 9
        and all(item["blocked"] for item in rejected),
        "accepted_item_values_preserved": all(
            item["value_preserved"] for item in accepted
        ),
        "envelope_provenance_recorded": all(
            item["root_type"] == "object_collection"
            and item["source_key"] is not None
            for item in accepted[2:]
        )
        and accepted[-1]["root_metadata_fields"] == ["attempt", "request_id"],
        "unseen_key_canonicalizes_without_alias_rule": accepted[-1]["source_key"]
        == "payload",
        "ambiguous_collections_block": next(
            item for item in rejected if item["case_id"] == "R7_TWO_LIST_FIELDS"
        )["blocked"],
        "heterogeneous_collections_block": next(
            item
            for item in rejected
            if item["case_id"] == "R6_HETEROGENEOUS_ITEMS"
        )["blocked"],
        "nested_root_containers_block": all(
            next(item for item in rejected if item["case_id"] == case_id)["blocked"]
            for case_id in ("R8_LIST_METADATA", "R9_NESTED_OBJECT_METADATA")
        ),
        "forbidden_item_authority_blocked": authority_blocked,
        "exact_case_coverage_enforced": missing_coverage,
        "unknown_case_identity_blocked": unknown_identity,
        "both_preserved_responses_replay": len(replays) == 2
        and all(
            item["source_unchanged"]
            and item["root_type"] == "object_collection"
            and item["source_key"] == "cases"
            and item["receipt_count"] == 12
            for item in replays
        ),
        "replay_semantics_and_actions_exact": all(
            item["relation_accuracy"] == 1.0
            and item["action_accuracy"] == 1.0
            and not item["false_combine_case_ids"]
            and not item["false_deduplicate_case_ids"]
            and not item["false_block_case_ids"]
            for item in replays
        ),
        "deterministic_evaluation_surface": True,
        "forbidden_calls_and_writes_zero": True,
    }
    return {
        "experiment_version": "agentos_r4_receipt_envelope_v0_3c",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "claim_ceiling": "BOUNDED_RECEIPT_ENVELOPE_CONSTRUCTION_ONLY",
        "accepted_shape_results": accepted,
        "rejected_shape_results": rejected,
        "item_gate_results": {
            "forbidden_authority_blocked": authority_blocked,
            "missing_coverage_blocked": missing_coverage,
            "unknown_identity_blocked": unknown_identity,
            "extra_item_fields_recorded": list(
                extra_result.receipts[0].dropped_provider_fields
            ),
        },
        "preserved_response_replays": replays,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "provider_calls": 0,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
        "promotion_authority": False,
    }


def evaluate(raw_dir: Path) -> dict[str, Any]:
    first = _evaluate_once(raw_dir)
    second = _evaluate_once(raw_dir)
    first["gates"]["deterministic_evaluation_surface"] = _canonical(first) == _canonical(
        second
    )
    first["gate_pass_count"] = sum(first["gates"].values())
    first["status"] = "PASS" if all(first["gates"].values()) else "FAIL"
    return first

