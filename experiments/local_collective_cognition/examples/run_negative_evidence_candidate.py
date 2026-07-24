"""Freeze baseline and split-auditor DeepSeek predictions before labels return."""

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
from local_collective_cognition.negative_evidence_candidate_runtime import (  # noqa: E402
    NegativeEvidenceCandidateRuntime,
    validate_negative_evidence_candidate_run,
)
from local_collective_cognition.negative_evidence_holdout import (  # noqa: E402
    validate_negative_evidence_corpus_artifact,
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


def _adapter(provider_id, task_kind, max_tokens):
    return OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        provider_id,
        "deepseek-v4-flash",
        "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY",
        (task_kind,),
        max_tokens=max_tokens,
        timeout_seconds=180,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    ))


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_split_v0_1"
    parser.add_argument(
        "--corpus", default=f"{base}/private_negative_evidence_corpus.json",
    )
    parser.add_argument(
        "--output", default=f"{base}/deepseek_negative_evidence_candidate_run.json",
    )
    args = parser.parse_args()
    corpus = json.loads(_resolve(args.corpus).read_text(encoding="utf-8"))
    validate_negative_evidence_corpus_artifact(corpus)
    runtime = NegativeEvidenceCandidateRuntime(corpus_artifact=corpus)
    experiment_id = "negative-evidence-candidate-" + datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")
    run = runtime.evaluate(
        experiment_id=experiment_id,
        baseline_adapter=_adapter(
            "deepseek-negative-evidence-baseline", JUDGE_TASK_KIND, 2600,
        ),
        live_adapter=_adapter(
            "deepseek-live-ambiguity-auditor",
            TASK_KINDS[LIVE_AMBIGUITY_AUDIT], 1800,
        ),
        fabrication_adapter=_adapter(
            "deepseek-fabrication-auditor",
            TASK_KINDS[FABRICATION_AUDIT], 1800,
        ),
    )
    validate_negative_evidence_candidate_run(run, corpus_artifact=corpus)
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "candidate_run_hash": run["candidate_run_hash"],
        "source_artifact_hash": run["source_artifact_hash"],
        "total_provider_calls": run["total_provider_calls"],
        "total_tokens": run["total_input_tokens"] + run["total_output_tokens"],
        "lane_successes": {
            lane: len(record["judgments"])
            for lane, record in run["lanes"].items()
        },
        "lane_failures": {
            lane: len(record["failures"])
            for lane, record in run["lanes"].items()
        },
        "baseline_states": dict(Counter(
            item["baseline_packet_state"] for item in run["fusion"]["records"]
        )),
        "fused_states": dict(Counter(
            item["fused_packet_state"] for item in run["fusion"]["records"]
        )),
        "panel_labels_available_at_prediction_time": False,
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
