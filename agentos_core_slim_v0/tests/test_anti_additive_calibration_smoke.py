import sys
import zipfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.anti_additive_calibration_smoke import RETURN_PACK_NAME, run_smoke  # noqa: E402


def test_anti_additive_calibration_smoke_closes_authority_and_artifact_surface(tmp_path):
    result = run_smoke(tmp_path / "aa-calibration-smoke")
    output = Path(result["output_dir"])
    pack = output / RETURN_PACK_NAME
    expected = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file() and path != pack
    }
    with zipfile.ZipFile(pack) as archive:
        actual = set(archive.namelist())
        bad_member = archive.testzip()

    assert result["status"] == "PASS"
    assert result["manifest_file_count"] == len(expected) - 1
    assert actual == expected
    assert bad_member is None
