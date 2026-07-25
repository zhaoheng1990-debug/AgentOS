"""Provider contract for claim-atom to evidence-group binding."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from ..provider_telemetry import hash_payload

TASK_KIND = "SCIFACT_CLAIM_ATOM_BINDING_V0_89"
RECEIPT_KIND = "CLAIM_ATOM_BINDING"
ATOM_TYPES = (
    "ENTITY_OR_POPULATION",
    "RELATION_OR_OUTCOME",
    "DIRECTION_OR_POLARITY",
    "QUANTIFIER_OR_SCOPE",
    "CAUSALITY_OR_MODALITY",
    "CONDITION_OR_TIME",
)
BINDING_STATES = (
    "BOUND_EXPLICIT",
    "BOUND_COMPOSITIONAL",
    "PARTIAL",
    "UNBOUND",
    "CONTRADICTED",
)
RELATIONS = ("SUPPORTS", "REFUTES", "INSUFFICIENT")
DIRECTNESS_STATES = (
    "DIRECT_EXPLICIT",
    "DIRECT_COMPOSITIONAL",
    "QUALIFIED_ONLY",
    "ASSOCIATIONAL_ONLY",
    "REQUIRES_UNSTATED_BRIDGE",
    "OUT_OF_SCOPE",
)
ATOM_FIELDS = ("atom_id", "atom_type", "atom_text", "required")
ATOM_BINDING_FIELDS = (
    "atom_id",
    "binding_state",
    "unit_ids",
    "rationale",
)
GROUP_BINDING_FIELDS = (
    "group_id",
    "relation_to_claim",
    "directness",
    "atom_bindings",
    "unstated_bridge_required",
    "bridge_description",
    "rationale",
)
REQUIRED_FIELDS = (
    "case_id",
    "receipt_kind",
    "source_public_case_hash",
    "source_evidence_set_hash",
    "claim_atoms",
    "group_bindings",
    "all_atoms_assessed",
    "all_groups_assessed",
    "rationale",
)


def build_claim_atom_binding_task(
    *,
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    group_ids = [
        group["group_id"] for group in evidence_receipt["evidence_groups"]
    ]
    unit_ids = [unit["unit_id"] for unit in public_case["evidence_units"]]
    return ProviderCognitiveTask(
        task_id=f"scifact-v0-89-binding-{public_case['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Decompose the claim into required semantic atoms, then assess "
            "whether every evidence group directly binds each atom. Atoms "
            "must cover the claim's entity or population, relation or "
            "outcome, direction or polarity, quantifier or scope, causality "
            "or modality, and any material condition or time qualifier. "
            "Do not fill missing links from scientific background knowledge. "
            "Mark any required but unstated link explicitly. Distinguish "
            "direct textual or compositional entailment from association, "
            "qualification, and unsupported causal or directional upgrade. "
            "Assess every atom for every evidence group. Do not output a "
            "candidate action, admission, promotion, retention, or utility."
        ),
        inputs={
            "benchmark_id": public_case["benchmark_id"],
            "case_id": public_case["case_id"],
            "claim": public_case["cognitive_object"]["claim"],
            "evidence_units": public_case["evidence_units"],
            "evidence_groups": evidence_receipt["evidence_groups"],
            "source_public_case_hash": hash_payload(public_case),
            "source_evidence_set_hash": hash_payload(evidence_receipt),
            "private_reference_available": False,
            "scope_receipt_available": False,
            "policy_action_requested": False,
        },
        allowed_evidence=unit_ids,
        expected_schema=_schema(public_case, evidence_receipt),
        timeout_seconds=min(300, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure_and_abstain",
    )


def validate_claim_atom_binding(
    receipt: dict[str, Any],
    *,
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
) -> list[str]:
    failures = []
    if set(receipt) != set(REQUIRED_FIELDS):
        failures.append("CLAIM_ATOM_BINDING_SHAPE_INVALID")
    if receipt.get("case_id") != public_case["case_id"]:
        failures.append("CLAIM_ATOM_BINDING_CASE_MISMATCH")
    if receipt.get("receipt_kind") != RECEIPT_KIND:
        failures.append("CLAIM_ATOM_BINDING_KIND_INVALID")
    if receipt.get("source_public_case_hash") != hash_payload(public_case):
        failures.append("CLAIM_ATOM_BINDING_PUBLIC_HASH_INVALID")
    if receipt.get("source_evidence_set_hash") != hash_payload(
        evidence_receipt
    ):
        failures.append("CLAIM_ATOM_BINDING_EVIDENCE_HASH_INVALID")
    if receipt.get("all_atoms_assessed") is not True:
        failures.append("CLAIM_ATOM_BINDING_ATOM_ASSESSMENT_INCOMPLETE")
    if receipt.get("all_groups_assessed") is not True:
        failures.append("CLAIM_ATOM_BINDING_GROUP_ASSESSMENT_INCOMPLETE")

    atoms = receipt.get("claim_atoms")
    atom_ids = []
    if not isinstance(atoms, list) or not atoms:
        failures.append("CLAIM_ATOM_BINDING_ATOMS_INVALID")
        atoms = []
    for atom in atoms:
        if not isinstance(atom, dict) or set(atom) != set(ATOM_FIELDS):
            failures.append("CLAIM_ATOM_BINDING_ATOM_SHAPE_INVALID")
            continue
        atom_ids.append(atom.get("atom_id"))
        if (
            not _nonempty(atom.get("atom_id"))
            or atom.get("atom_type") not in ATOM_TYPES
            or not _nonempty(atom.get("atom_text"))
            or atom.get("required") is not True
        ):
            failures.append("CLAIM_ATOM_BINDING_ATOM_VALUE_INVALID")
    if len(atom_ids) != len(set(atom_ids)):
        failures.append("CLAIM_ATOM_BINDING_ATOM_ID_DUPLICATE")

    group_map = {
        group["group_id"]: group
        for group in evidence_receipt["evidence_groups"]
    }
    bindings = receipt.get("group_bindings")
    seen_groups = []
    if not isinstance(bindings, list):
        failures.append("CLAIM_ATOM_BINDING_GROUPS_INVALID")
        bindings = []
    for binding in bindings:
        if (
            not isinstance(binding, dict)
            or set(binding) != set(GROUP_BINDING_FIELDS)
        ):
            failures.append("CLAIM_ATOM_BINDING_GROUP_SHAPE_INVALID")
            continue
        group_id = binding.get("group_id")
        seen_groups.append(group_id)
        group = group_map.get(group_id)
        if (
            group is None
            or binding.get("relation_to_claim") not in RELATIONS
            or binding.get("directness") not in DIRECTNESS_STATES
            or not isinstance(binding.get("unstated_bridge_required"), bool)
            or not isinstance(binding.get("bridge_description"), str)
            or not _nonempty(binding.get("rationale"))
        ):
            failures.append("CLAIM_ATOM_BINDING_GROUP_VALUE_INVALID")
            continue
        if (
            binding["unstated_bridge_required"]
            != (
                binding["directness"]
                == "REQUIRES_UNSTATED_BRIDGE"
            )
        ):
            failures.append("CLAIM_ATOM_BINDING_BRIDGE_INCONSISTENT")
        if (
            binding["unstated_bridge_required"]
            and not binding["bridge_description"].strip()
        ):
            failures.append("CLAIM_ATOM_BINDING_BRIDGE_DESCRIPTION_MISSING")
        _validate_atom_bindings(
            binding.get("atom_bindings"),
            atom_ids=atom_ids,
            allowed_units=set(group["unit_ids"]),
            failures=failures,
        )
    expected_groups = set(group_map)
    if set(seen_groups) != expected_groups or len(seen_groups) != len(
        set(seen_groups)
    ):
        failures.append("CLAIM_ATOM_BINDING_GROUP_COVERAGE_INVALID")
    if not _nonempty(receipt.get("rationale")):
        failures.append("CLAIM_ATOM_BINDING_RATIONALE_MISSING")
    forbidden = {
        "runtime_action",
        "candidate_state",
        "admission",
        "promotion",
        "retention",
        "utility",
    }
    if forbidden.intersection({key.casefold() for key in receipt}):
        failures.append("CLAIM_ATOM_BINDING_POLICY_AUTHORITY_PRESENT")
    return sorted(set(failures))


def _validate_atom_bindings(
    value: Any,
    *,
    atom_ids: list[Any],
    allowed_units: set[str],
    failures: list[str],
) -> None:
    seen_atoms = []
    if not isinstance(value, list):
        failures.append("CLAIM_ATOM_BINDING_ATOM_BINDINGS_INVALID")
        return
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != set(ATOM_BINDING_FIELDS)
        ):
            failures.append("CLAIM_ATOM_BINDING_ATOM_BINDING_SHAPE_INVALID")
            continue
        seen_atoms.append(item.get("atom_id"))
        units = item.get("unit_ids")
        if (
            item.get("atom_id") not in atom_ids
            or item.get("binding_state") not in BINDING_STATES
            or not isinstance(units, list)
            or len(units) != len(set(units))
            or not set(units).issubset(allowed_units)
            or not _nonempty(item.get("rationale"))
        ):
            failures.append("CLAIM_ATOM_BINDING_ATOM_BINDING_VALUE_INVALID")
        elif (
            item["binding_state"] in {
                "BOUND_EXPLICIT",
                "BOUND_COMPOSITIONAL",
                "CONTRADICTED",
            }
            and not units
        ):
            failures.append("CLAIM_ATOM_BINDING_BOUND_ATOM_EVIDENCE_MISSING")
    if set(seen_atoms) != set(atom_ids) or len(seen_atoms) != len(
        set(seen_atoms)
    ):
        failures.append("CLAIM_ATOM_BINDING_ATOM_COVERAGE_INVALID")


def _schema(
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
) -> dict[str, Any]:
    group_ids = [
        group["group_id"] for group in evidence_receipt["evidence_groups"]
    ]
    unit_ids = [unit["unit_id"] for unit in public_case["evidence_units"]]
    atom = _object_schema(
        ATOM_FIELDS,
        {
            "atom_id": {"type": "string"},
            "atom_type": {"type": "string", "enum": list(ATOM_TYPES)},
            "atom_text": {"type": "string"},
            "required": {"type": "boolean", "enum": [True]},
        },
    )
    atom_binding = _object_schema(
        ATOM_BINDING_FIELDS,
        {
            "atom_id": {"type": "string"},
            "binding_state": {
                "type": "string",
                "enum": list(BINDING_STATES),
            },
            "unit_ids": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string", "enum": unit_ids},
            },
            "rationale": {"type": "string"},
        },
    )
    group_binding = _object_schema(
        GROUP_BINDING_FIELDS,
        {
            "group_id": {"type": "string", "enum": group_ids},
            "relation_to_claim": {
                "type": "string",
                "enum": list(RELATIONS),
            },
            "directness": {
                "type": "string",
                "enum": list(DIRECTNESS_STATES),
            },
            "atom_bindings": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": atom_binding,
            },
            "unstated_bridge_required": {"type": "boolean"},
            "bridge_description": {"type": "string"},
            "rationale": {"type": "string"},
        },
    )
    return _object_schema(
        REQUIRED_FIELDS,
        {
            "case_id": {"type": "string", "enum": [public_case["case_id"]]},
            "receipt_kind": {"type": "string", "enum": [RECEIPT_KIND]},
            "source_public_case_hash": {
                "type": "string",
                "enum": [hash_payload(public_case)],
            },
            "source_evidence_set_hash": {
                "type": "string",
                "enum": [hash_payload(evidence_receipt)],
            },
            "claim_atoms": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": atom,
            },
            "group_bindings": {
                "type": "array",
                "minItems": len(group_ids),
                "maxItems": len(group_ids),
                "uniqueItems": True,
                "items": group_binding,
            },
            "all_atoms_assessed": {"type": "boolean", "enum": [True]},
            "all_groups_assessed": {"type": "boolean", "enum": [True]},
            "rationale": {"type": "string"},
        },
    )


def _object_schema(
    required: tuple[str, ...],
    properties: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(required),
        "properties": properties,
    }


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
