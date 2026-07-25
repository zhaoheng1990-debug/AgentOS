"""Finalize the v0.84 typed reference after Kimi adjudication."""

import argparse
import json
import shutil
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v9_external_adjudication import (  # noqa: E402
    build_typed_reference,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kimi-response", required=True)
    args = parser.parse_args()
    output = ROOT / "outputs" / "admission_v9_external_panel_v0_84"
    response_path = Path(args.kimi_response)
    response = read(response_path)
    reference = build_typed_reference(
        panel_manifest=read(output / "panel_manifest_private.json"),
        adjudication_pack=read(
            output / "kimi_k3_ternary_boundary_pack_v0_84.json"
        ),
        adjudication_manifest=read(
            output / "adjudication_manifest_private.json"
        ),
        adjudication_response=response,
    )
    path = output / "typed_admission_reference_candidate_v0_84.json"
    path.write_text(
        json.dumps(reference, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    raw = output / "raw_received"
    raw.mkdir(exist_ok=True)
    shutil.copyfile(
        response_path,
        raw / "KIMI_K3_adjudication_response.json",
    )
    print(json.dumps({
        "reference_status": reference["reference_status"],
        "label_count": reference["label_count"],
        "artifact_hash": reference["artifact_hash"],
        "output": str(path),
    }, indent=2))


if __name__ == "__main__":
    main()
