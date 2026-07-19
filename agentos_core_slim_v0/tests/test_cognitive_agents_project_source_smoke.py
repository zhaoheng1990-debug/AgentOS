import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.cognitive_agents_project_source_smoke import latest_receipts_by_stage


@dataclass(frozen=True)
class Receipt:
    stage: str
    status: str


def test_latest_receipts_by_stage_preserves_recovery_without_treating_old_block_as_final():
    receipts = (
        Receipt("GENERATION", "COMPLETED"),
        Receipt("REVIEW", "COMPLETED"),
        Receipt("REPLICATION", "COMPLETED"),
        Receipt("SYNTHESIS", "BLOCKED"),
        Receipt("SYNTHESIS", "COMPLETED"),
    )

    latest = latest_receipts_by_stage(receipts)

    assert latest["SYNTHESIS"].status == "COMPLETED"
    assert len(receipts) == 5
