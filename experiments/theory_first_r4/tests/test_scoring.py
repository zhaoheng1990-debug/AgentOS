import pytest

from theory_first_r4.cases import CASES, ROLE_IDS, exact_reference
from theory_first_r4.scoring import SUBSETS, evaluate_predictions, subset_key


def test_exact_predictions_recover_unit_k_and_shapley_order() -> None:
    reference = exact_reference()
    predictions = {
        subset_key(roles): {
            case.case_id: reference[case.case_id][subset_key(roles)]
            for case in CASES
        }
        for roles in SUBSETS
    }
    result = evaluate_predictions(
        predictions,
        {
            role: (predictions[role], predictions[role])
            for role in ROLE_IDS
        },
        (
            predictions[subset_key(ROLE_IDS)],
            predictions[subset_key(ROLE_IDS)],
        ),
    )
    assert result["role_probability_error"]["maximum"] == pytest.approx(
        0.0, abs=1e-12
    )
    assert result["full_probability_error"]["maximum"] == pytest.approx(
        0.0, abs=1e-12
    )
    assert result["k_info"] == pytest.approx(1.0, abs=1e-12)
    assert result["role_order_matches"] is True
