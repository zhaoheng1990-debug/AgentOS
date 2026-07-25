from local_collective_cognition.admission_v3_fresh_holdout import (
    PRIOR_TEST_PROMPT_IDS,
    SELECTED_PROMPT_IDS as V078_PROMPT_IDS,
    V077_DEVELOPMENT_PROMPT_IDS,
)
from local_collective_cognition.admission_v4_fresh_holdout import (
    SELECTED_PROMPT_IDS,
)


def test_v079_selected_objects_are_disjoint_from_prior_surfaces():
    selected = set(SELECTED_PROMPT_IDS)
    prior = (
        set(PRIOR_TEST_PROMPT_IDS)
        | set(V077_DEVELOPMENT_PROMPT_IDS)
        | set(V078_PROMPT_IDS)
    )

    assert len(SELECTED_PROMPT_IDS) == 12
    assert len(selected) == 12
    assert not selected & prior
