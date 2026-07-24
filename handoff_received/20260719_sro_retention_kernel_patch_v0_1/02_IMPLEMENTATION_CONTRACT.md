# Implementation contract

## Changed kernel surfaces

| Path | Change |
|---|---|
| `agentos_kernel/sro_retention_runtime.py` | new witness, routing and delayed-ledger objects |
| `agentos_kernel/provider_cognition_layer.py` | add graded SRO operation; layer ID v0.6 -> v0.7 |
| `agentos_kernel/__init__.py` | public exports only |
| `tests/test_sro_retention_runtime.py` | new behavior and boundary tests |
| `SRO_RETENTION_RUNTIME.md` | runtime contract and claim boundary |

No release-version file, durable-store implementation, existing retention gate,
autonomous evolution policy, README or CHANGELOG is modified by this patch.

## Kernel invariants

1. Only `project_scoped` witnesses and matcher receipts are routable.
2. Provider/model cognition supplies semantic estimates; AgentOSKernel owns the route.
3. Matcher receipts require exact route classes, normalized probabilities,
   calibration ref, evidence scope, replayability and Provider support ref.
4. Invalid contracts fail closed to `ABSTAIN`.
5. `OBSERVE` means the task evidence is incomplete; `ABSTAIN` means the matcher
   cannot make a calibrated commitment.
6. Negative-transfer, structural-role and boundary failures route to `REJECT`.
7. Stale or drifted validity routes to `REVISE` before reuse.
8. Direct predictions with local interface/drift mismatch route to
   `LOCAL_RECONSTRUCTION`.
9. Synthetic/formal evidence cannot authorize direct reuse.
10. Delayed outcomes require a prior sealed prediction and cannot be rewritten.
11. Every delayed event is hash chained.
12. No object grants global-memory, production, execution or theory-promotion authority.

## Compatibility contract

- `ConstraintAlignedRetentionGate` public API and behavior are unchanged.
- Existing `ProviderBackedRuntimeCognitionLayer` callers remain valid; only one
  provider-required operation is added.
- New objects are additive public exports.
- Existing retained records are not automatically migrated.
- The patch contains no new third-party dependency.

## Success gate

```text
targeted tests pass
full existing tests pass
compileall passes
isolated patch replays on captured preimage
manifest and zip hashes reproduce
```
