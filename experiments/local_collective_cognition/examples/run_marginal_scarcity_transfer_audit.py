"""Run the v0.59 dual-role exhaustive reference audit."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter  # noqa: E402
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


def main():
    revision = os.environ.get("AGENTOS_TRANSFER_REVISION", "v0_59")
    if revision not in {"v0_59", "v0_59_1"}:
        raise ValueError("transfer_revision_invalid")
    output = (
        REPO_ROOT / "outputs" / f"marginal_scarcity_transfer_{revision}"
    )
    corpus = read(output / "transfer_corpus_frozen.json")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-scarcity-transfer-reference-v0-59",
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
    (output / "reference_completeness_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({
        "revision": revision,
        "reference_complete": audit["reference_complete"],
        "valid": audit["valid_receipt_count"],
        "required": audit["required_receipt_count"],
        "mismatches": len(audit["reference_mismatches"]),
        "disagreements": len(audit["cross_role_disagreements"]),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
