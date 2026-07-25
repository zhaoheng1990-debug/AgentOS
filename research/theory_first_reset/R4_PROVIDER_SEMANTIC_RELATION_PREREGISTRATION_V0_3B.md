# R4 Provider Semantic Relation Preregistration v0.3B

## Status

`PREREGISTERED_FRESH_PROVIDER_RELATION_TEST`

## Inheritance

- MethodologyKernel v1.1;
- `R4_SEMANTIC_RELATION_COMPOSITION_THEORY_V0_3.md`;
- `R4_ENGINEERING_OBJECT_MAP_V0_3.md`;
- `R4_RELATION_BOUNDARY_SYNTHETIC_CLOSURE_V0_3A.md`;
- `R4_PROVIDER_SEMANTIC_RELATION_AUTHORIZATION_V0_3B.json`.

## Research Question

Can one Provider instantiate candidate `SemanticPacketRelation` receipts from
new semantic micro-world descriptions, without emitting composition actions or
probabilities, such that Runtime-derived actions remain accurate and
non-harmful?

Secondary question:

Does relation accuracy degrade when 12 cases are presented in one batch compared
with one case per call?

## Ontology To Metric

```text
SemanticPacketRelation
  -> Provider relation-state receipt
  -> exact state accuracy and per-state confusion

CompositionAdmissibility
  -> Runtime-derived action
  -> action accuracy, false combine, false deduplicate, false block

PresentationRobustness
  -> batch/single relation agreement
  -> exact agreement and accuracy difference
```

## Fresh Corpus

Twelve synthetic micro-worlds are created after this preregistration and frozen
in source before any Provider call.

Balance:

- 2 `INDEPENDENT_DISTINCT`;
- 2 `EXACT_DUPLICATE`;
- 2 `DEPENDENT_DISTINCT`;
- 2 `PARTIAL_OVERLAP`;
- 2 `SCOPE_INCOMPATIBLE`;
- 2 `UNRESOLVED`.

The public surface contains:

- case ID;
- two packet IDs;
- two evidence descriptors;
- descriptor evidence references;
- the target scope.

The private surface contains:

- exact relation state;
- Runtime-derived exact action.

Private relation labels and actions are never included in Provider prompts.

The corpus must pass before calls:

- 12 unique case IDs;
- exact two-per-state balance;
- unique packet IDs within each case;
- two public evidence references per case;
- no private state or action string in serialized public prompts;
- corpus hash frozen in the implementation commit.

## Provider Configuration

- Provider: DeepSeek;
- model: `deepseek-v4-flash`;
- thinking: disabled;
- temperature: 0;
- response format: JSON object;
- maximum completion tokens: 5000.

## Provider Output

Required:

- case ID;
- one of the six relation states;
- exactly the admitted descriptor evidence references;
- unresolved-assumptions array.

Forbidden:

- composition action;
- selected or excluded packet IDs;
- composed probability;
- acceptance, retention, baseline, or publication state.

Top-level object and top-level array are both mechanically canonicalized to a
receipt list. The observed root type is recorded. This is frozen before calls
because root wrapping adds no semantic information.

Extra fields are recorded and excluded from canonical state.

## Presentation Arms

### Batch A

- all 12 cases in ascending order;
- relation definitions in canonical order.

### Batch B

- all 12 cases in descending order;
- relation definitions in reverse order.

### Single

- 12 independent logical calls;
- one case per call;
- relation-definition order rotated deterministically by case index.

Total:

- 14 logical calls;
- at most 28 physical attempts;
- at most 120000 total tokens.

## Runtime Action Mapping

Provider cannot emit the action.

Runtime derives:

| Relation | Action |
| --- | --- |
| `INDEPENDENT_DISTINCT` | `COMBINE` |
| `EXACT_DUPLICATE` | `DEDUPE_AND_COMBINE` |
| all other states | `BLOCK` |

## Frozen Metrics

For each arm:

- exact relation accuracy;
- macro state recall;
- exact action accuracy;
- false `COMBINE`;
- false `DEDUPE_AND_COMBINE`;
- false `BLOCK`;
- evidence-reference coverage;
- contract failures.

Across arms:

- Batch A versus Batch B exact agreement;
- majority batch state versus Single exact agreement;
- Single minus mean-batch accuracy;
- token cost per valid relation receipt;
- root-shape and extra-field diagnostics.

## Frozen PASS Gates

All 14 gates must pass:

1. 14/14 logical calls complete within 28 physical attempts;
2. total tokens do not exceed 120000;
3. mechanical receipt coverage is 100%;
4. Batch A relation accuracy is at least 11/12;
5. Batch B relation accuracy is at least 11/12;
6. Single relation accuracy is at least 11/12;
7. macro state recall in every arm is at least 0.80;
8. Batch A versus Batch B exact agreement is at least 11/12;
9. batch-majority versus Single exact agreement is at least 10/12;
10. exact Runtime action accuracy in every arm is at least 11/12;
11. false `COMBINE` count is zero across all arms;
12. false `DEDUPE_AND_COMBINE` count is zero across all arms;
13. evidence-reference coverage is 100% and no forbidden field enters canonical
    state;
14. Provider decision authority, CoreSlim writes, retention writes, and
    baseline writes are zero.

## Discriminating Outcomes

### Semantic adequacy supported

- all gates pass;
- Provider relation receipts are adequate for this same-Provider fresh
  synthetic surface;
- no Core synchronization follows automatically.

### Batch degradation

- Single accuracy passes;
- either batch arm scores below 10/12;
- false-action gates remain separately decisive.

### Semantic inadequacy

- Single and batch arms fail relation accuracy;
- errors are distributed across relation states rather than only root shape.

### Taxonomy or construction failure

- systematic ambiguity is found in the private reference;
- state labels cannot be assigned without adding unstated assumptions;
- close v0.3B without Provider adequacy inference.

## Stop Rule

Stop immediately when:

- one logical call exhausts two attempts;
- token budget is crossed;
- private relation labels enter a prompt;
- a frozen state, case, metric, or threshold would need repair;
- forbidden project writes occur.

No same-version semantic repair is allowed after the first Provider response.
