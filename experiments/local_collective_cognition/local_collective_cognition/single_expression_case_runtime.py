"""Low-friction single-expression advocate runtime for protocol v0.16."""

from __future__ import annotations

from .disagreement_case_failure import DisagreementCaseProviderFailure
from .single_expression_contracts import single_expression_schema, validate_single_expression
from .single_expression_receipt import SingleExpressionVerifier
from .verified_case_runtime import VerifiedDisagreementCaseRuntime


class SingleExpressionCaseRuntime(VerifiedDisagreementCaseRuntime):
    def __init__(self, base) -> None:
        super().__init__(base)
        self.verifier = SingleExpressionVerifier(base.harness)

    def _evidence_run(self, item_id: str, model_id: str, candidate_id: str, candidate_label: str):
        run = self._execute(
            role_id=f"single-expression-advocate-{model_id}-{item_id}", model_id=model_id,
            task_kind="pilot_disagreement_argument",
            objective=(
                "Return one expression that derives the assigned candidate from public problem values. "
                "Use only +, -, *, /, %, SWAP_HALVES(text), REVERSE_PAIRS(text), and nesting. "
                "Do not return prose, intermediate facts, a competing candidate, or an answer key."
            ), item_id=item_id,
            round_context={"role": "isolated_single_expression_advocate",
                           "candidate_id": candidate_id, "candidate_label": candidate_label,
                           "peer_output": "withheld"},
            schema=single_expression_schema(item_id, candidate_id), stage="ARGUMENT",
        )
        try:
            validate_single_expression(
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
            "expression": argument["expression"],
            "verification_receipt": receipt.as_dict(),
        }
