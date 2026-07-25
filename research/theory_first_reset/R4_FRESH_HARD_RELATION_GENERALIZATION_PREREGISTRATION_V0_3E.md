# R4 Fresh Hard Relation Generalization Preregistration v0.3E

## Status

`PREREGISTERED_FRESH_HARD_BATCH_TEST`

## Corpus

- 18 cases generated after theory freeze;
- 3 cases per frozen relation state;
- at least 12 domains;
- no v0.3B case reuse;
- no direct lexical relation cues;
- private adjudication basis frozen before Provider calls.

The corpus is an internal synthetic fresh surface, not an external benchmark
holdout.

## Provider Arm

One batch logical call:

- all 18 cases;
- frozen six relation definitions;
- deterministic interleaved case order;
- one JSON receipt collection;
- at most two physical attempts.

No Single or repeated batch arm is authorized in this version.

## Provider Configuration

- Provider: DeepSeek;
- model request: `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- JSON object response mode;
- maximum completion tokens: 7000.

## Budget

| Quantity | Limit |
| --- | ---: |
| logical calls | 1 |
| physical attempts | 2 |
| total tokens | 20000 |
| expected receipts | 18 |

## Frozen Metrics

- exact relation accuracy;
- recall for each of six states;
- macro state recall;
- exact Runtime action accuracy;
- false combine;
- false deduplicate;
- false block;
- evidence-reference coverage;
- true-unresolved assumption coverage;
- token cost per receipt;
- root shape and dropped-field diagnostics.

## Frozen PASS Gates

All 13 gates must pass:

1. corpus contains 18 unique cases and exactly 3 per state;
2. lexical de-cueing and private-surface leakage checks pass;
3. one logical call completes within two attempts;
4. total tokens do not exceed 20000;
5. mechanical receipt coverage is 18/18;
6. relation accuracy is at least 15/18;
7. recall for every state is at least 2/3;
8. macro state recall is at least 0.80;
9. Runtime action accuracy is at least 17/18;
10. false combine count is zero;
11. false deduplicate count is zero;
12. false block count is at most one and all true `UNRESOLVED` cases contain
    at least one unresolved assumption;
13. evidence coverage is 100%, Provider decision authority is zero, and
    CoreSlim, retention, and baseline writes are zero.

## Outcome Classes

`PASS_FRESH_HARD_RELATION_GENERALIZATION`

- all gates pass.

`FAIL_HARMFUL_GENERALIZATION`

- any false combine or false deduplicate occurs.

`FAIL_SEMANTIC_TRANSFER`

- mechanics pass but accuracy, recall, action, or uncertainty gates fail.

`FAIL_CORPUS_CONSTRUCTION`

- private adjudication or lexical de-cueing fails before calls.

`FAIL_PROVIDER_CONSTRUCTION_EARLY_STOP`

- the batch call exhausts two attempts.

## Stop Rule

No same-version repair after:

- corpus hash freeze;
- private reference reveal to the scorer;
- first Provider call.

If the batch reveals specific ambiguous cases, preserve them and design any
isolated follow-up as a new version.

## Claim Ceiling

`SAME_PROVIDER_FRESH_HARD_SYNTHETIC_RELATION_GENERALIZATION_ONLY`

