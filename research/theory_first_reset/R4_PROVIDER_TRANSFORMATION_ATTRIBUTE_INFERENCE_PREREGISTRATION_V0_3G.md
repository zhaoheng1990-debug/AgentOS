# R4 Provider Transformation Attribute Inference Preregistration v0.3G

## Status

`PREREGISTERED_FRESH_PROVIDER_ATTRIBUTE_TEST`

## Frozen Sequence

1. freeze this theory and preregistration;
2. construct twelve fresh cases without Provider exposure;
3. freeze public corpus, private reference, prompt, and implementation hashes;
4. run deterministic leakage, balance, contract, and compiler preflight;
5. make one Provider batch logical call with at most two physical attempts;
6. canonicalize attributes and evidence references mechanically;
7. compile relation and action with the unchanged v0.3F Runtime compiler;
8. score against the private reference;
9. preserve result and close the version without same-version repair.

## Provider Configuration

- Provider: DeepSeek;
- requested model: `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- response format: JSON object;
- maximum completion tokens: 7000;
- logical calls: 1;
- maximum physical attempts: 2;
- total token ceiling: 20000.

## Frozen Corpus Shape

- twelve unique cases;
- six hidden counterfactual pairs;
- each case has case-local admitted evidence references;
- all five attributes have a private exact reference;
- each pair changes one intended decisive attribute or witness condition;
- no v0.3F case text is reused;
- no relation state or Runtime action appears in the public case surface.

## Canonical Provider Receipt

Required:

- `case_id`;
- `source_identity`;
- `lineage_coupling`;
- `information_relation`;
- `added_uncertainty`;
- `target_claim_relation`;
- `attribute_evidence_refs`;
- `missing_facts`.

`attribute_evidence_refs` must contain exactly the five attribute names. Every
reference must belong to the corresponding case's admitted public evidence.

Forbidden canonical fields:

- relation state;
- Runtime action;
- selected packet;
- acceptance or retention state;
- probability;
- publication or baseline authority.

Extra fields are recorded and dropped. Missing or invalid required fields make
the physical attempt invalid.

## Frozen Metrics

- per-attribute exact accuracy;
- exact five-attribute tuple accuracy;
- counterfactual-pair sensitivity;
- evidence-reference coverage;
- missing-fact preservation;
- Runtime relation accuracy;
- Runtime action accuracy;
- false combine;
- false deduplicate;
- false block;
- token cost per valid receipt;
- contract failures and dropped fields.

## Frozen PASS Gates

All 15 gates must pass:

1. deterministic corpus preflight passes;
2. public prompt contains no private attribute tuple, relation, or action;
3. one logical call completes within two physical attempts;
4. total tokens do not exceed 20000;
5. twelve canonical receipts are present exactly once;
6. each of the five attribute accuracies is at least 10/12;
7. exact five-attribute tuple accuracy is at least 9/12;
8. at least 5/6 counterfactual pairs recover the intended change;
9. evidence-reference coverage is 100%;
10. true missing-fact cases preserve the required unknown attribute;
11. Runtime relation accuracy is at least 10/12;
12. Runtime action accuracy is at least 10/12;
13. false `DEDUPE_AND_COMBINE` is zero;
14. no forbidden Provider field enters canonical state;
15. Provider decision authority and CoreSlim, retention, and baseline writes are
    zero.

False deduplication is a hard failure even when all aggregate thresholds pass.

## Interpretation

`PASS` supports same-Provider inference adequacy on this fresh synthetic
surface. It permits theory work on claim-scoped receipt lifecycle, but does not
authorize CoreSlim integration.

`FAIL_SEMANTIC` preserves the exact confusion pattern and revises the inference
object before another corpus.

`FAIL_CONSTRUCTION` preserves the raw attempt and stops without semantic
adequacy inference.

## No Same-Version Repair

After first Provider exposure, no case, private reference, prompt, schema,
threshold, compiler rule, or scoring rule may change under v0.3G.

