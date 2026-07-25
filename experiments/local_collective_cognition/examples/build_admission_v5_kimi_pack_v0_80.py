"""Validate GPT/Gemini responses and build anonymous Kimi pack."""

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v5_external_adjudication import (  # noqa: E402
    build_adjudication,
    validate_adjudication,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpt-response", required=True)
    parser.add_argument("--gemini-response", required=True)
    args = parser.parse_args()
    output = ROOT / "outputs" / "admission_v5_external_panel_v0_80"
    packs = (
        read(output / "gpt_5_6_atomic_admission_pack_v0_80.json"),
        read(output / "gemini_3_1_atomic_admission_pack_v0_80.json"),
    )
    responses = (
        read(Path(args.gpt_response)),
        read(Path(args.gemini_response)),
    )
    manifest = read(output / "panel_manifest_private.json")
    pack, adjudication_manifest = build_adjudication(
        packs=packs,
        panel_manifest=manifest,
        responses=responses,
    )
    validate_adjudication(
        pack=pack,
        manifest=adjudication_manifest,
    )
    pack_path = output / "kimi_k3_atomic_admission_pack_v0_80.json"
    write(pack_path, pack)
    write(
        output / "adjudication_manifest_private.json",
        adjudication_manifest,
    )
    raw = output / "raw_received"
    raw.mkdir(exist_ok=True)
    shutil.copyfile(
        args.gpt_response,
        raw / "ANNOTATION_LANE_A_GPT5_6_response.json",
    )
    shutil.copyfile(
        args.gemini_response,
        raw / "ANNOTATION_LANE_B_Gemini3_1_response.json",
    )
    zip_path = output / "Kimi_K3_Atomic_Admission_Adjudication_v0_80.zip"
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.write(pack_path, arcname=pack_path.name)
    print(json.dumps({
        "agreement_count": adjudication_manifest["agreement_count"],
        "disagreement_count": adjudication_manifest["disagreement_count"],
        "reference_state": adjudication_manifest["reference_state"],
        "kimi_zip": str(zip_path),
        "kimi_zip_sha256": hashlib.sha256(
            zip_path.read_bytes()
        ).hexdigest(),
    }, indent=2))


if __name__ == "__main__":
    main()
