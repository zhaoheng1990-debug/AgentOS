"""Freeze a new holdout and collect routed local role receipts before external labels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_reference_first_roles import MODEL_IDS  # noqa: E402
from local_collective_cognition.cognitive_action_fresh_holdout import build_fresh_action_holdout, validate_fresh_action_holdout  # noqa: E402
from local_collective_cognition.cognitive_action_fresh_runtime import analyze_fresh_roles, build_external_annotation_pack, build_fresh_role_plan, run_fresh_roles  # noqa: E402
from local_collective_cognition.local_transformers_provider import LocalTransformersModelSpec  # noqa: E402
from local_collective_cognition.staged_semantic_role_adapter import StagedSemanticResidentPool, StagedSemanticRoleAdapter  # noqa: E402


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "cognitive_action_overnight_v0_16"))
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--llama-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    calibration = json.loads((output / "staged_semantic_analysis.json").read_text(encoding="utf-8"))
    corpus = build_fresh_action_holdout()
    validate_fresh_action_holdout(corpus)
    write(output / "fresh_action_corpus_frozen.json", corpus)
    plan = build_fresh_role_plan(corpus=corpus, calibration_analysis=calibration)
    write(output / "fresh_action_role_plan.json", plan)
    paths = dict(zip(MODEL_IDS, (args.qwen_path, args.gemma_path, args.llama_path)))
    specs = tuple(LocalTransformersModelSpec(model, paths[model]) for model in MODEL_IDS)
    pool = StagedSemanticResidentPool(specs)
    try:
        pool.load_all()
        run = run_fresh_roles(corpus=corpus, plan=plan, adapters=tuple(StagedSemanticRoleAdapter(model_id=model, pool=pool) for model in MODEL_IDS))
    finally:
        pool.unload_all()
    analysis = analyze_fresh_roles(corpus=corpus, plan=plan, run=run)
    annotation_pack = build_external_annotation_pack(corpus=corpus, role_run=run)
    write(output / "fresh_action_role_run.json", run)
    write(output / "fresh_action_role_analysis.json", analysis)
    write(output / "fresh_action_external_annotation_pack.json", annotation_pack)
    print(json.dumps({"corpus_hash": corpus["artifact_hash"], "plan_hash": plan["plan_hash"], "run_hash": run["run_hash"], "analysis_hash": analysis["artifact_hash"], "coverage": analysis["strict_receipt_coverage"], "coordinator_run_allowed": analysis["coordinator_run_allowed"], "annotation_pack_hash": annotation_pack["pack_hash"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

