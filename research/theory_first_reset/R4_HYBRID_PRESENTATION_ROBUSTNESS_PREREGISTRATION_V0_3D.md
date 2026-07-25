# R4 Hybrid Presentation Robustness Preregistration v0.3D

## Status

`PREREGISTERED_BOUNDED_PROVIDER_DIAGNOSTIC`

## Question

Do the frozen v0.3B semantic relation cases retain accurate and non-harmful
relation judgments under reversed batch order and isolated single-case
presentation?

## Evidence Arms

### Historical Batch A

- source: two preserved v0.3B invalid-envelope responses;
- primary prediction: attempt 1;
- stability witness: attempt 2;
- required preflight agreement: 12/12;
- new Provider calls: zero.

### Current Batch B

- cases in descending order;
- relation definitions in reverse order;
- one logical call;
- at most two physical attempts.

### Current Single

- twelve isolated logical calls;
- one case per call;
- relation-definition order rotated by frozen case index;
- at most twenty-four physical attempts.

## Frozen Provider Configuration

- Provider: DeepSeek;
- model request: `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- JSON object response mode;
- maximum completion tokens per call: 5000.

Existing v0.3B system and user prompts are reused byte-for-byte.

## Budget

| Quantity | Limit |
| --- | ---: |
| new logical calls | 13 |
| new physical attempts | 26 |
| incremental total tokens | 80000 |
| repeated Batch A calls | 0 |

Historical v0.3B token use is reported separately and excluded from the
incremental ceiling.

## Frozen Metrics

For Batch B and Single:

- relation accuracy;
- macro state recall;
- Runtime action accuracy;
- false combine;
- false deduplicate;
- false block;
- evidence-reference coverage;
- contract failures.

Across arms:

- historical Batch A versus Batch B exact agreement;
- historical Batch A versus Single exact agreement;
- Batch B versus Single exact agreement;
- new-arm accuracy difference;
- case-level disagreement matrix;
- incremental tokens per new receipt;
- root-shape distribution.

## Frozen PASS Gates

All 15 gates must pass:

1. both historical source hashes match;
2. historical attempts agree 12/12;
3. 13/13 new logical calls complete within 26 physical attempts;
4. incremental tokens do not exceed 80000;
5. new mechanical receipt coverage is 24/24;
6. Batch B relation accuracy is at least 11/12;
7. Single relation accuracy is at least 11/12;
8. macro state recall in both new arms is at least 0.80;
9. Batch A versus Batch B agreement is at least 11/12;
10. Batch A versus Single agreement is at least 10/12;
11. Batch B versus Single agreement is at least 10/12;
12. Runtime action accuracy in all three arms is at least 11/12;
13. false combine and false deduplicate counts are both zero across all arms;
14. evidence coverage is 100% and no forbidden authority field enters canonical
    state;
15. Provider decision authority, repeated Batch A calls, and CoreSlim,
    retention, and baseline writes are zero.

## Frozen Outcome Classes

`PASS_PRESENTATION_ROBUST_WITH_HYBRID_TIME_LIMIT`

- all gates pass.

`FAIL_PRESENTATION_OR_TIME_INSTABILITY`

- mechanics pass but one or more semantic/agreement gates fail;
- closure reports all compatible rival models.

`FAIL_HARMFUL_ACTION`

- any false combine or false deduplicate occurs.

`FAIL_CONSTRUCTION_EARLY_STOP`

- one logical call exhausts two attempts;
- semantic panel remains incomplete and unscorable.

## Leakage Gate

Before calls:

- serialized Batch B and Single prompts must contain no private relation state
  assigned to a case;
- no Runtime action may appear in case payloads;
- historical response content may not enter Provider prompts;
- public prompt hashes must be frozen in a manifest commit.

## Stop Rule

Stop without same-version repair when:

- preflight historical binding fails;
- one logical call exhausts two attempts;
- token ceiling is crossed;
- a prompt or private-reference hash differs from the frozen manifest;
- a threshold or semantic field would need revision.

## Interpretation Boundary

A pass supports same-Provider presentation robustness on an already exposed
synthetic corpus. It does not support fresh semantic generalization.

A failure cannot uniquely separate presentation effect from time drift because
Batch A is historical.

