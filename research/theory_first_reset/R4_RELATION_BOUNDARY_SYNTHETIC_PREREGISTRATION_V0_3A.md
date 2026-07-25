# R4 Relation Boundary Synthetic Preregistration v0.3A

## Status

`PREREGISTERED_ZERO_PROVIDER_CONSTRUCTION`

## Objective

Test whether the optimized object chain can:

1. represent complete packet-pair relations;
2. derive composition actions without Provider authority;
3. deduplicate exact evidence;
4. block unsupported composition;
5. preserve numeric information under valid independent composition;
6. remain deterministic, modular, and replayable.

## Frozen Relation States

- `INDEPENDENT_DISTINCT`
- `EXACT_DUPLICATE`
- `DEPENDENT_DISTINCT`
- `PARTIAL_OVERLAP`
- `SCOPE_INCOMPATIBLE`
- `UNRESOLVED`

No new state may be added after execution.

## Frozen Plan Actions

- `COMBINE`
- `DEDUPE_AND_COMBINE`
- `BLOCK`

## Frozen Cases

1. two independent packets -> `COMBINE`;
2. three independent packets -> `COMBINE`;
3. two exact duplicates -> `DEDUPE_AND_COMBINE`;
4. duplicate pair plus one independent packet -> `DEDUPE_AND_COMBINE`;
5. dependent distinct pair -> `BLOCK`;
6. partial-overlap pair -> `BLOCK`;
7. scope-incompatible pair -> `BLOCK`;
8. unresolved pair -> `BLOCK`;
9. incomplete three-packet graph -> `BLOCK`;
10. duplicate component with inconsistent probabilities -> `BLOCK`;
11. mixed duplicate graph with contradictory external edges -> `BLOCK`;
12. common-prior mismatch -> `BLOCK`.

Private exact probabilities are computed only for actionable cases.

## Oracle And Negative Controls

Oracle relation arm:

- uses the frozen relation graph;
- must produce the exact action and probability.

Naive arm:

- combines every packet as independent;
- is expected to overcount duplicate evidence.

Removal arm:

- removes one required relation edge;
- must become blocked.

Wrong-relation arm:

- changes one exact duplicate to independent;
- must demonstrate duplicate overconfidence.

## Frozen PASS Gates

All 14 gates must pass:

1. all 12 cases validate mechanically;
2. exact action agreement is 12/12;
3. actionable probability mean error is at most `1e-12`;
4. actionable probability maximum error is at most `1e-12`;
5. no blocked case produces a probability;
6. exact duplicates are selected once;
7. duplicate-plus-independent composition is order invariant;
8. incomplete graph blocks;
9. contradictory duplicate probability blocks;
10. contradictory cross-component relation blocks;
11. common-prior mismatch blocks;
12. naive duplicate composition shows positive overconfidence error;
13. removal tests block or expose the frozen failure;
14. Provider calls, CoreSlim writes, retention writes, and baseline writes are
    zero.

## Determinism

Two complete runs must produce byte-identical:

- `result.json`
- `hash_inventory.json`
- `closure.json`

## Modularity

The standalone implementation must separate:

- contracts;
- frozen cases;
- graph compilation;
- numeric composition;
- evaluation;
- CLI and artifact writing.

No implementation module may import `agentos_core_slim_v0`, `agentos_runtime`,
Provider clients, retention, or baseline modules.

## Interpretation

`PASS`:

- validates the finite object construction only;
- authorizes drafting a fresh Provider semantic-relation preregistration;
- grants no Core synchronization or production authority.

`FAIL`:

- closes v0.3A;
- requires theory or object revision before Provider calls;
- may not be repaired in the same version after result reveal.
