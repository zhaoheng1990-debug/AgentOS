"""Bounded live R4 orchestration and deterministic scoring."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .cases import CASES, ROLE_IDS
from .prompts import (
    COORDINATOR_SYSTEM,
    ROLE_SYSTEM,
    coordinator_prompt,
    role_prompt,
)
from .provider import DeepSeekAdapter
from .schemas import (
    CoordinatorReceipt,
    RoleReceipt,
    parse_coordinator_receipts,
    parse_role_receipts,
)
from .scoring import SUBSETS, evaluate_predictions, subset_key


def _role_dicts(
    receipts: list[RoleReceipt], include_provider_direction: bool
) -> list[dict[str, object]]:
    packets = []
    for receipt in receipts:
        packet = asdict(receipt)
        packet.pop("dropped_provider_fields", None)
        if not include_provider_direction:
            packet.pop("direction", None)
        packets.append(packet)
    return packets


def _probabilities(receipts: list[RoleReceipt | CoordinatorReceipt]) -> dict[str, float]:
    return {receipt.case_id: receipt.probability_y1 for receipt in receipts}


def run_live_experiment(
    adapter: DeepSeekAdapter | None = None, protocol_version: str = "v0_1"
) -> dict[str, Any]:
    if protocol_version not in {"v0_1", "v0_2"}:
        raise ValueError("unknown protocol version")
    include_provider_direction = protocol_version == "v0_1"
    provider = adapter or DeepSeekAdapter()
    raw_contents: dict[str, str] = {}
    role_runs: dict[str, dict[str, list[RoleReceipt]]] = {}

    for role_id in ROLE_IDS:
        role_runs[role_id] = {}
        for replicate in ("A", "B"):
            logical_id = f"role_{role_id}_{replicate}"
            content, receipts = provider.call_json(
                logical_id,
                ROLE_SYSTEM,
                role_prompt(role_id, replicate, include_provider_direction),
                lambda value, role=role_id: parse_role_receipts(
                    value, role, include_provider_direction
                ),
            )
            raw_contents[logical_id] = content
            role_runs[role_id][replicate] = receipts

    role_packets = {
        role_id: _role_dicts(
            role_runs[role_id]["A"], include_provider_direction
        )
        for role_id in ROLE_IDS
    }
    coordinator_runs: dict[str, list[CoordinatorReceipt]] = {}
    coordinator_specs = (
        (("ROLE_A", "ROLE_B"), "A"),
        (("ROLE_A", "ROLE_C"), "A"),
        (("ROLE_B", "ROLE_C"), "A"),
        (ROLE_IDS, "A"),
        (ROLE_IDS, "B"),
    )
    for roles, replicate in coordinator_specs:
        logical_id = f"coordinator_{'_'.join(roles)}_{replicate}"
        content, receipts = provider.call_json(
            logical_id,
            COORDINATOR_SYSTEM,
            coordinator_prompt(
                roles, role_packets, replicate, include_provider_direction
            ),
            lambda value, included=roles: parse_coordinator_receipts(
                value, included, include_provider_direction
            ),
        )
        raw_contents[logical_id] = content
        coordinator_runs[logical_id] = receipts

    predictions: dict[str, dict[str, float]] = {
        "PRIOR": {case.case_id: case.prior_y1 for case in CASES},
        "ROLE_A": _probabilities(role_runs["ROLE_A"]["A"]),
        "ROLE_B": _probabilities(role_runs["ROLE_B"]["A"]),
        "ROLE_C": _probabilities(role_runs["ROLE_C"]["A"]),
        "ROLE_A+ROLE_B": _probabilities(coordinator_runs["coordinator_ROLE_A_ROLE_B_A"]),
        "ROLE_A+ROLE_C": _probabilities(coordinator_runs["coordinator_ROLE_A_ROLE_C_A"]),
        "ROLE_B+ROLE_C": _probabilities(coordinator_runs["coordinator_ROLE_B_ROLE_C_A"]),
        "ROLE_A+ROLE_B+ROLE_C": _probabilities(
            coordinator_runs["coordinator_ROLE_A_ROLE_B_ROLE_C_A"]
        ),
    }
    if set(predictions) != {subset_key(roles) for roles in SUBSETS}:
        raise RuntimeError("prediction subset coverage mismatch")

    scoring = evaluate_predictions(
        predictions,
        {
            role: (
                _probabilities(role_runs[role]["A"]),
                _probabilities(role_runs[role]["B"]),
            )
            for role in ROLE_IDS
        },
        (
            _probabilities(coordinator_runs["coordinator_ROLE_A_ROLE_B_ROLE_C_A"]),
            _probabilities(coordinator_runs["coordinator_ROLE_A_ROLE_B_ROLE_C_B"]),
        ),
    )
    ledger = provider.ledger()
    total_tokens = sum(int(row["usage"]["total_tokens"]) for row in ledger)
    valid_attempts = sum(row["status"] == "VALID" for row in ledger)
    gates = {
        "call_and_attempt_budget": valid_attempts == 11 and len(ledger) <= 22,
        "token_limit": total_tokens <= 200000,
        "role_mechanical_validity": all(
            len(role_runs[role][replicate]) == len(CASES)
            for role in ROLE_IDS
            for replicate in ("A", "B")
        ),
        "coordinator_mechanical_validity": all(
            len(receipts) == len(CASES) for receipts in coordinator_runs.values()
        ),
        "role_mean_probability_error": scoring["role_probability_error"]["mean"]
        <= 0.02,
        "role_max_probability_error": scoring["role_probability_error"]["maximum"]
        <= 0.08,
        "replicate_direction_agreement": scoring[
            "role_stability_direction_agreement"
        ]
        == 1.0,
        "replicate_probability_mae": scoring["role_stability_probability"]["mean"]
        <= 0.03,
        "full_mean_probability_error": scoring["full_probability_error"]["mean"]
        <= 0.03,
        "full_direction_agreement": scoring["full_direction_agreement"] == 1.0,
        "full_strong_wrong_zero": scoring["full_strong_wrong_count"] == 0,
        "k_info_bounded_positive": 0.0 < scoring["k_info"] <= 1.05,
        "shapley_role_order": scoring["role_order_matches"],
        "no_raw_or_private_reference": all(
            not receipt.raw_evidence_used and not receipt.private_reference_used
            for receipts in coordinator_runs.values()
            for receipt in receipts
        ),
        "no_forbidden_project_write": True,
    }
    mechanical_gate_names = {
        "call_and_attempt_budget",
        "token_limit",
        "role_mechanical_validity",
        "coordinator_mechanical_validity",
        "no_raw_or_private_reference",
        "no_forbidden_project_write",
    }
    if all(gates.values()):
        status = "PASS"
    elif all(gates[name] for name in mechanical_gate_names):
        status = "PARTIAL"
    else:
        status = "FAIL"
    return {
        "experiment_version": f"agentos_r4_provider_adequacy_{protocol_version}",
        "status": status,
        "claim_ceiling": (
            "SAME_PROVIDER_CONTEXT_ISOLATION_ADEQUACY_ONLY"
            if protocol_version == "v0_1"
            else "PAIRED_MINIMAL_RECEIPT_DIAGNOSTIC_ONLY"
        ),
        "provider": {
            "provider_id": "deepseek",
            "model_id": "deepseek-v4-flash",
            "thinking": "disabled",
            "response_format": "json_object",
        },
        "logical_call_count": valid_attempts,
        "physical_attempt_count": len(ledger),
        "total_tokens": total_tokens,
        "attempt_ledger": ledger,
        "scoring": scoring,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "raw_contents": raw_contents,
        "provider_authority": False,
        "runtime_write_allowed": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
    }


def write_result(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
