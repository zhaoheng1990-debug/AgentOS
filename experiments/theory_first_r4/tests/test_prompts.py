from theory_first_r4.cases import ROLE_IDS
from theory_first_r4.prompts import coordinator_prompt, role_prompt


def _packets() -> dict[str, list[dict[str, object]]]:
    return {
        role: [
            {
                "case_id": f"R4-{index:02d}",
                "role_id": role,
                "evidence_id": f"R4-{index:02d}-E{role[-1]}",
                "probability_y1": 0.6,
                "direction": "Y1",
                "calculation_basis": "PRIOR_ODDS_TIMES_ASSIGNED_LR",
                "assumptions": ["COMMON_PRIOR", "ONLY_ASSIGNED_EVIDENCE"],
            }
            for index in range(1, 13)
        ]
        for role in ROLE_IDS
    }


def test_role_prompt_contains_only_one_assigned_lr_per_case() -> None:
    prompt = role_prompt("ROLE_A", "A")
    assert prompt.count("assigned_likelihood_ratio") == 12
    assert "private" not in prompt.casefold() or "private answer" in prompt.casefold()
    assert "ROLE_B" not in prompt
    assert "ROLE_C" not in prompt


def test_coordinator_prompt_contains_packets_not_likelihood_ratios() -> None:
    prompt = coordinator_prompt(("ROLE_A", "ROLE_B"), _packets(), "A")
    assert "assigned_likelihood_ratio" not in prompt
    assert "role_packets" in prompt
    assert "private_reference_used" in prompt

