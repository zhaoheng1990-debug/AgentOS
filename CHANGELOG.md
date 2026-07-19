# Changelog

All notable CoreSlim changes are recorded here.

## Unreleased

## 0.4.0-alpha.12 - 2026-07-19

- Added a modular `SelectionExecutionFeedbackBridge` that carries a frozen contextual-policy decision into existing Team or Ablation execution Runtimes and returns Kernel-admitted outcomes as exact-context organization records.
- Added strong request commitments for selection receipt, trial surface, evidence references, ordered roles, selected agent identities, complete Provider/model/Runner/Harness/context bindings, Kernel execution authorization, and a separate execution budget.
- Added per-protocol execution footprints for every actually executed arm, including Provider-call count, normalized cost, execution-result hash, and Harness-receipt hash. Kernel budget gates cover hidden comparator arms as well as admitted outcomes.
- Added explicit adapters for the existing three-arm team Runtime and matched organization-ablation Runtime. Coordinator identity is bound separately where the legacy execution result stores it outside cognitive member IDs.
- Added a hash-chained feedback repository with blocked-event preservation, transactional receipt persistence, restart reconstruction, snapshot verification, tamper rejection, duplicate-trial protection, and a read-only `OrganizationTrialRecordSource` port for later Selector runs.
- Kept the bridge, Selector, Provider support, adapters, persistence, Kernel request contracts, outcome contracts, and admission gate in focused modules. Architecture tests cap facade size and reject Kernel dependencies on Runtime or filesystem APIs.
- Added a deterministic LIFE-Cog3R smoke that executes two independent real three-arm trials: the first remains insufficient, the second closes matched evidence, and a restarted downstream Selector obtains project-scoped authorization without manually supplied records.
- Verified 289 local tests, Python compilation, a short-path clean-copy regression, focused budget and binding failures, real execution feedback, restart replay, and independent manifest/hash/ZIP artifact auditing.

## 0.4.0-alpha.11 - 2026-07-19

- Added a modular `ContextualOrganizationPolicyRuntime` that selects among seven executable role policies from structured problem requirements, exact-context matched evidence, registry feasibility, explicit budgets, and risk envelopes.
- Added one bounded Provider assessment operation for structure fit, expected Cbit, cost, residual risk, anti-additive pressure, and uncertainty. Provider recommendations remain advisory; the Kernel owns every hard gate, selected policy, activation mode, and assignment authority.
- Added project-scoped authorization, exploratory-trial-only, and abstention outcomes. Unmatched evidence cannot authorize execution, high-risk cases require matched evidence, adverse matched outcomes block, and cross-context evidence is never pooled.
- Added self-validating matched-evidence commitments, strong advice/decision/assignment bindings, hash-chained selection events, blocked-Provider receipts, restart reconstruction, snapshot verification, and tamper rejection.
- Split contracts, evidence aggregation, Provider support, Kernel selection, persistence, and the Runtime facade into focused modules. Architecture tests prevent Kernel-to-Runtime/filesystem dependencies and cap facade growth.
- Added a deterministic smoke and auditable return pack in which Provider recommends an over-budget full team and the Kernel selects the evidence-supported feasible role combination.
- Refactored the SRO retention slice from two monolithic modules into focused Kernel contracts, matcher-receipt validation, reuse policy, delayed state, Runtime contracts, legacy migration, Provider matching, repository/replay, and JSONL persistence adapters.
- Reduced `SRORetentionRuntime` to a compatibility facade that coordinates independently testable services while preserving the alpha.10 public imports and behavior.
- Removed filesystem access from the SRO Kernel path. `DelayedRetrievalLedger` now depends on an event-store port, with `JsonlDelayedRetrievalEventStore` implemented in `agentos_runtime`.
- Added architecture regression tests that reject Kernel-to-Runtime/filesystem dependencies and verify compatibility exports resolve to the focused module types.
- Verified 272 local tests, Python compilation, deterministic Selector smoke output, restart replay, artifact manifest/hash/ZIP integrity, and a short-path clean-copy run.

## 0.4.0-alpha.10 - 2026-07-19

- Integrated retention/SFI research through the latest closed v1.8 result as a bounded, project-scoped `SRORetentionRuntime`; the planned, unexecuted v1.9 result is not promoted.
- Added strongly bound `SRORetentionTask`, `SROCalibrationContract`, and route receipts. Witness ID/hash, concrete project scope, task commitment, Provider invocation receipt, cognition audit, calibration, and evidence refs are mechanically bound before the Kernel routes reuse.
- Routed graded SRO judgment through `ProviderTaskRouter` and `ProviderBackedRuntimeCognitionLayer`; Provider output is restricted to an exact semantic field set and cannot supply or override identity, authority, scope, or final route state.
- Hardened `GradedSROCompatibilityGate` with binding hashes and confidence/probability consistency while preserving direct reuse, local reconstruction, observe, reject, revise, and abstain safety semantics.
- Added a persistent, hash-chained `DelayedRetrievalLedger` with restart replay, prediction-before-outcome ordering, `fsync`, tamper rejection, and stale concurrent-writer detection.
- Added candidate-only migration for legacy retention records. Current constraint-aligned records may proceed to explicit witness reconstruction; older ACCEPT-label records remain `PENDING_PROVIDER_REVALIDATION`; unsupported or negative-transfer records are quarantined.
- Added a deterministic end-to-end smoke and return pack covering legacy migration, revalidation, witness reconstruction, Provider-backed routing, delayed scoring, restart recovery, manifest, hashes, and ZIP integrity.
- Preserved the research ceiling: no v1.8 synthetic weights, global-memory write authority, automatic legacy promotion, production activation, or v1.9 minimality claim.
- Added committed, frozen LIFE_COG3R, MATH_CBIT1, and OCS1R2 source extracts so default project-source smokes remain reproducible in a clean clone without inheriting the local research archive.
- Verified 251 local tests, clean-worktree execution, Python compilation, deterministic smoke output, restart replay, and release-artifact manifest/hash/ZIP integrity.

## 0.4.0-alpha.9 - 2026-07-19

- Added the authorized `DYNAMIC_NO_SYNTHESIZER` protocol. Generator, Reviewer, and Replicator still execute as isolated roles, while a Generator-bound projection normalizes only the formal hypothesis proposal and cannot read review or replication bodies.
- Hardened dynamic coordination with action schemas limited to currently reachable transitions, explicit pending-candidate finalization semantics, and zero-Cbit allowance only for mandatory frozen-protocol progression.
- Unified evidence-alias admission across team execution and organization ablation while retaining exact source paths, Provider-cited aliases, hidden-truth separation, and fail-closed rejection of unknown references.
- Constrained blind semantic `quality_score` to the inclusive `[0, 1]` scale in both the Provider contract and Runtime validation; the preserved OCS failure demonstrates rejection of an invalid scale.
- Completed two live full five-protocol bundles each for MATH_CBIT1 and OCS1R2, plus the LIFE Synthesizer matched pairs. All four organization components now have at least two matched observations in each context.
- Added a cross-project attribution audit that preserves context-specific effect sizes, compares directions without pooling causal estimates, and keeps all transfer claims candidate-only.
- Observed all four components as beneficial in the bounded LIFE context and harmful in the bounded MATH_CBIT1 and OCS1R2 contexts. Every cross-project role conclusion is therefore `CONTEXT_DEPENDENT`; no universal role ranking or cognitive-multiplication claim is made.
- Added manifests, return packs, replay and evidence-boundary audits for the new live authorization, ablation, learning-feedback, and cross-project artifacts.
- Verified 220 local tests and Python compilation before the release-artifact inventory audit.

## 0.4.0-alpha.8 - 2026-07-19

- Added `CognitiveOrganizationAblationRuntime`, which executes an authorized `DYNAMIC_TEAM` baseline together with Coordinator, Reviewer, and Replicator one-component omissions.
- Added Kernel authorization and budget checks requiring the full baseline plus every selected ablation; unsupported or mixed experiment families fail closed before Provider execution.
- Extended deliberation and coordination contracts with authorization-bound role omission while preserving the default exact four-role path.
- Added equal evidence/finding surfaces, opaque protocol identities, blind Provider semantic assessment, hidden-truth Harness scoring, per-protocol replay, runtime hash chains, manifests, and return packs.
- Added a matched-ablation experiment family that filters Provider suggestions to registered one-component omission protocols and fills missing authorized variants deterministically.
- Added learning feedback from repeated passing ablation bundles. Source hashes must be independent, matched effects are Kernel-computed, and Provider causal status, direction, and evidence references must match frozen constraints.
- Completed two independent live LIFE-Cog3R matched-ablation bundles. Coordinator, Adversarial Reviewer, and Replicator reached two matched pairs; Synthesizer remains unidentifiable because it was not ablated.
- Preserved failed live receipts that exposed evidence-reference, protocol-family, causal-direction, and status-mapping errors; none were imported as evidence.
- Verified 209 local tests, Python compilation, two live ablation manifests and return packs, and the final live learning-feedback manifest and return pack.

## 0.4.0-alpha.7 - 2026-07-19

- Added a cognitive organization learning runtime that admits completed alpha.6 three-arm results only after replay, hidden-truth separation, Harness-owned metric, and evidence-surface gates pass.
- Added context- and evidence-tier-isolated protocol evaluation across repeated complete best-member, fixed-team, and dynamic-team trial groups.
- Added matched-ablation attribution for Coordinator, Reviewer, Replicator, and Synthesizer contributions; absent repeated matched pairs remain explicitly `NOT_IDENTIFIABLE`.
- Added Provider-backed failure diagnosis with evidence aliases and fail-closed rejection of unsupported causal claims or unknown experiment variants.
- Added advisory credit disagreement as an exploration-priority signal without protocol-selection, route-selection, or execution authority.
- Added bounded experiment proposals, separate Kernel authorization, hash-chained organization-learning events, replay, tamper detection, manifests, and return packs.
- Added duplicate-source rejection, SHA-256 field validation, bounded credit profiles, and a conflict gate that prevents Provider causal direction from contradicting frozen matched-ablation effects.
- Reprocessed LIFE-Cog3R, MATH_CBIT1, and OCS1R2 alpha.6 project sources. The single live LIFE result remains `REQUIRE_EXPLORATION` with `SOLO` as incumbent; no role contribution is claimed without matched live ablations.
- Verified 195 local tests and independently recomputed five final alpha.7 manifests and return-pack inventories.

## 0.4.0-alpha.6 - 2026-07-19

- Added the authorization bridge from a Kernel team-formation decision to actual isolated best-member, fixed-team, and dynamic-team execution.
- Added a held-out frozen-finding Harness that owns truth, observed Cbit, error correction, negative-transfer interception, cost, and convergence metrics.
- Added Provider-backed solo cognition, four-role team execution, equal-protocol coordination, synthesizer-bound output normalization, and arm-identity-blind semantic assessment.
- Added per-arm hash-chained replay and a fail-closed replay gate before Harness evaluation.
- Added separate credit events for the best member, fixed team, dynamic team, and formation Provider.
- Added project-source trial loaders and return packs for LIFE-Cog3R, MATH_CBIT1, and OCS1R2.
- Completed a 27-call live LIFE-Cog3R trial. All runtime gates passed, but the dynamic team underperformed both the best member and fixed team; the negative result was preserved in the credit ledger.
- Preserved a separate Moonshot `PROVIDER_UNAVAILABLE` failure run and bounded the successful live evidence to independent DeepSeek role/model contexts rather than claiming multi-provider robustness.
- Verified 179 local tests, three final project-source fixture return packs, all live replay gates, and zero hidden-truth keys across 27 recorded live Provider tasks.

## 0.4.0-alpha.5 - 2026-07-19

- Added isolated, Provider-bound member problem baselines over one complete admitted-evidence surface.
- Added Provider-supported cognitive-team proposals over registered agent identities, capabilities, scopes, contexts, advisory credit, and provider diversity.
- Added a separate Kernel authorization gate with canonical role ordering and an explicit frozen budget.
- Added Provider-backed semantic assessment for best-member, fixed-team, and dynamic-team arms while keeping observed Cbit, cost, and convergence steps Harness-owned.
- Added deterministic three-arm counterfactual evaluation and separate individual-agent/team-combination credit events without route-selection authority; pure parity is recorded as neutral `TEAM_COMPOSITION_INCONCLUSIVE` rather than positive credit.
- Added strict nested output validation, receipt-level Provider/model binding, replay snapshots, tamper detection, rollback pointer, cross-project pointer candidate, manifest, and return pack.
- Added a passing LIFE-COG3R live formation-readiness smoke with independent DeepSeek/Kimi problem baselines and a two-provider dynamic team. The dynamic team was at parity with both baselines; observed Cbit remained zero because no downstream research trial was executed.
- Verified 159 local tests, 9/9 live gates, a 9-event replay chain, a 10-file independently recomputed manifest, and a 9-entry return-pack CRC.

## 0.4.0-alpha.4 - 2026-07-18

- Added provider-backed prospective problem-quality assessment with blinded source labels.
- Added deterministic comparison of the group-selected problem against best-member and human baselines.
- Added the Kernel-owned `PENDING_AGENDA_REVIEW -> APPROVED_FOR_TRIAL -> ACTIVE -> RESOLVED/PARTIAL/INVALIDATED` lifecycle.
- Added explicit trial plans, independent Harness receipt gates, provider-backed outcome interpretation, and candidate-only outcome receipts.
- Added agenda, epistemic-credit, residual-problem, and cascading-invalidation feedback integration.
- Added outcome consistency gates for evidence scope, independent replication, residual IDs, and rival reduction.
- Added a passing strictly blinded LIFE-COG3R problem-quality trial: 12 negative-control rows independently resolved to 7 pass and 5 fail, the frozen Harness Cbit proxy measured 0.50 against 0.85 expected, and three residual problems were returned.
- Added a pre-trial quality-rejection receipt that invalidates weak problems without fabricating an observed Cbit value.
- Verified 140 local tests, replay integrity, provider/Harness Cbit consistency, and an independently recomputed 12-file live manifest.

## 0.4.0-alpha.3 - 2026-07-18

- Added four independently bound problem-definition roles: Framer, Critic, Researchability Assessor, and Agenda Synthesizer.
- Added provider-backed plural problem framing with no seeded candidate question.
- Added dynamic nested Provider schemas for exact scope, evidence refs, generated problem IDs, and unit metrics.
- Added independent problem criticism and researchability information barriers.
- Added Kernel-gated group agenda selection over the surviving and researchable candidate intersection.
- Added pending-only `DeliberationSeed` output and Kernel-authorized intake into cognitive coordination.
- Added invalidated-evidence exclusion, priority gates, explicit STOP, retry, private quarantine, replay, and manifest coverage.
- Added a passing LIFE-COG3R endogenous-problem live smoke and verified 124 local tests.

## 0.4.0-alpha.2 - 2026-07-18

- Added an independently bound provider-backed Cognitive Coordinator.
- Added structured `CoordinationProposal` records without execution or final-state authority.
- Added Kernel-gated dynamic role ordering, intake, synthesis, and candidate-finalization checkpoints.
- Added mechanical route prerequisites, cycle budgets, per-role execution budgets, and anti-loop conflict-reference gates.
- Added checkpoint-scoped retry, public coordination receipts, replay snapshots, and private coordinator memory.
- Added a coordinated LIFE-COG3R live smoke with recovered proposal and Provider failures.
- Verified 112 local tests and a passing Kernel-gated coordination session.

## 0.4.0-alpha.1 - 2026-07-18

- Added four independently bound cognitive roles: Generator, Reviewer, Replicator, and Synthesizer.
- Added immutable role contracts, formal-message types, and mechanical information barriers.
- Added owner-scoped hash-chained private Agent workspaces.
- Added a Kernel-gated deliberation state machine with blocked-stage retry and pending-only candidate formation.
- Added fixed Provider/model binding through `ProviderCognitiveAgentAdapter`.
- Added public hash-chained deliberation events, snapshots, replay, and tamper detection.
- Added a provider-backed LIFE-COG3R four-role smoke test.
- Verified 102 local tests and a passing live cognitive-role session.

## 0.3.1 - 2026-07-18

- Added data-driven provider semantic consistency assertions.
- Added fail-closed handling for evidence/judgment conflicts.
- Added provider-backed revalidation while preserving initial conflict receipts.
- Added modular P0-P5 group cognition runtime components.
- Added a real project-source smoke workflow and regression coverage.
- Verified 87 local tests and a passing LIFE-COG3R P0-P5 smoke run.

## 0.3.0 - 2026-07-17

- Established the provider cognition quality lifecycle baseline.
- Added provider execution routing, receipts, fallback, schema validation, and provenance.
- Added durable task, artifact versioning, evidence dimension, and quality decision primitives.
