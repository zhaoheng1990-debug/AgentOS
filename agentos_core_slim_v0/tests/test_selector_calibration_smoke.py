import json
import sys
import zipfile
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from examples.selector_calibration_drift_smoke import run_smoke  # noqa: E402


def test_selector_calibration_smoke_closes_return_pack(tmp_path):
    result = run_smoke(tmp_path)
    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    assert Path(result["manifest_path"]).exists()
    assert Path(result["return_pack"]).exists()
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    expected = {item["path"] for item in manifest["files"]} | {"manifest.json"}
    with zipfile.ZipFile(result["return_pack"]) as archive:
        assert set(archive.namelist()) == expected
