"""Collect the frozen v0.17 local role receipts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_reference_first_roles import MODEL_IDS  # noqa: E402
from local_collective_cognition.cognitive_action_axis_routing import analyze_axis_roles, run_axis_roles  # noqa: E402
from local_collective_cognition.local_transformers_provider import LocalTransformersModelSpec  # noqa: E402
from local_collective_cognition.staged_semantic_role_adapter import StagedSemanticResidentPool, StagedSemanticRoleAdapter  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "axis_credibility_routing_v0_17"))
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--llama-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    args = parser.parse_args()
    output = Path(args.output_dir)
    corpus = read(output / "axis_fresh_corpus_frozen.json")
    plan = read(output / "axis_role_plan.json")
    paths = dict(zip(MODEL_IDS, (args.qwen_path, args.gemma_path, args.llama_path)))
    pool = StagedSemanticResidentPool(tuple(LocalTransformersModelSpec(model, paths[model]) for model in MODEL_IDS))
    try:
        pool.load_all()
        run = run_axis_roles(
            corpus=corpus,
            plan=plan,
            adapters=tuple(StagedSemanticRoleAdapter(model_id=model, pool=pool) for model in MODEL_IDS),
        )
    finally:
        pool.unload_all()
    analysis = analyze_axis_roles(corpus=corpus, plan=plan, run=run)
    write(output / "axis_role_run.json", run)
    write(output / "axis_role_analysis.json", analysis)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "coverage": analysis["strict_receipt_coverage"],
        "tuple_inference_allowed": analysis["tuple_inference_allowed"],
        "accounting": analysis["accounting"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())

