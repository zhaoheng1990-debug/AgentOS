"""Build an anonymous Kimi-K3 pack from two returned lane responses."""

import argparse
import json
import sys
import zipfile
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v2_external_adjudication import (  # noqa: E402
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
    output = ROOT / "outputs" / "admission_v2_external_panel_v0_77"
    packs = (
        read(output / "gpt_5_6_typed_admission_pack_v0_77.json"),
        read(output / "gemini_3_1_typed_admission_pack_v0_77.json"),
    )
    inputs = {
        "packs": packs,
        "panel_manifest": read(
            output / "panel_manifest_private.json"
        ),
        "responses": (
            read(Path(args.gpt_response)),
            read(Path(args.gemini_response)),
        ),
    }
    pack, manifest = build_adjudication(**inputs)
    validate_adjudication(
        pack=pack,
        manifest=manifest,
        source_inputs=inputs,
    )
    pack_path = output / "kimi_k3_typed_admission_pack_v0_77.json"
    write(pack_path, pack)
    write(output / "adjudication_manifest_private.json", manifest)
    zip_path = output / "Kimi_K3_Admission_V2_Adjudication_v0_77.zip"
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.write(pack_path, arcname=pack_path.name)
    print(json.dumps({
        "agreement_count": manifest["agreement_count"],
        "disagreement_count": manifest["disagreement_count"],
        "reference_state": manifest["reference_state"],
        "kimi_zip": str(zip_path),
    }, indent=2))


if __name__ == "__main__":
    main()
