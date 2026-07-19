import json
import subprocess
import sys
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from examples.problem_structure_admission_smoke import RETURN_PACK_NAME, run_smoke  # noqa: E402


def test_problem_structure_admission_smoke_and_artifacts(tmp_path):
    output_dir = tmp_path / "problem-structure-admission-smoke"
    result = run_smoke(output_dir)

    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    assert (output_dir / RETURN_PACK_NAME).is_file()
    audit_path = tmp_path / "problem-structure-admission-audit.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(CORE_ROOT / "examples" / "audit_release_artifacts.py"),
            "--artifact-dir",
            str(output_dir),
            "--output",
            str(audit_path),
        ],
        cwd=CORE_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["status"] == "PASS"
