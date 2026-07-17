# AgentOS Core Refactor Seed v0.1

## Objective

Upgrade AgentOS CoreSlim from a collection of bounded primitives into a reusable cognitive runtime substrate. The work must absorb the cross-domain lessons proven in VCOS without importing VC-specific industry logic, report templates, provider prompts, or UI workflows.

## Design Principle

AgentOS remains the cognitive runtime subject. Providers augment bounded semantic work; they do not replace runtime ownership of objectives, constraints, evidence organization, conflict handling, replay, audit, state transitions, or candidate decisions.

Keep the architecture layered:

1. Core: task state, decision findings, event ledger, artifact identity, version relations, replay and rollback.
2. Middleware: provider-backed cognitive task execution, quality decision matrix, evidence-dimension registration, read-model projections.
3. Domain plugins: industry ontology, search plans, diligence workflow, report renderers, provider prompts, Obsidian conventions, and UI.

## P0: Provider Cognitive Execution Plane

Implement a general provider-backed task runtime.

Required types:

- `ProviderCognitiveTask`
- `ProviderCapabilityProfile`
- `ProviderTaskRouter`
- `ProviderAdapter`
- `ProviderResultEnvelope`
- `ProviderInvocationReceipt`
- `ProviderFallbackDecision`

Required behavior:

- Runtime defines task objective, inputs, allowed evidence, expected schema, budget, timeout, freshness requirement, and failure semantics.
- Adapters encapsulate provider-specific formats, including thinking mode, web-search mode, local models, and custom endpoints.
- Provider output is never accepted directly. It must be normalized into a typed result envelope, retain provenance and usage information, then pass runtime validation.
- Persist task ID, idempotency key, model/provider selection, input/output hashes, token usage when available, timeout, retry/fallback decision, and redacted error state.
- Support a provider-unavailable outcome without fabricating a semantic result.
- Domain plugins register task kinds and prompts. Core must not contain VC, company, funding, report, or industry-specific prompts.

Refactor the existing `ProviderBackedRuntimeCognitionLayer` from contract-only auditing into the policy boundary used by this execution plane. Keep mechanical validation, replay, rollback, and boundary checks local to AgentOS.

## P0: Quality Decision Matrix

Replace monolithic quality gates with an independent `QualityDecisionMatrix`.

Required gates:

1. `EvidenceAdmissionGate`: block only untraceable claims or evidence that has no support path.
2. `ScopeCoverageGate`: assess each requested coverage object as complete, qualified, or missing.
3. `ReaderIntegrityGate`: route malformed text, duplicate content, invalid tables, and layout defects to repair without invalidating unrelated content.
4. `PublicationRetentionGate`: determine whether a candidate may become the current published pointer.
5. `BaselineEligibilityGate`: independently control promotion into a governed baseline.

Every finding must contain:

- `control_object`
- `severity`
- `repair_action`
- `blocking_effect`
- `evidence_refs`

Requirements:

- A failure must block only the declared control object and transition.
- Reader-quality defects may block a revision, never erase a previously published artifact.
- Candidate readability, publication, and baseline eligibility must remain distinct decisions.
- Domain plugins own coverage dimensions and thresholds; core owns finding semantics and isolation rules.

## P0: Artifact Version and Publication Retention Model

Implement append-only artifact revision storage.

Required types:

- `ArtifactIdentity`
- `ArtifactRevision`
- `ArtifactRelation`
- `ArtifactPointer`
- `PublicationDecision`
- `RetentionDecision`

Required pointer classes:

- candidate pointer
- published/current pointer
- baseline pointer
- superseded/archive pointer

Requirements:

- New candidates always create a revision; they never overwrite published content in place.
- Only `PublicationRetentionGate` may move the published/current pointer.
- Failed candidate or supplement runs preserve the previous published pointer.
- Baseline promotion is a separate decision and cannot be inferred from publication.
- Revision, replacement, rollback, and pointer movement must be replayable from ledger records.

Refactor direct overwrite behavior in project-scoped durable storage to use this model where a durable artifact is externally consumable.

## P0: Runtime Task Lifecycle and Recovery

Implement a generic long-running task lifecycle.

Required states:

`INTAKE`, `PLANNED`, `RUNNING`, `PAUSED`, `WAITING`, `CANCELLED`, `FAILED`, `ROLLING_BACK`, `ROLLED_BACK`, `COMPLETED`, `BLOCKED`.

Required capabilities:

- stage graph / stage checkpoints
- durable task run state
- idempotent resume after process restart
- pause, resume, cancel, retry, rollback
- task-local event ledger and action receipts
- active-run read model for UI or operator tooling
- resource/budget/timeout stop conditions

`CodexToolBridge` and future harnesses remain bounded action adapters. They must not become the lifecycle owner.

## P1: Cognitive Asset Ledger and Read-Only Projections

Implement a generic append-only `CognitiveAssetLedger` with:

- identity and revision lineage
- source/provenance and visibility boundary
- freshness, expiry, drift, quarantine, revocation, and supersession state
- candidate, published, baseline, archived, and invalidated statuses
- read-model projection hooks

Add a generic `ArtifactProjection` contract for one-way projections. Obsidian, Markdown, PDF, dashboards, and other human surfaces are adapters, not runtime truth sources and never baseline-writing authorities.

## P1: Evidence Dimension and Cbit Controls

Implement an abstract `EvidenceDimensionSpec` registry. A registered dimension may define:

- claim/support model
- freshness policy
- evidence admission requirements
- conflict strategy
- coverage object model
- Cbit gain estimate and convergence/stop condition

Core must not hard-code domain dimensions such as company funding, policy, patents, or market size. Those belong to plugins.

## P2: Persistent Read Models and Source Hygiene

Add durable read-model projections for:

- recent and active task runs
- selected workspace context
- artifact pointers and revision history
- pending repair actions
- provider invocation status

Establish source-audit exclusions for runtime outputs, return packs, caches, test artifacts, provider traces, and temporary files. Packaging must include explicit manifests and hashes without treating runtime outputs as source files.

## Non-Goals

Do not import any of the following into AgentOS Core:

- VC industry report chapters, company/funding event schemas, or industry ontology
- Kimi, DeepSeek, or other provider-specific prompt content
- report PDF styling or Markdown templates
- VC diligence workflow, investment recommendation logic, or baseline-review UI
- Obsidian folder conventions or domain-specific note layouts

These are domain plugin responsibilities.

## Acceptance Criteria

1. A provider task can be routed through two adapters with the same task contract and normalized result envelope.
2. Provider failure produces a typed recoverable outcome; no semantic output is fabricated.
3. One `ReaderIntegrityGate` failure blocks only one artifact revision and preserves the prior published pointer.
4. A `ScopeCoverageGate` finding may mark an artifact qualified without preventing it from being readable.
5. A failed supplement candidate cannot overwrite a published artifact.
6. A task paused during a stage resumes from its durable checkpoint after runtime restart.
7. Rollback restores the prior revision/pointer state and creates an audit receipt.
8. A projection adapter can render ledger-backed content without gaining mutation or baseline authority.
9. Core tests prove that no VC-specific classes, prompt strings, or report schemas are imported by the core package.
10. Existing CoreSlim regression tests remain green.

## Suggested Delivery Sequence

1. Provider execution plane plus tests.
2. QualityDecisionMatrix plus version/pointer retention model.
3. Task lifecycle, checkpoints, and recovery.
4. CognitiveAssetLedger and projection interface.
5. EvidenceDimensionSpec, Cbit convergence controls, read models, and source hygiene.

## Expected Result

The resulting AgentOS base can host VCOS, research systems, operational agents, and future domain runtimes without forcing them into local-rule-only behavior or allowing a failed candidate to corrupt a usable published state.
