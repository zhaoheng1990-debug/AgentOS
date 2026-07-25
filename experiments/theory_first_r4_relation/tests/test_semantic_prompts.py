from theory_first_r4_relation.semantic_cases import CASES
from theory_first_r4_relation.semantic_prompts import batch_prompt, single_prompt


def test_prompts_exclude_private_actions_and_probability_outputs() -> None:
    prompts = [batch_prompt("A"), batch_prompt("B")]
    prompts.extend(single_prompt(case, index) for index, case in enumerate(CASES))
    for prompt in prompts:
        assert "DEDUPE_AND_COMBINE" not in prompt
        assert '"COMBINE"' not in prompt
        assert "composed_probability" not in prompt
        assert "private_relation_state" not in prompt
