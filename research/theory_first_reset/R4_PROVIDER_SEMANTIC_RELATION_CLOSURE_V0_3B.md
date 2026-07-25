# R4 Provider Semantic Relation Closure v0.3B

## Status

`FAIL_EARLY_STOP_MECHANICAL_ENVELOPE_MISMATCH`

Post-hoc diagnostic:

`UNACCEPTED_BATCH_SEMANTIC_CONTENT_12_OF_12_EXACT_TWICE`

Evidence coordinate:

`LIVE_PROVIDER_FRESH_SYNTHETIC_EARLY_STOP`

The preregistered run stopped after Batch A exhausted its two physical attempts.
Neither response passed the frozen receipt-envelope parser. No Batch B or
single-case call was made. No same-version repair was applied.

The preserved invalid responses contain complete relation assessments and are
analyzed separately without scoring or promotion authority.

## Frozen Coordinate

- theory: `R4_SEMANTIC_RELATION_COMPOSITION_THEORY_V0_3.md`;
- construction closure:
  `R4_RELATION_BOUNDARY_SYNTHETIC_CLOSURE_V0_3A.md`;
- authorization:
  `R4_PROVIDER_SEMANTIC_RELATION_AUTHORIZATION_V0_3B.json`;
- preregistration:
  `R4_PROVIDER_SEMANTIC_RELATION_PREREGISTRATION_V0_3B.md`;
- corpus manifest:
  `R4_PROVIDER_SEMANTIC_RELATION_CORPUS_MANIFEST_V0_3B.json`;
- preregistration commit: `ac3cc65`;
- corpus and implementation commit: `7da071f`;
- Provider: DeepSeek `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- private relation labels exposed: false;
- Runtime actions exposed: false;
- CoreSlim, retention, and baseline writes: zero.

## Execution

| Quantity | Result |
| --- | ---: |
| planned logical calls | 14 |
| valid logical calls | 0 |
| physical attempts | 2 |
| prompt tokens | 4412 |
| completion tokens | 1773 |
| total tokens | 6185 |
| cache-hit tokens | 2176 |

Both attempts used the same frozen prompt hash:

```text
d52854592979b299d6b7de65327cfc01b0c45e1f88fd94d13039a728ab0b93b1
```

Both failed:

```text
ValueError:
root must be a receipt object, receipts object, or array
```

## Observed Envelope

The Provider returned:

```json
{
  "cases": [
    {
      "case_id": "R43B-01",
      "relation_state": "INDEPENDENT_DISTINCT",
      "evidence_refs": ["...", "..."],
      "unresolved_assumptions": []
    }
  ]
}
```

The frozen parser accepted:

- a top-level array;
- `{"receipts": [...]}`;
- a direct single receipt object.

It did not accept `{"cases": [...]}`.

The key `cases` appears to preserve the input container name rather than the
requested output container name. The semantic receipt items themselves contain
the required fields and no forbidden composition or state authority.

## Formal Gate Status

The overall result is `FAIL`, not `PARTIAL`:

- 14/14 logical calls did not complete;
- mechanical receipt coverage was not accepted;
- all semantic and cross-arm gates are formally unscorable;
- Batch B and Single arms were not executed.

No post-hoc normalization may convert this version to pass.

## Unaccepted Semantic Diagnostic

For diagnostic purposes only, each `cases` array was placed under the already
frozen `receipts` key and passed through the unchanged item validator.

| Diagnostic | Attempt 1 | Attempt 2 |
| --- | ---: | ---: |
| relation accuracy | 12/12 | 12/12 |
| macro state recall | 1.0 | 1.0 |
| Runtime action accuracy | 12/12 | 12/12 |
| false combine | 0 | 0 |
| false deduplicate | 0 | 0 |
| false block | 0 | 0 |
| evidence-reference coverage | 100% | 100% |

Relation-state agreement between attempts:

```text
12/12
```

The two response hashes differ because the unresolved-assumption wording for
the last two cases differs. Relation states, evidence references, and
Runtime-derived actions remain identical.

This diagnostic supports:

`BATCH_SEMANTIC_CONTENT_WAS_EXACT_ON_THE_OBSERVED_FRESH_SURFACE`

It does not establish:

- accepted Provider relation adequacy;
- Batch B robustness;
- single-case robustness;
- batch-versus-single equivalence;
- completion of the preregistered panel.

## Phenomenon Analysis

### 1. Semantic content and envelope compliance diverged

The Provider identified:

- two independent-distinct cases;
- two exact duplicates;
- two dependent-distinct cases;
- two partial overlaps;
- two scope incompatibilities;
- two unresolved cases.

Every classification matched the private reference in both attempts, while both
responses failed the outer envelope.

The present bottleneck is therefore not supported as semantic inadequacy.

### 2. Retry reproduced the state surface but not the prose

At temperature zero:

- all 12 relation states were stable;
- all evidence references were stable;
- unresolved-assumption prose changed;
- root alias remained `cases`.

This suggests a stable structural output preference with flexible explanatory
wording.

### 3. Key-name strictness added no Cbit

`cases` versus `receipts` does not change:

- item identity;
- relation state;
- evidence scope;
- unresolved assumptions;
- Runtime action.

Rejecting solely on this key distinguishes envelopes without distinguishing
semantic content.

However, silently accepting every list-valued field would be unsafe when an
object contains multiple candidate arrays or mixed metadata. The correction
must be shape-bound and ambiguity-blocking, not alias-specific.

## Failure Classification

Primary:

`CONSTRUCTION_FAILURE / MECHANICAL_ENVELOPE_MISMATCH`

Not supported:

`PROVIDER_SEMANTIC_RELATION_INADEQUACY`

Still unresolved:

- batch order robustness;
- single-case presentation;
- batch-size degradation;
- same-Provider transfer to a second fresh relation corpus.

## Theory Writeback

Add a general `ReceiptEnvelopeCanonicalizer` before item validation.

Allowed shapes:

1. root array -> receipt items;
2. direct object containing all required receipt keys -> one receipt;
3. object with exactly one list-valued field whose every item contains the
   required receipt keys -> receipt items and recorded source key.

Blocked shapes:

- zero candidate item collections;
- more than one candidate list;
- mixed valid and invalid receipt items;
- nested authority fields;
- missing exact expected case coverage.

The canonicalizer:

- is deterministic;
- does not inspect private truth;
- does not alter item values;
- records original root type and source key;
- grants no semantic or decision authority.

This is a general shape rule, not a `cases` exception.

## Anti-Additive Audit

Do not add:

- a `cases` alias branch;
- another Provider retry;
- a second schema;
- a second coordinator Runtime.

Add only:

- one shape-based envelope canonicalizer;
- adversarial ambiguity tests;
- zero-call replay over the preserved v0.3B raw responses.

## Artifacts

Local ignored artifacts:

```text
outputs/r4_provider_semantic_relation_v0_3b/
```

Hashes:

```text
attempt_ledger_checkpoint.json
  0a1cf89b23d85203f35f8a9046a9ee894ac7cd8bc863af3e624ee0f3af78c76a
failure_analysis.json
  e308c687b502b05edfe16e8ce5a4646b54479eb3933833bf3609bbc751465643
hash_inventory.json
  ce04a3afa310845a4e84d31e9d3139fa00d9c43314bda9f631ee547958deb9bb
```

## Next Research Object

`R4_v0_3C_SHAPE_BASED_RECEIPT_ENVELOPE_CANONICALIZATION`

Required next sequence:

1. zero-Provider theory and adversarial shape tests;
2. zero-call replay of both preserved v0.3B responses;
3. only after pass, a new Provider experiment version;
4. reused v0.3B cases may test mechanical recovery only;
5. fresh semantic generalization requires a second unseen corpus.

Provider calls are paused until v0.3C construction closes.
