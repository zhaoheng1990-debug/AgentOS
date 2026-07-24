"""Run all pre-label v0.2 generalization arms."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.negative_evidence_audit_contracts import (  # noqa: E402
    FABRICATION_AUDIT,
    LIVE_AMBIGUITY_AUDIT,
    TASK_KINDS,
)
from local_collective_cognition.negative_evidence_generalization_fusion import (  # noqa: E402
    BASELINE,
    HETEROGENEOUS_LIVE,
    MONOLITHIC_REPEAT_2,
    MONOLITHIC_REPEAT_3,
    SAME_MODEL_LIVE,
    SHARED_FABRICATION,
)
from local_collective_cognition.negative_evidence_generalization_holdout import (  # noqa: E402
    validate_generalization_corpus_artifact,
)
from local_collective_cognition.negative_evidence_generalization_runtime import (  # noqa: E402
    NegativeEvidenceGeneralizationRuntime,
    validate_generalization_candidate_run,
)
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.structure_semantic_judge_contracts import (  # noqa: E402
    JUDGE_TASK_KIND,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _deepseek(provider_id, task_kind, max_tokens):
    return OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        provider_id, "deepseek-v4-flash",
        "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY",
        (task_kind,), max_tokens=max_tokens, timeout_seconds=240,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    ))


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_generalization_v0_2"
    parser.add_argument(
        "--corpus", default=f"{base}/private_negative_generalization_corpus.json",
    )
    parser.add_argument(
        "--output", default=f"{base}/four_arm_candidate_run.json",
    )
    args = parser.parse_args()
    corpus = json.loads(_resolve(args.corpus).read_text(encoding="utf-8"))
    validate_generalization_corpus_artifact(corpus)
    adapters = {
        BASELINE: _deepseek("deepseek-generalization-baseline", JUDGE_TASK_KIND, 2600),
        MONOLITHIC_REPEAT_2: _deepseek(
            "deepseek-generalization-monolithic-r2", JUDGE_TASK_KIND, 2600,
        ),
        MONOLITHIC_REPEAT_3: _deepseek(
            "deepseek-generalization-monolithic-r3", JUDGE_TASK_KIND, 2600,
        ),
        SAME_MODEL_LIVE: _deepseek(
            "deepseek-generalization-live", TASK_KINDS[LIVE_AMBIGUITY_AUDIT], 1800,
        ),
        SHARED_FABRICATION: _deepseek(
            "deepseek-generalization-fabrication",
            TASK_KINDS[FABRICATION_AUDIT], 1800,
        ),
        HETEROGENEOUS_LIVE: OpenAICompatibleJsonAdapter(
            OpenAICompatibleProviderSpec(
                "moonshot-generalization-live", "kimi-k2.5",
                "https://api.moonshot.cn/v1/chat/completions", "MOONSHOT_API_KEY",
                (TASK_KINDS[LIVE_AMBIGUITY_AUDIT],), max_tokens=1800,
                timeout_seconds=240,
            )
        ),
    }
    experiment_id = "negative-generalization-" + datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")
    run = NegativeEvidenceGeneralizationRuntime(
        corpus_artifact=corpus,
    ).evaluate(experiment_id=experiment_id, adapters=adapters)
    validate_generalization_candidate_run(run, corpus_artifact=corpus)
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    records = run["fusion"]["records"]
    print(json.dumps({
        "candidate_run_hash": run["candidate_run_hash"],
        "source_artifact_hash": run["source_artifact_hash"],
        "total_unique_provider_calls": run["total_unique_provider_calls"],
        "total_unique_tokens": (
            run["total_unique_input_tokens"] + run["total_unique_output_tokens"]
        ),
        "lane_successes": {
            lane: len(value["judgments"]) for lane, value in run["lanes"].items()
        },
        "lane_failures": {
            lane: len(value["failures"]) for lane, value in run["lanes"].items()
        },
        "arm_states": {
            "SINGLE_MONOLITHIC": dict(Counter(
                item["single_monolithic_state"] for item in records
            )),
            "BUDGET_MATCHED_MONOLITHIC": dict(Counter(
                item["budget_matched_monolithic_state"] for item in records
            )),
            "SAME_MODEL_SPLIT": dict(Counter(
                item["same_model_split_state"] for item in records
            )),
            "HETEROGENEOUS_SPLIT": dict(Counter(
                item["heterogeneous_split_state"] for item in records
            )),
        },
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
