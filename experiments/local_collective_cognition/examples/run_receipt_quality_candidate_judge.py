"""Freeze DeepSeek receipt-quality predictions before panel labels return."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.receipt_quality_calibration_corpus import (  # noqa: E402
    validate_receipt_quality_corpus_artifact,
)
from local_collective_cognition.receipt_quality_candidate_runtime import (  # noqa: E402
    ReceiptQualityCandidateRuntime,
    validate_receipt_quality_candidate_run,
)
from local_collective_cognition.structure_semantic_judge_contracts import (  # noqa: E402
    JUDGE_TASK_KIND,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/receipt_quality_calibration_v0_1"
    parser.add_argument(
        "--corpus", default=f"{base}/private_receipt_quality_corpus.json",
    )
    parser.add_argument(
        "--output", default=f"{base}/deepseek_receipt_quality_candidate_run.json",
    )
    args = parser.parse_args()
    corpus = _load(args.corpus)
    validate_receipt_quality_corpus_artifact(corpus)
    adapter = OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        "deepseek",
        "deepseek-v4-flash",
        "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY",
        (JUDGE_TASK_KIND,),
        max_tokens=2200,
        timeout_seconds=180,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    ))
    experiment_id = "receipt-quality-candidate-" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    run = ReceiptQualityCandidateRuntime(corpus_artifact=corpus).evaluate(
        experiment_id=experiment_id, adapter=adapter,
    )
    validate_receipt_quality_candidate_run(run, corpus_artifact=corpus)
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "judge_run_hash": run["judge_run_hash"],
        "source_artifact_hash": run["source_artifact_hash"],
        "successful_batches": run["successful_batches"],
        "failed_batches": run["failed_batches"],
        "total_provider_calls": run["total_provider_calls"],
        "total_tokens": run["total_input_tokens"] + run["total_output_tokens"],
        "panel_labels_available_at_prediction_time": (
            run["panel_labels_available_at_prediction_time"]
        ),
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
