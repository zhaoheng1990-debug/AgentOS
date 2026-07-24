"""Frozen institutional constraints for structure-first cognition experiments."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CONSTRAINT_VERSION = "science_institutional_constraints_v0_26"


def build_science_institutional_constraints():
    commitment = {
        "constraint_version": CONSTRAINT_VERSION,
        "source": {
            "title": "Agentic AI and the next intelligence explosion",
            "publication": "Science",
            "doi": "10.1126/science.aeg1895",
            "source_role": "UPPER_LEVEL_ARCHITECTURAL_DIRECTION_NOT_BENCHMARK_EVIDENCE",
        },
        "frozen_principles": [
            {
                "principle_id": "SCI-PLURAL-COGNITION",
                "statement": (
                    "Cognition may be distributed across differentiated and "
                    "relational roles rather than treated as one isolated model."
                ),
                "experiment_constraint": (
                    "Do not infer group cognition from one Provider response; "
                    "this smoke isolates a structure-expansion mechanism only."
                ),
            },
            {
                "principle_id": "SCI-STRUCTURED-DISAGREEMENT",
                "statement": (
                    "Useful cognitive organizations require explicit criticism, "
                    "counterfactual pressure, and checks on premature agreement."
                ),
                "experiment_constraint": (
                    "The intervention arm must include reverse-edge, object-switch, "
                    "or coordinate-switch operations and preserve counterevidence."
                ),
            },
            {
                "principle_id": "SCI-ROLE-DIFFERENTIATION",
                "statement": (
                    "Specialized roles and perspectives should expose information "
                    "that a homogeneous pass can miss."
                ),
                "experiment_constraint": (
                    "Situated perspectives are graph-position bound; role labels "
                    "alone are not counted as independent cognitive agents."
                ),
            },
            {
                "principle_id": "SCI-INSTITUTIONAL-MEMORY",
                "statement": (
                    "Externalized records, replay, and governance are part of the "
                    "cognitive system rather than optional reporting."
                ),
                "experiment_constraint": (
                    "Freeze inputs and receipts by hash, emit replay and rollback "
                    "pointers, and prohibit retention or baseline mutation."
                ),
            },
            {
                "principle_id": "SCI-RECURSIVE-SOCIETY",
                "statement": (
                    "Future agent societies may recursively form and dissolve "
                    "sub-organizations around emerging problems."
                ),
                "experiment_constraint": (
                    "Recursive society formation is explicitly out of scope until "
                    "structure-first problem emergence shows positive gain."
                ),
            },
            {
                "principle_id": "SCI-INSTITUTIONAL-ALIGNMENT",
                "statement": (
                    "Alignment must include institutional checks, role protocols, "
                    "and authority boundaries."
                ),
                "experiment_constraint": (
                    "Provider outputs are candidate receipts; Runtime owns evidence "
                    "scope, validation, scoring, state, and final experiment gate."
                ),
            },
        ],
        "authority_boundary": {
            "provider_is_runtime_support": True,
            "provider_has_final_decision_authority": False,
            "synthetic_output_may_be_promoted_as_real_evidence": False,
            "selection_authority": False,
            "retention_write_allowed": False,
            "baseline_write_allowed": False,
            "production_authority": False,
        },
        "claim_ceiling": (
            "SYNTHETIC_STRUCTURE_FIRST_MECHANISM_SMOKE_ONLY_NO_GROUP_"
            "COGNITION_OR_REAL_WORLD_VALIDITY"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_science_institutional_constraints(artifact):
    commitment = {
        key: value for key, value in artifact.items()
        if key != "artifact_hash"
    }
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact != build_science_institutional_constraints()
    ):
        raise ValueError("science_institutional_constraints_invalid")
