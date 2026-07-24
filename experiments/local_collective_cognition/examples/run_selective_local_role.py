"""Run the local pragmatic role only for v0.18 admitted objects."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_selective_runtime import run_local_preference_roles  # noqa: E402
from local_collective_cognition.local_transformers_provider import LocalTransformersModelSpec  # noqa: E402
from local_collective_cognition.staged_semantic_role_adapter import StagedSemanticResidentPool, StagedSemanticRoleAdapter  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "selective_escalation_v0_18"))
    parser.add_argument("--model-id", default="llama-3.2-1b-instruct")
    parser.add_argument("--model-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    args = parser.parse_args()
    output = Path(args.output_dir)
    corpus = read(output / "selective_fresh_corpus_frozen.json")
    plan = read(output / "selective_admission_plan.json")
    if not plan["admitted_conflict_ids"]:
        run = run_local_preference_roles(
            corpus=corpus,
            admission_plan=plan,
            adapter=None,
        )
    else:
        pool = StagedSemanticResidentPool((LocalTransformersModelSpec(args.model_id, args.model_path),))
        try:
            pool.load_all()
            run = run_local_preference_roles(
                corpus=corpus,
                admission_plan=plan,
                adapter=StagedSemanticRoleAdapter(model_id=args.model_id, pool=pool),
            )
        finally:
            pool.unload_all()
    write(output / "selective_local_role_run.json", run)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "requested_count": run["requested_count"],
        "output_count": len(run["outputs"]),
        "failure_count": len(run["failures"]),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
