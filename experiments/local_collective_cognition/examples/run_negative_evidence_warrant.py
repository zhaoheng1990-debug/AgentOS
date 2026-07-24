"""Run frozen pre-reference v0.5 arms."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter
from local_collective_cognition.negative_evidence_audit_contracts import FABRICATION_AUDIT, LIVE_AMBIGUITY_AUDIT, TASK_KINDS
from local_collective_cognition.negative_evidence_warrant_contracts import WARRANT_TASK_KIND
from local_collective_cognition.negative_evidence_warrant_fusion import BASELINE, FABRICATION, LEGACY_LIVE, MONOLITHIC_REPEAT_2, MONOLITHIC_REPEAT_3, WARRANT_LIVE
from local_collective_cognition.negative_evidence_warrant_holdout import validate_warrant_corpus_artifact
from local_collective_cognition.negative_evidence_warrant_runtime import NegativeEvidenceWarrantRuntime, RECOVERY_RUNTIME_VERSION, validate_warrant_candidate_run
from local_collective_cognition.openai_compatible_provider import OpenAICompatibleJsonAdapter, OpenAICompatibleProviderSpec
from local_collective_cognition.structure_semantic_judge_contracts import JUDGE_TASK_KIND


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def deepseek(provider_id, task_kind, max_tokens):
    adapter = OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        provider_id,
        "deepseek-v4-flash",
        "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY",
        (task_kind,),
        max_tokens=max_tokens,
        timeout_seconds=240,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    ))
    return BoundedRetryProviderAdapter(adapter, max_attempts=2)


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_warrant_v0_5_1"
    parser.add_argument("--corpus", default=f"{base}/private_negative_warrant_corpus.json")
    parser.add_argument("--output", default=f"{base}/candidate_run.json")
    args = parser.parse_args()
    corpus = json.loads(resolve(args.corpus).read_text(encoding="utf-8"))
    validate_warrant_corpus_artifact(corpus)
    adapters = {
        BASELINE: deepseek("deepseek-warrant-baseline", JUDGE_TASK_KIND, 2600),
        MONOLITHIC_REPEAT_2: deepseek("deepseek-warrant-mono-r2", JUDGE_TASK_KIND, 2600),
        MONOLITHIC_REPEAT_3: deepseek("deepseek-warrant-mono-r3", JUDGE_TASK_KIND, 2600),
        LEGACY_LIVE: deepseek("deepseek-warrant-legacy-live", TASK_KINDS[LIVE_AMBIGUITY_AUDIT], 1800),
        WARRANT_LIVE: deepseek("deepseek-warrant-execution-live", WARRANT_TASK_KIND, 2200),
        FABRICATION: deepseek("deepseek-warrant-fabrication", TASK_KINDS[FABRICATION_AUDIT], 1800),
    }
    run = NegativeEvidenceWarrantRuntime(corpus_artifact=corpus, runtime_version=RECOVERY_RUNTIME_VERSION).evaluate(
        experiment_id="negative-warrant-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        adapters=adapters,
    )
    validate_warrant_candidate_run(run, corpus_artifact=corpus)
    output = resolve(args.output)
    output.write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    records = run["fusion"]["records"]
    state_keys = {
        "SINGLE": "single_monolithic_state",
        "BUDGET": "budget_matched_monolithic_state",
        "NAIVE": "naive_replication_state",
        "WARRANTED": "warranted_veto_state",
    }
    print(json.dumps({
        "candidate_run_hash": run["candidate_run_hash"],
        "calls": run["total_unique_provider_calls"],
        "tokens": run["total_unique_input_tokens"] + run["total_unique_output_tokens"],
        "successes": {key: len(value["judgments"]) for key, value in run["lanes"].items()},
        "failures": {key: len(value["failures"]) for key, value in run["lanes"].items()},
        "states": {key: dict(Counter(item[value] for item in records)) for key, value in state_keys.items()},
        "warrant_kinds": dict(Counter(item["warrant_kind"] for item in records)),
        "runtime_warrant_states": dict(Counter(item["runtime_warrant_state"] for item in records)),
        "accounting": run["fusion"]["arm_accounting"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
