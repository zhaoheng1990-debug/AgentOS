import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.organization_cross_project_attribution_smoke import COMPONENTS, run_audit


def feedback(context_key, effectiveness):
    components = []
    hypotheses = []
    for component_id, value in zip(COMPONENTS, effectiveness, strict=True):
        direction = "BENEFICIAL" if value > 0 else "HARMFUL" if value < 0 else "UNCERTAIN"
        components.append(
            {
                "component_id": component_id,
                "identifiability": "IDENTIFIED_MATCHED_ABLATION",
                "matched_pair_count": 2,
                "mean_effectiveness_contribution": value,
                "mean_cbit_contribution": 0.1,
                "mean_cost_contribution": 0.2,
            }
        )
        hypotheses.append(
            {
                "component_id": component_id,
                "causal_status": "IDENTIFIED_MATCHED_ABLATION",
                "direction": direction,
            }
        )
    return {
        "status": "PASS",
        "context_key": context_key,
        "evidence_tier": "LIVE_PROJECT",
        "source_bundle_count": 2,
        "record_count": 10,
        "gates": {"identified": True, "replay": True},
        "diagnosis": {
            "attribution": {"components": components},
            "component_hypotheses": hypotheses,
        },
    }


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_cross_project_audit_preserves_context_and_blocks_pooled_effects(tmp_path):
    life = write(tmp_path / "life.json", feedback("context://life", (0.1, 0.2, 0.3, 0.4)))
    math = write(tmp_path / "math.json", feedback("context://math", (-0.1, 0.2, -0.3, 0.4)))

    result = run_audit((life, math), tmp_path / "audit")
    transfer = {item["component_id"]: item for item in result["component_transfer"]}

    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    assert transfer["COORDINATOR"]["transfer_status"] == "CONTEXT_DEPENDENT"
    assert transfer["ADVERSARIAL_REVIEWER"]["transfer_status"] == (
        "DIRECTION_CONSISTENT_ACROSS_OBSERVED_CONTEXTS"
    )
    assert all(item["candidate_state"] == "CANDIDATE_ONLY" for item in transfer.values())
    assert "pooled_effect" not in json.dumps(result)
    assert (tmp_path / "audit" / "manifest.json").is_file()
    assert (
        tmp_path / "audit" / "AgentOS_OrganizationCrossProjectAttribution_ReturnPack_v0_1.zip"
    ).is_file()


def test_cross_project_audit_rejects_provider_direction_that_conflicts_with_kernel_sign(tmp_path):
    first = feedback("context://first", (0.1, 0.2, 0.3, 0.4))
    second = feedback("context://second", (-0.1, -0.2, -0.3, -0.4))
    second["diagnosis"]["component_hypotheses"][0]["direction"] = "BENEFICIAL"

    with pytest.raises(ValueError, match="cross_project_provider_direction_mismatch"):
        run_audit(
            (
                write(tmp_path / "first.json", first),
                write(tmp_path / "second.json", second),
            ),
            tmp_path / "audit",
        )
