"""Deterministic role composition and factor compilation for R4 v0.3K."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .factor_compiler import compile_factorized_transformation
from .factor_contracts import FactorizedTransformationCandidate
from .role_cases import (
    EFFECT_ATTRIBUTES,
    PROVENANCE_ATTRIBUTES,
    ROLE_CASES,
    WIDE_ATTRIBUTES,
)
from .role_schemas import ParsedRoleReceipts


@dataclass(frozen=True)
class ComposedRoleReceipt:
    arm: str
    round_name: str
    case_id: str
    attributes: tuple[tuple[str, str], ...]
    refs: tuple[tuple[str, tuple[str, ...]], ...]
    dropped_fields: tuple[str, ...]

    def attribute_dict(self) -> dict[str, str]:
        return dict(self.attributes)

    def ref_dict(self) -> dict[str, tuple[str, ...]]:
        return dict(self.refs)


def compose_receipts(
    provenance_source: ParsedRoleReceipts,
    effect_source: ParsedRoleReceipts,
    arm: str,
    round_name: str,
) -> tuple[ComposedRoleReceipt, ...]:
    if provenance_source.scope not in {"wide", "provenance"}:
        raise ValueError("invalid provenance source scope")
    if effect_source.scope not in {"wide", "effect"}:
        raise ValueError("invalid effect source scope")
    provenance = provenance_source.by_case()
    effect = effect_source.by_case()
    if set(provenance) != set(effect):
        raise ValueError("role source case coverage mismatch")
    composed = []
    for case_id in sorted(provenance):
        p_receipt = provenance[case_id]
        e_receipt = effect[case_id]
        p_values = p_receipt.attribute_dict()
        e_values = e_receipt.attribute_dict()
        p_refs = p_receipt.ref_dict()
        e_refs = e_receipt.ref_dict()
        values = {
            **{name: p_values[name] for name in PROVENANCE_ATTRIBUTES},
            **{name: e_values[name] for name in EFFECT_ATTRIBUTES},
        }
        refs = {
            **{name: p_refs[name] for name in PROVENANCE_ATTRIBUTES},
            **{name: e_refs[name] for name in EFFECT_ATTRIBUTES},
        }
        composed.append(
            ComposedRoleReceipt(
                arm=arm,
                round_name=round_name,
                case_id=case_id,
                attributes=tuple((name, values[name]) for name in WIDE_ATTRIBUTES),
                refs=tuple((name, refs[name]) for name in WIDE_ATTRIBUTES),
                dropped_fields=tuple(
                    sorted(set(p_receipt.dropped_fields + e_receipt.dropped_fields))
                ),
            )
        )
    return tuple(composed)


def _ref(
    refs: dict[str, tuple[str, ...]],
    name: str,
    suffix: str | None = None,
) -> str | None:
    values = refs[name]
    if suffix:
        return next((value for value in values if value.endswith(suffix)), None)
    return values[0] if values else None


def candidate_from_receipt(
    receipt: ComposedRoleReceipt,
) -> FactorizedTransformationCandidate:
    values = receipt.attribute_dict()
    refs = receipt.ref_dict()
    return FactorizedTransformationCandidate(
        case_id=receipt.case_id,
        case_family="matched_role_decomposition",
        source_identity=values["source_identity"],
        lineage_coupling=values["lineage_coupling"],
        transform_status=values["transform_status"],
        information_effect=values["information_effect"],
        added_uncertainty=values["added_uncertainty"],
        target_claim_relation=values["target_claim_relation"],
        source_witness_ref=_ref(refs, "source_identity"),
        lineage_witness_ref=_ref(refs, "lineage_coupling"),
        transform_status_witness_ref=_ref(refs, "transform_status"),
        information_effect_witness_ref=_ref(refs, "information_effect"),
        target_claim_witness_ref=_ref(refs, "target_claim_relation"),
        uncertainty_witness_ref=_ref(refs, "added_uncertainty"),
        claim_tolerance_witness_ref=_ref(
            refs, "added_uncertainty", "/tolerance"
        ),
        full_domain_witness_ref=(
            _ref(refs, "information_effect")
            if values["information_effect"] == "GLOBAL_EQUIVALENT"
            else None
        ),
        expected_relation_state="UNRESOLVED",
        expected_action="BLOCK",
    )


def compile_composed(receipt: ComposedRoleReceipt):
    return compile_factorized_transformation(candidate_from_receipt(receipt))


def private_receipts() -> tuple[ComposedRoleReceipt, ...]:
    return tuple(
        ComposedRoleReceipt(
            arm="private",
            round_name="private",
            case_id=case.case_id,
            attributes=tuple(
                (name, case.factorized_dict()[name]) for name in WIDE_ATTRIBUTES
            ),
            refs=tuple(
                (name, case.expected_refs()[name]) for name in WIDE_ATTRIBUTES
            ),
            dropped_fields=(),
        )
        for case in ROLE_CASES
    )


def private_outcomes() -> dict[str, dict[str, object]]:
    outcomes = {}
    for case, receipt in zip(ROLE_CASES, private_receipts(), strict=True):
        compiled = compile_composed(receipt)
        outcomes[case.case_id] = {
            "relation_state": compiled.relation_state,
            "action": compiled.action,
            "revalidation": case.revalidation,
            "errors": compiled.errors,
        }
    return outcomes


def fail_closed_mutation_audit() -> dict[str, bool]:
    base = candidate_from_receipt(private_receipts()[0])
    mutations = {
        "invalid_status_effect": replace(
            base,
            transform_status="NO_TRANSFORM",
            information_effect="GLOBAL_EQUIVALENT",
        ),
        "missing_source_witness": replace(base, source_witness_ref=None),
        "missing_tolerance_witness": replace(
            base, claim_tolerance_witness_ref=None
        ),
    }
    return {
        name: (
            (compiled := compile_factorized_transformation(candidate)).relation_state
            == "UNRESOLVED"
            and compiled.action == "BLOCK"
            and bool(compiled.errors)
        )
        for name, candidate in mutations.items()
    }
