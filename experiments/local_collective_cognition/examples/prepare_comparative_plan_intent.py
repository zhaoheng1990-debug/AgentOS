"""Freeze v0.31 comparative plan-intent experiment."""
from __future__ import annotations
import json, sys
from pathlib import Path
PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]
from local_collective_cognition.comparative_plan_intent_experiment import build_plan_intent_preregistration  # noqa: E402
from local_collective_cognition.comparative_plan_intent_holdout import build_comparative_plan_intent_holdout  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p, v): Path(p).write_text(json.dumps(v, indent=2, sort_keys=True), encoding="utf-8")
def verify(v):
    if v["artifact_hash"] != hash_payload({k: x for k, x in v.items() if k != "artifact_hash"}):
        raise ValueError("source_hash_invalid")
def main():
    src = REPO_ROOT / "outputs" / "selective_role_routing_v0_30"
    analysis = read(src / "selective_role_routing_analysis.json")
    posthoc = read(src / "posthoc_cost_route_decomposition.json")
    ledger, closure = read(src / "ledger.json"), read(src / "closure.json")
    for value in (analysis, posthoc, ledger, closure): verify(value)
    if ledger["source_analysis_hash"] != analysis["artifact_hash"] or closure["source_ledger_hash"] != ledger["artifact_hash"]:
        raise ValueError("source_chain_invalid")
    corpus = build_comparative_plan_intent_holdout()
    prereg = build_plan_intent_preregistration(
        corpus=corpus, prior_analysis=analysis,
        prior_closure=closure, prior_posthoc=posthoc,
    )
    out = REPO_ROOT / "outputs" / "comparative_plan_intent_v0_31"
    out.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("source_v0_30_analysis.json", analysis),
        ("source_v0_30_posthoc.json", posthoc),
        ("source_v0_30_closure.json", closure),
        ("comparative_plan_intent_corpus_frozen.json", corpus),
        ("comparative_plan_intent_preregistration.json", prereg),
    ): write(out / name, value)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": prereg["artifact_hash"],
        "case_count": corpus["case_count"], "task_call_count": 48,
        "soft_tokens": prereg["cost_policy"]["soft_expected_total_tokens"],
        "hard_tokens": prereg["cost_policy"]["hard_runaway_total_tokens"],
    }, indent=2, sort_keys=True))
if __name__ == "__main__": raise SystemExit(main())
