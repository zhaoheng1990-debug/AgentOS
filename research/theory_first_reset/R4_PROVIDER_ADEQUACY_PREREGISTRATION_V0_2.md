# R4 Provider Adequacy Preregistration v0.2

## Status

`PREREGISTERED_PAIRED_PROTOCOL_DIAGNOSTIC`

Theory basis:

`R4_MINIMAL_SUFFICIENT_RECEIPT_THEORY_V0_2.md`

Authorization:

`R4_PROVIDER_PROTOCOL_DIAGNOSTIC_AUTHORIZATION_V0_2.json`

This version is a one-factor protocol diagnostic after the R4 v0.1 receipt
failure. It reuses the finite cases to isolate deterministic-field redundancy.
It is not a fresh confirmation.

## Frozen Question

When Provider-generated `direction` is removed and direction is derived by the
Runtime, can the same Provider:

1. return mechanically valid role probabilities;
2. remain stable across isolated replicates;
3. support packet-only probability composition;
4. preserve the exact role-contribution ordering;
5. do so within the frozen call and token budget?

## Single Intervention

Changed from v0.1:

```text
Provider output:
  probability_y1 + direction

becomes:

Provider output:
  probability_y1

Runtime canonical state:
  probability_y1 + derived direction
```

Unchanged:

- 12 cases and exact private references;
- three roles and evidence assignments;
- common priors and likelihood ratios;
- two counterbalanced role replicates;
- pair and full coordinator calls;
- model, thinking mode, temperature, and JSON output mode;
- scoring functions and thresholds;
- call, attempt, and token ceilings;
- no-write and no-promotion boundaries.

## Provider Configuration

- provider: DeepSeek;
- model: `deepseek-v4-flash`;
- base URL: `https://api.deepseek.com`;
- thinking: disabled;
- response format: JSON object;
- temperature: 0;
- maximum completion tokens: 6000.

## Frozen Cases

The case table is byte-equivalent in meaning to v0.1:

| Case | Prior | LR A | LR B | LR C |
| --- | ---: | ---: | ---: | ---: |
| R4-01 | 0.50 | 4.00 | 2.50 | 0.40 |
| R4-02 | 0.50 | 0.25 | 0.40 | 2.50 |
| R4-03 | 0.35 | 4.00 | 0.67 | 1.50 |
| R4-04 | 0.65 | 0.25 | 1.50 | 0.67 |
| R4-05 | 0.20 | 4.00 | 4.00 | 0.67 |
| R4-06 | 0.80 | 0.25 | 0.25 | 1.50 |
| R4-07 | 0.50 | 1.50 | 0.67 | 1.00 |
| R4-08 | 0.35 | 2.50 | 0.40 | 1.00 |
| R4-09 | 0.65 | 0.40 | 2.50 | 1.00 |
| R4-10 | 0.50 | 4.00 | 0.25 | 1.00 |
| R4-11 | 0.20 | 2.50 | 2.50 | 0.40 |
| R4-12 | 0.80 | 0.40 | 0.40 | 2.50 |

## Calls

Role calls:

- ROLE_A replicate A;
- ROLE_A replicate B;
- ROLE_B replicate A;
- ROLE_B replicate B;
- ROLE_C replicate A;
- ROLE_C replicate B.

Coordinator calls:

- ROLE_A + ROLE_B;
- ROLE_A + ROLE_C;
- ROLE_B + ROLE_C;
- ROLE_A + ROLE_B + ROLE_C replicate A;
- ROLE_A + ROLE_B + ROLE_C replicate B.

Total:

- 11 logical calls;
- at most 2 attempts per logical call;
- at most 22 physical attempts;
- at most 200000 total tokens.

## Mechanical Contract

Required role fields:

- case ID;
- role ID;
- evidence ID;
- probability;
- calculation basis;
- assumptions.

Required coordinator fields:

- case ID;
- included roles;
- probability;
- composition basis;
- no-raw-evidence attestation;
- no-private-reference attestation.

Provider-generated direction is not required. The Runtime derives it from the
accepted probability. Extra fields are recorded and dropped from canonical
state instead of becoming decision inputs.

Invalid raw response content must be persisted locally before validation.

## Frozen Scoring

The exact posterior, expected base-2 cross entropy, `J_provider`, `J_exact`,
`K_info`, three-role Shapley allocation, action readbacks, and cost accounting
are unchanged from v0.1.

## Frozen PASS Gates

R4 v0.2 passes this paired diagnostic only if all 15 conditions hold:

1. 11/11 logical calls complete within 22 physical attempts;
2. total tokens do not exceed 200000;
3. role receipt mechanical validity is 100%;
4. coordinator receipt mechanical validity is 100%;
5. mean role probability error is at most 0.02;
6. maximum role probability error is at most 0.08;
7. replicate direction agreement is 100%;
8. replicate probability MAE is at most 0.03;
9. full coordinator mean probability error is at most 0.03;
10. full coordinator MAP direction agreement is 100%;
11. no full coordinator strong wrong direction occurs;
12. `0 < K_info <= 1.05`;
13. Provider Shapley role ordering matches the exact ordering;
14. coordinator receipts attest no raw evidence or private-reference use;
15. no forbidden project write occurs.

Derived direction is used for gates 7, 10, and 11.

## Interpretation

`PASS`:

- all 15 gates pass;
- supports the minimal-sufficient-receipt mechanism for this paired finite
  diagnostic;
- does not count as fresh external confirmation.

`PARTIAL`:

- all mechanical, leakage, and budget gates pass;
- at least one numeric calibration, stability, composition, or ordering gate
  fails.

`FAIL`:

- a logical call exhausts its attempts;
- required packet coverage or binding fails;
- leakage or budget boundary fails;
- scoring would require changing a frozen prompt, metric, or threshold.

## Stop Rule

After the first Provider response:

- no prompt repair;
- no schema repair;
- no threshold change;
- no case replacement;
- no additional attempt beyond the frozen budget.

Close the observed version and preserve all negative evidence.
