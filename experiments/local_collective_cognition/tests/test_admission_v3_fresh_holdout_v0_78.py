from local_collective_cognition.admission_v3_fresh_holdout import (
    PRIOR_TEST_PROMPT_IDS,
    SELECTED_PROMPT_IDS,
    V077_DEVELOPMENT_PROMPT_IDS,
)


def test_v078_selected_objects_are_disjoint_from_prior_surfaces():
    selected = set(SELECTED_PROMPT_IDS)

    assert len(SELECTED_PROMPT_IDS) == 12
    assert len(selected) == 12
    assert not selected & set(PRIOR_TEST_PROMPT_IDS)
    assert not selected & set(V077_DEVELOPMENT_PROMPT_IDS)
