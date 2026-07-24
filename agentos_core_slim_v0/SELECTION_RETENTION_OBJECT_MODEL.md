# AgentOS Selection-first Retention Object Model v0.1

Status: `INTEGRATED_SHADOW_CONTRACTS__NO_AUTOMATIC_RETENTION`

## Why this object model exists

Retention cannot be reconstructed reliably from a successful final artifact
alone. AgentOS must know which real alternatives existed, which path was
selected, which paths were rejected or deferred, and what change was expected
before the consequence became visible. Otherwise retrospective explanation can
be mistaken for prospective selection evidence.

Alpha.21 therefore separates five objects:

1. `CognitiveActionReceipt` records one role-bounded cognitive operation.
2. `TypedRelationEvidenceBinding` separates primary, corroborating,
   counterevidence, and gap evidence without owning relation truth.
3. `ProspectiveSelectionEvent` seals the selection portfolio before
   consequences.
4. `ConsequenceBinding` links a later observation while remaining logically
   `UNASSIGNED`.
5. `PortfolioSelectionRetentionGate` forms only a project-scoped shadow
   candidate from separate applicability, value, and validity evidence.

## Module boundaries

| Module | Single responsibility |
| --- | --- |
| `agentos_kernel/cognitive_action_models.py` | cognitive action vocabulary, role capability, cost, and hash-bound receipt |
| `agentos_kernel/typed_evidence_binding.py` | typed relation-evidence contract and two-role consensus |
| `agentos_kernel/selection_models.py` | prospective selection and Provider-supported semantic route |
| `agentos_kernel/retention_evidence_models.py` | consequence, applicability, value, and validity evidence |
| `agentos_kernel/selection_retention_policy.py` | non-compensable portfolio gate and candidate state |
| `agentos_runtime/selection_retention_migration.py` | candidate-only legacy witness reconstruction |
| `agentos_runtime/selection_retention_repository.py` | project-scoped event chain, snapshot, and replay |
| `agentos_kernel/selection_retention_models.py` | thin compatibility facade only |

There is no combined selection-retention Runtime. Kernel modules have no
filesystem or Runtime imports. Persistence and migration remain separate
Runtime services.

## Authority boundary

Providers support semantic action, evidence typing, path ranking,
applicability, value interpretation, and validity assessment. The Runtime
organizes these receipts and preserves conflicts. The Kernel validates object
binding, enforces hard gates, and owns candidate state.

The following remain forbidden:

- assigning a consequence to a retained memory merely because it followed a
  selection;
- compensating stale or drifted validity with a high Cbit score;
- converting a legacy witness into a prospective selection without explicit
  alternatives;
- treating corroboration as primary evidence;
- granting global memory, baseline, or production authority from a shadow
  decision.

## Research lineage and claim ceiling

The typed evidence contract was synchronized only after the external v0.63
revealed mechanism calibration completed:

- 12/12 binding receipts;
- 30/30 relation consensuses;
- zero binding conflicts or contract failures;
- 12/12 state receipts;
- zero state mismatches or cross-role disagreements;
- required `PC-TRAFFIC:REL-O3-O1` recovery;
- 24 task calls and 82,847 physical tokens.

One nonconflicting corroboration divergence was retained by typed union. The
experiment grants contract-sync eligibility, not fresh-generalization,
retention-write, baseline, or production authority. A new frozen holdout is
still required before stronger claims.

## Legacy compatibility

`SerialSelectionWitness` remains supported by the existing SRO retention
runtime. `SerialSelectionWitnessAdapter` creates a
`PENDING_SELECTION_RECONSTRUCTION` candidate that preserves the legacy hash,
project scope, and evidence. A Kernel-authorized reconstruction must supply
the missing alternatives, selected path, rejected/deferred partition, and
path-change hypothesis before `ProspectiveSelectionEvent` can exist.
