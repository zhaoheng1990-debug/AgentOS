# R4 Factorization Causal Benefit Preregistration v0.3J

## Status

`PREREGISTERED_MATCHED_FRESH_PROVIDER_COMPARISON`

## Frozen Sequence

1. freeze theory and this preregistration;
2. construct twelve fresh cases and both private references;
3. freeze public corpus, prompts, references, implementation, and call order;
4. pass deterministic leakage and compiler preflight;
5. execute four logical calls in `L-F-F-L` order;
6. compile relations, actions, and revalidation trajectories locally;
7. score without repair or rerun;
8. preserve result and theory writeback.

## Provider Budget

- Provider: DeepSeek;
- requested model: `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- logical calls: 4;
- maximum physical attempts: 8;
- maximum completion tokens per call: 7000;
- maximum total tokens: 60000.

## Fresh Corpus

- twelve cases unused by prior Provider experiments;
- identical public evidence in both arms;
- at least two cases separating asserted-unverified from unknown
  applicability;
- all seven valid factorized status-effect combinations represented;
- no relation, Runtime action, revalidation label, or private attribute tuple
  in the public prompts.

## Frozen PASS Gates

All 18 gates must pass:

1. deterministic corpus preflight passes;
2. public prompts contain no private state or Runtime authority;
3. four logical calls complete within eight physical attempts;
4. total tokens do not exceed 60000;
5. twelve receipts are present exactly once in every call;
6. evidence-reference sets are exact in every call;
7. shared-attribute accuracy is at least 10/12 in every call;
8. legacy information-relation accuracy is at least 10/12 in both legacy
   calls;
9. factorized transform-status accuracy is at least 10/12 in both factorized
   calls;
10. factorized information-effect accuracy is at least 10/12 in both
    factorized calls;
11. factorized latent-pair resolution exceeds legacy unique resolution by at
    least 2/12 in each matched round;
12. factorized revalidation accuracy exceeds legacy by at least 2/12 in each
    matched round;
13. Runtime relation accuracy is at least 10/12 in every call;
14. Runtime action accuracy is at least 11/12 in every call;
15. false deduplication is zero across all calls;
16. within-arm action agreement is at least 11/12;
17. no forbidden Provider field enters canonical state;
18. Provider decision authority and protected writes are zero.

Factorized token overhead is measured but is not a PASS gate unless the total
budget is exceeded.

## No Same-Version Repair

After first Provider exposure, no corpus, reference, prompt, schema, projection,
threshold, compiler, scoring rule, or call order may change.
