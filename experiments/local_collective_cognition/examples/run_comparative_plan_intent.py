"""Run v0.31 comparative plan-intent experiment."""
from __future__ import annotations
import json, sys
from pathlib import Path
PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]
from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter  # noqa: E402
from local_collective_cognition.comparative_plan_intent_experiment import analyze_plan_intent_experiment, run_plan_intent_experiment  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.openai_compatible_provider import OpenAICompatibleJsonAdapter, OpenAICompatibleProviderSpec  # noqa: E402
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p, v): Path(p).write_text(json.dumps(v, indent=2, sort_keys=True), encoding="utf-8")
def main():
    out = REPO_ROOT / "outputs" / "comparative_plan_intent_v0_31"
    corpus = read(out / "comparative_plan_intent_corpus_frozen.json")
    prereg = read(out / "comparative_plan_intent_preregistration.json")
    adapter = BoundedRetryProviderAdapter(OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        provider_id="deepseek-comparative-plan-intent-v0-31",
        model_id="deepseek-v4-flash", endpoint="https://api.deepseek.com/chat/completions",
        api_key_env="DEEPSEEK_API_KEY", task_kinds=(TASK_KIND,),
        max_tokens=3000, timeout_seconds=300,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    )), max_attempts=2, delay_seconds=1.0)
    run = run_plan_intent_experiment(
        corpus=corpus, preregistration=prereg, adapter=adapter,
        checkpoint_callback=lambda value: write(out / "comparative_plan_intent_progress.json", value),
    )
    analysis = analyze_plan_intent_experiment(corpus=corpus, preregistration=prereg, run=run)
    write(out / "comparative_plan_intent_run.json", run)
    write(out / "comparative_plan_intent_analysis.json", analysis)
    print(json.dumps({
        "decision": analysis["decision"], "state": analysis["candidate_state"],
        "metrics": analysis["pooled_contrast_metrics"],
        "plans": analysis["plan_metrics"], "conditions": analysis["conditions"],
        "tokens": analysis["total_tokens"],
    }, indent=2, sort_keys=True))
if __name__ == "__main__": raise SystemExit(main())
