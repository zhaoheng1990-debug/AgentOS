# Problem Structure Admission Runtime

AgentOS CoreSlim 0.4.0-alpha.13 closes the boundary between endogenous problem definition and
contextual organization-policy selection. A selected question is no longer assumed to carry a valid
constraint structure. The Runtime reconstructs that structure from the existing four-role problem
receipts, obtains bounded Provider support, and lets the Kernel decide whether the result may enter
the Selector.

## Object Mapping

```text
constraint-field reconstruction
        -> ProblemStructureCandidate
        -> Provider dimension assessment
        -> Kernel admission decision
        -> ContextualProblemStructure
        -> Contextual Organization Policy Selector
```

The observable proxies are the source seed hash, four formal-message hashes, four execution-receipt
hashes, evidence references, committed source signals, per-dimension uncertainty, and revision
ancestry. These are engineering correspondences, not proof that six scalar dimensions exhaust the
ontology of a problem.

## Existing Roles, New Boundary

Alpha.13 does not create another set of problem agents. `ProblemDefinitionStructureAdapter` consumes
the existing `EndogenousProblemRuntime` result only after it reaches `CANDIDATE`, retains
`PENDING_AGENDA_REVIEW`, exposes exactly the Framer, Critic, Researchability, and Agenda messages,
and passes replay.

The adapter verifies the seed, every formal message, and every execution receipt before Provider
execution. It binds the selected framing item, critique, researchability assessment, agenda choice,
rivals, unresolved conflicts, required Harnesses, and nine source signals into one immutable
`ProblemStructureCandidate`.

## Six Provider-Supported Dimensions

The Provider assesses exactly:

- premise uncertainty;
- evidence conflict;
- replication need;
- synthesis need;
- coordination complexity;
- novelty need.

Each assessment must contain a score, uncertainty, support state, rationale, admitted evidence refs,
and committed source-signal names. The Provider cannot alter the objective, source problem, project,
context, evidence surface, identities, revision ancestry, candidate state, or authorization. Unknown
fields fail the exact output contract.

## Kernel Admission

`ProblemStructureAdmissionGate` requires complete dimension coverage, `CONSISTENT` support,
dimension and global uncertainty below the configured ceilings, evidence confined to the candidate,
and dimension-specific source-signal bindings. A passing judgment forms a project-scoped
`ContextualProblemStructure`; its `structure_receipt_hash` is the Kernel decision hash.

The receipt grants only Selector input eligibility. It explicitly carries no execution, global
policy, production, accepted-knowledge, or publication authority.

## Revision And Replay

Admissions are append-only. A second structure for the same `context_key` and source problem must
name the exact latest receipt hash as `supersedes_receipt_hash`. Missing, stale, or invented
predecessors fail before Provider execution. The prior receipt remains available and the new receipt
is marked `ADMITTED_REVISION_PROJECT_SCOPED`.

`ProblemStructureRepository` stores admissions and blocked attempts in a hash-chained JSONL ledger,
reconstructs nested contracts after restart, verifies snapshots, and rejects event tampering.

## Selector Boundary

`ContextualOrganizationPolicyRuntime` accepts an optional `AdmittedProblemStructureSource`. When the
source is configured, callers must provide `problem_admission_id`; the resolver validates the full
admission receipt, Kernel decision, project, ID, and internal structure binding before use. Direct
problem objects are rejected. The compatibility path remains available only when no admission source
is configured.

## Modular Ownership

| Module | Owns |
| --- | --- |
| `problem_structure_admission_models.py` | immutable source signals, candidate, judgment, decision, and receipt contracts |
| `problem_structure_admission_gate.py` | pure Kernel evidence, signal, uncertainty, scope, and authority gates |
| `problem_structure_source_adapter.py` | verified conversion from the existing plural problem Runtime |
| `problem_structure_provider.py` | one exact-schema Provider assessment and invocation audit |
| `problem_structure_repository.py` | revision ledger, blocked events, snapshots, reconstruction, and replay |
| `problem_structure_admission.py` | thin composition facade |
| `problem_structure_source.py` | read-only Selector source port and compatibility resolver |

Architecture tests cap module growth and reject Kernel imports from Runtime, filesystem, or operating
system APIs.

## Verification

```powershell
python -m pytest -q tests/test_problem_structure_admission.py `
  tests/test_problem_structure_modularity.py `
  tests/test_problem_structure_admission_smoke.py

python examples/problem_structure_admission_smoke.py `
  --output-dir artifacts/problem-structure-admission-smoke

python examples/audit_release_artifacts.py `
  --artifact-dir artifacts/problem-structure-admission-smoke `
  --output artifacts/problem-structure-admission-audit.json
```

The deterministic smoke runs the real four-stage problem-definition state machine, admits the six
dimensions, restarts the ledger, and makes a downstream Selector consume the admitted receipt by ID.
The resulting organization policy remains exploratory because one admitted structure is not matched
execution evidence.
