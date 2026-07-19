import json
import sys
import zipfile
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from examples.contextual_policy_calibration_control_smoke import run_smoke  # noqa: E402


def test_contextual_policy_calibration_control_smoke(tmp_path):
    result = run_smoke(tmp_path)
    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {item["path"] for item in manifest["files"]} | {"manifest.json"}
    with zipfile.ZipFile(result["return_pack"]) as archive:
        assert set(archive.namelist()) == expected
