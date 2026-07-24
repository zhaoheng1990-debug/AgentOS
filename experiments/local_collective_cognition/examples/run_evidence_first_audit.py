"""Run the v0.54 dual-role reference completeness audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import (  # noqa: E402
    BoundedRetryProviderAdapter,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.reference_completeness_audit import (  # noqa: E402
    run_reference_completeness_audit,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "evidence_first_v0_54"
    corpus = read(output / "evidence_first_corpus_frozen.json")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-reference-audit-v0-54",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=3000,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )
    audit = run_reference_completeness_audit(
        corpus=corpus, adapter=adapter
    )
    write(output / "reference_completeness_audit.json", audit)
    print(json.dumps({
        "reference_complete": audit["reference_complete"],
        "valid_receipts": audit["valid_receipt_count"],
        "required_receipts": audit["required_receipt_count"],
        "contract_failures": len(audit["contract_failures"]),
        "reference_mismatches": len(audit["reference_mismatches"]),
        "cross_role_disagreements": len(
            audit["cross_role_disagreements"]
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
