"""Hash-bound receipts for Provider semantic structure judgments."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_VERSION


def build_judgment_receipt(*, task, payload, invocation_receipt, surface, adapter):
    candidate_ids = [item["blind_candidate_id"] for item in payload["assessments"]]
    commitment = {
        "judge_version": JUDGE_VERSION,
        "batch_id": payload["batch_id"],
        "judge_provider_id": adapter.profile.provider_id,
        "judge_model_id": adapter.profile.model_id,
        "task_contract_hash": task.contract_hash(),
        "invocation_receipt_hash": invocation_receipt["receipt_hash"],
        "blind_surface_hash": surface["surface_hash"],
        "source_artifact_hash": surface["source_artifact_hash"],
        "candidate_ids": candidate_ids,
        "payload_hash": hash_payload(payload),
        "evidence_refs": list(task.allowed_evidence),
        "provider_backed": True,
        "provider_authority": False,
        "source_identity_withheld": True,
    }
    return {**commitment, "receipt_hash": hash_payload(commitment)}


def validate_judgment_receipt(receipt, *, payload=None, surface=None):
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if (receipt.get("judge_version") != JUDGE_VERSION
            or receipt.get("receipt_hash") != hash_payload(committed)
            or receipt.get("provider_backed") is not True
            or receipt.get("provider_authority") is not False
            or receipt.get("source_identity_withheld") is not True):
        raise ValueError("semantic_judgment_receipt_invalid")
    if payload is not None and receipt["payload_hash"] != hash_payload(payload):
        raise ValueError("semantic_judgment_payload_binding_invalid")
    if surface is not None and (
        receipt["blind_surface_hash"] != surface["surface_hash"]
        or receipt["source_artifact_hash"] != surface["source_artifact_hash"]
    ):
        raise ValueError("semantic_judgment_surface_binding_invalid")


def validate_judge_run(run, *, surface=None):
    committed = {key: value for key, value in run.items() if key != "judge_run_hash"}
    if run.get("judge_run_hash") != hash_payload(committed):
        raise ValueError("semantic_judge_run_hash_invalid")
    if surface is not None and run.get("blind_surface_hash") != surface["surface_hash"]:
        raise ValueError("semantic_judge_run_surface_binding_invalid")
    for item in run.get("judgments", []):
        validate_judgment_receipt(item["receipt"], payload=item["payload"], surface=surface)
