"""Provider-backed current-case arguments and blinded disagreement adjudication."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .collective_protocol import LocalCollectiveCognitionProtocol, RoleRun
from .disagreement_case_contracts import argument_schema, judgment_schema, validate_argument, validate_judgment
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .provider_telemetry import hash_payload


@dataclass(frozen=True)
class DisagreementCaseBundle:
    item_id: str
    primary_model_id: str
    peer_model_id: str
    judge_model_id: str
    primary_candidate_id: str
    peer_candidate_id: str
    primary_argument_run: RoleRun
    peer_argument_run: RoleRun
    judge_run: RoleRun
    argument_hashes: tuple[str, str]
    judgment_hash: str

    @property
    def judgment(self) -> dict[str, Any]:
        return self.judge_run.result

    def as_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "primary_model_id": self.primary_model_id,
            "peer_model_id": self.peer_model_id,
            "judge_model_id": self.judge_model_id,
            "primary_candidate_id": self.primary_candidate_id,
            "peer_candidate_id": self.peer_candidate_id,
            "primary_argument": self.primary_argument_run.result,
            "peer_argument": self.peer_argument_run.result,
            "judgment": self.judgment,
            "argument_hashes": list(self.argument_hashes),
            "judgment_hash": self.judgment_hash,
            "provider_task_contract_hashes": [
                self.primary_argument_run.tasks[-1].contract_hash(),
                self.peer_argument_run.tasks[-1].contract_hash(),
                self.judge_run.tasks[-1].contract_hash(),
            ],
        }


class DisagreementCaseRuntime:
    def __init__(self, base: LocalCollectiveCognitionProtocol) -> None:
        self.base = base

    def adjudicate(self, *, primary, peer, witness) -> DisagreementCaseBundle:
        if len({primary.model_id, peer.model_id, witness.model_id}) != 3 or not (
            primary.item_id == peer.item_id == witness.item_id
        ):
            raise ValueError("disagreement_case_identity_invalid")
        item_id = primary.item_id
        primary_id, peer_id = self._candidate_ids(item_id)
        completed = []
        try:
            primary_run = self._argument_run(
                item_id=item_id, model_id=primary.model_id,
                candidate_id=primary_id, candidate_label=primary.answer,
            )
            completed.append(primary_run)
            peer_run = self._argument_run(
                item_id=item_id, model_id=peer.model_id,
                candidate_id=peer_id, candidate_label=peer.answer,
            )
            completed.append(peer_run)
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend(tuple(completed)) from exc
        records = sorted((
            {"candidate_id": primary_id, "candidate_label": primary.answer,
             "argument": primary_run.result["argument"]},
            {"candidate_id": peer_id, "candidate_label": peer.answer,
             "argument": peer_run.result["argument"]},
        ), key=lambda item: item["candidate_id"])
        try:
            judge_run = self._execute(
                role_id=f"case-judge-{witness.model_id}-{item_id}",
                model_id=witness.model_id,
                task_kind="pilot_disagreement_adjudication",
                objective=(
                    "Judge the two anonymized candidate arguments against the public question. "
                    "Select a candidate only when its reasoning is decisively stronger; otherwise abstain."
                ),
                item_id=item_id,
                round_context={
                    "role": "blinded_disagreement_judge",
                    "candidate_records": records,
                    "independent_witness_label": witness.answer,
                    "candidate_order_randomized_before_judgment": True,
                },
                schema=judgment_schema(item_id), stage="JUDGE",
            )
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend(tuple(completed)) from exc
        try:
            validate_judgment(judge_run.result, item_id, list(self.base.harness.evidence_refs))
        except ValueError as exc:
            raise DisagreementCaseProviderFailure(
                stage="JUDGE", run=judge_run, failures=(str(exc),),
            ) from exc
        argument_hashes = (hash_payload(primary_run.result), hash_payload(peer_run.result))
        return DisagreementCaseBundle(
            item_id=item_id, primary_model_id=primary.model_id, peer_model_id=peer.model_id,
            judge_model_id=witness.model_id, primary_candidate_id=primary_id,
            peer_candidate_id=peer_id, primary_argument_run=primary_run,
            peer_argument_run=peer_run, judge_run=judge_run,
            argument_hashes=argument_hashes, judgment_hash=hash_payload(judge_run.result),
        )

    @staticmethod
    def _candidate_ids(item_id: str) -> tuple[str, str]:
        primary_first = int(sha256(item_id.encode("utf-8")).hexdigest(), 16) % 2 == 0
        return ("CANDIDATE_1", "CANDIDATE_2") if primary_first else ("CANDIDATE_2", "CANDIDATE_1")

    def _argument_run(self, *, item_id: str, model_id: str, candidate_id: str, candidate_label: str) -> RoleRun:
        run = self._execute(
            role_id=f"case-advocate-{model_id}-{item_id}", model_id=model_id,
            task_kind="pilot_disagreement_argument",
            objective=(
                "Independently justify the assigned candidate against the public question. "
                "Do not infer or discuss any competing candidate."
            ),
            item_id=item_id,
            round_context={
                "role": "isolated_candidate_advocate", "candidate_id": candidate_id,
                "candidate_label": candidate_label, "peer_output": "withheld",
            },
            schema=argument_schema(item_id, candidate_id), stage="ARGUMENT",
        )
        try:
            validate_argument(run.result, item_id, candidate_id, list(self.base.harness.evidence_refs))
        except ValueError as exc:
            raise DisagreementCaseProviderFailure(
                stage="ARGUMENT", run=run, failures=(str(exc),),
            ) from exc
        return run

    def _execute(
        self, *, role_id: str, model_id: str, task_kind: str, objective: str,
        item_id: str, round_context: dict[str, Any], schema: dict[str, Any], stage: str,
    ) -> RoleRun:
        adapter = self.base.small_adapters[model_id]
        task = ProviderCognitiveTask(
            task_id=role_id, task_kind=task_kind, objective=objective,
            inputs={
                "benchmark_public_input": self.base.harness.provider_inputs((item_id,)),
                "benchmark_item_ids": [item_id], "round_context": round_context,
            },
            allowed_evidence=list(self.base.harness.evidence_refs), expected_schema=schema,
            timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        )
        audit = self.base.harness.audit_provider_task(task)
        if audit.status != "PASS_HIDDEN_ANSWER_ABSENT":
            raise ValueError("disagreement_case_provider_input_audit_blocked")
        envelope = ProviderTaskRouter([adapter]).route(task)
        telemetry = self.base.telemetry_ledger.items(task_ids=(task.task_id,))
        if not telemetry:
            raise RuntimeError("disagreement_case_telemetry_missing")
        run = RoleRun(
            role_id=role_id, model_id=model_id, result=envelope.normalized_result,
            tasks=(task,), audits=(audit,), telemetry=telemetry,
        )
        if envelope.status != "COMPLETED" or not isinstance(envelope.normalized_result, dict):
            failed = RoleRun(
                role_id=role_id, model_id=model_id,
                result={"status": "FAILED", "validation_errors": list(envelope.validation_errors)},
                tasks=(task,), audits=(audit,), telemetry=telemetry,
            )
            raise DisagreementCaseProviderFailure(
                stage=stage, run=failed, failures=tuple(envelope.validation_errors),
            )
        return run
