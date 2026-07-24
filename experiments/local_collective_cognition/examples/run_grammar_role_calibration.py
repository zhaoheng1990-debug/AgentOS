"""Run v0.16 grammar-backed calibration on the burned v0.15 panel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_reference_first_roles import MODEL_IDS  # noqa: E402
from local_collective_cognition.grammar_backed_role_adapter import GrammarBackedResidentPool, GrammarBackedRoleAdapter  # noqa: E402
from local_collective_cognition.grammar_role_calibration import analyze_grammar_calibration, render_grammar_calibration_analysis, run_grammar_calibration  # noqa: E402
from local_collective_cognition.local_transformers_provider import LocalTransformersModelSpec  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default=str(REPO_ROOT / "outputs" / "clarification_reference_first_v0_15"))
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "cognitive_action_overnight_v0_16"))
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--llama-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    args = parser.parse_args()
    source, output = Path(args.source_dir), Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    corpus = read(source / "private_reference_first_corpus.json")
    reference = read(source / "reference_first_model_panel_reference_candidate.json")
    role_plan = read(source / "local_specialist_role_plan.json")
    paths = dict(zip(MODEL_IDS, (args.qwen_path, args.gemma_path, args.llama_path)))
    specs = tuple(LocalTransformersModelSpec(model, paths[model]) for model in MODEL_IDS)
    pool = GrammarBackedResidentPool(specs)
    try:
        pool.load_all()
        run = run_grammar_calibration(
            corpus=corpus,
            reference=reference,
            role_plan=role_plan,
            adapters=tuple(GrammarBackedRoleAdapter(model_id=model, pool=pool) for model in MODEL_IDS),
        )
    finally:
        pool.unload_all()
    analysis = analyze_grammar_calibration(corpus=corpus, reference=reference, role_plan=role_plan, run=run)
    write(output / "grammar_calibration_run.json", run)
    write(output / "grammar_calibration_analysis.json", analysis)
    (output / "GRAMMAR_CALIBRATION_ANALYSIS.md").write_text(render_grammar_calibration_analysis(analysis), encoding="utf-8")
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "coverage": analysis["overall_coverage"],
        "role_metrics": analysis["role_metrics"],
        "routing": analysis["selected_bijective_routing"],
        "accounting": analysis["accounting"],
        "fresh_blind_collection_allowed": analysis["fresh_blind_collection_allowed"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

