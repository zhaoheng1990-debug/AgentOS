import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    REPO_ROOT
    / "research/theory_first_reset"
    / "R4_TRANSFORMATION_SEMANTICS_FACTORIZATION_VALIDATION_MANIFEST_V0_3I.json"
)
MODULE_ROOT = (
    REPO_ROOT
    / "experiments/theory_first_r4_relation/theory_first_r4_relation"
)
TEST_ROOT = REPO_ROOT / "experiments/theory_first_r4_relation/tests"


def test_factorization_validation_manifest_matches_frozen_files() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, expected_hash in manifest["implementation_files"].items():
        root = TEST_ROOT if name.startswith("test_") else MODULE_ROOT
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected_hash
