"""Provider-backed arguments with Harness replay receipts and blinded judgment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .argument_evidence_contracts import argument_evidence_schema, validate_argument_evidence
from .argument_verification_receipt import MechanicalArgumentVerifier
from .disagreement_case_contracts import judgment_schema, validate_judgment
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .disagreement_case_runtime import DisagreementCaseRuntime
from .provider_telemetry import hash_payload


@dataclass(frozen=True)
class VerifiedCaseBundle:
    item_id: str
    primary_model_id: str
    peer_model_id: str
    judge_model_id: str
    primary_candidate_id: str
    peer_candidate_id: str
    primary_argument_run: Any
    peer_argument_run: Any
    judge_run: Any
    verification_receipts: tuple[Any, Any]
    argument_hashes: tuple[str, str]
    judgment_hash: str

    @property
    def judgment(self):
        return self.judge_run.result

    def as_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id, "primary_model_id": self.primary_model_id,
            "peer_model_id": self.peer_model_id, "judge_model_id": self.judge_model_id,
            "primary_candidate_id": self.primary_candidate_id,
            "peer_candidate_id": self.peer_candidate_id,
            "primary_argument": self.primary_argument_run.result,
            "peer_argument": self.peer_argument_run.result, "judgment": self.judgment,
            "verification_receipts": [item.as_dict() for item in self.verification_receipts],
            "argument_hashes": list(self.argument_hashes), "judgment_hash": self.judgment_hash,
            "provider_task_contract_hashes": [
                self.primary_argument_run.tasks[-1].contract_hash(),
                self.peer_argument_run.tasks[-1].contract_hash(), self.judge_run.tasks[-1].contract_hash(),
            ],
        }


class VerifiedDisagreementCaseRuntime(DisagreementCaseRuntime):
    judge_role = "blinded_verified_case_judge"

    def __init__(self, base) -> None:
        super().__init__(base)
        self.verifier = MechanicalArgumentVerifier(base.harness)

    def adjudicate(self, *, primary, peer, witness) -> VerifiedCaseBundle:
        if len({primary.model_id, peer.model_id, witness.model_id}) != 3 or not (
            primary.item_id == peer.item_id == witness.item_id
        ):
            raise ValueError("verified_case_identity_invalid")
        item_id = primary.item_id
        primary_id, peer_id = self._candidate_ids(item_id)
        completed = []
        try:
            primary_run = self._evidence_run(item_id, primary.model_id, primary_id, primary.answer)
            completed.append(primary_run)
            peer_run = self._evidence_run(item_id, peer.model_id, peer_id, peer.answer)
            completed.append(peer_run)
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend(tuple(completed)) from exc
        receipts = (
            self.verifier.verify(item_id=item_id, candidate_id=primary_id,
                                 candidate_label=primary.answer, argument=primary_run.result),
            self.verifier.verify(item_id=item_id, candidate_id=peer_id,
                                 candidate_label=peer.answer, argument=peer_run.result),
        )
        records = sorted((
            self._record(primary_id, primary.answer, primary_run.result, receipts[0]),
            self._record(peer_id, peer.answer, peer_run.result, receipts[1]),
        ), key=lambda item: item["candidate_id"])
        try:
            judge_run = self._execute(
                role_id=f"verified-case-judge-{witness.model_id}-{item_id}",
                model_id=witness.model_id, task_kind="pilot_disagreement_adjudication",
                objective=(
                    "Judge the anonymized arguments and Harness replay receipts. Select a candidate only "
                    "when its verified derivation and semantic reasoning are decisively stronger; otherwise abstain."
                ), item_id=item_id,
                round_context={"role": self.judge_role, "candidate_records": records,
                               "independent_witness_label": witness.answer,
                               "candidate_order_randomized_before_judgment": True},
                schema=judgment_schema(item_id), stage="JUDGE",
            )
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend(tuple(completed)) from exc
        try:
            validate_judgment(judge_run.result, item_id, list(self.base.harness.evidence_refs))
        except ValueError as exc:
            raise DisagreementCaseProviderFailure(
                stage="JUDGE", run=judge_run, failures=(str(exc),),
            ).prepend(tuple(completed)) from exc
        hashes = (hash_payload(primary_run.result), hash_payload(peer_run.result))
        return VerifiedCaseBundle(
            item_id=item_id, primary_model_id=primary.model_id, peer_model_id=peer.model_id,
            judge_model_id=witness.model_id, primary_candidate_id=primary_id,
            peer_candidate_id=peer_id, primary_argument_run=primary_run, peer_argument_run=peer_run,
            judge_run=judge_run, verification_receipts=receipts, argument_hashes=hashes,
            judgment_hash=hash_payload(judge_run.result),
        )

    def _evidence_run(self, item_id: str, model_id: str, candidate_id: str, candidate_label: str):
        run = self._execute(
            role_id=f"verified-case-advocate-{model_id}-{item_id}", model_id=model_id,
            task_kind="pilot_disagreement_argument",
            objective=(
                "Independently justify the assigned candidate. Supply one to four replayable facts. "
                "Each expression must use public problem values or a previous result and only +, -, *, /, %, "
                "SWAP_HALVES(text), or REVERSE_PAIRS(text). Do not discuss competing candidates."
            ), item_id=item_id,
            round_context={"role": "isolated_verified_candidate_advocate", "candidate_id": candidate_id,
                           "candidate_label": candidate_label, "peer_output": "withheld"},
            schema=argument_evidence_schema(item_id, candidate_id), stage="ARGUMENT",
        )
        try:
            validate_argument_evidence(
                run.result, item_id, candidate_id, list(self.base.harness.evidence_refs),
            )
        except ValueError as exc:
            raise DisagreementCaseProviderFailure(
                stage="ARGUMENT", run=run, failures=(str(exc),),
            ) from exc
        return run

    @staticmethod
    def _record(candidate_id, candidate_label, argument, receipt):
        return {
            "candidate_id": candidate_id, "candidate_label": candidate_label,
            "argument": argument["argument"], "derived_facts": argument["derived_facts"],
            "conclusion_value": argument["conclusion_value"],
            "verification_receipt": receipt.as_dict(),
        }
