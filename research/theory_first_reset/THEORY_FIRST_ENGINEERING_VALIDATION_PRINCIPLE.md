# Theory-First, Engineering-Validation Research Principle

## Status

`ACTIVE_RESEARCH_GOVERNANCE`

## Constitutional Rule

AgentOS research follows this order:

```text
Theory Research
  -> Theory Freeze
  -> Engineering Derivation
  -> Validation Preregistration
  -> Minimal Engineering Instrument
  -> Empirical Validation
  -> Theory Update
  -> Promotion Review
```

Engineering does not generate architecture by accumulating fixes around
observed failures. It implements the smallest instrument needed to discriminate
a frozen theory from its rivals.

## 1. Theory Research Comes First

Before any new role, module, receipt, compiler, state, metric, or Provider
workflow is implemented, the research window must define:

1. ontology-level research object;
2. boundary and excluded claims;
3. current theory baseline;
4. causal mechanism;
5. theory variables and relations;
6. leading and rival models;
7. discriminating predictions;
8. falsification conditions;
9. observable proxies and their validity limits;
10. expected theoretical Cbit gain;
11. Anti-Additive and ObjectUpgrading audits;
12. evidence needed to choose among the models.

If these objects are not sufficiently defined, the authorized work remains
theoretical research. Lack of a theory object is not permission to discover
one by adding code.

## 2. Theory Freeze Gate

A theory packet moves through:

```text
DRAFT
  -> REVIEW_READY
  -> FROZEN_FOR_ENGINEERING_VALIDATION
  -> VALIDATED | REVISED | REJECTED | INCONCLUSIVE
```

`FROZEN_FOR_ENGINEERING_VALIDATION` requires:

- the object chain is explicit:
  `UpperOntologyObject -> ProjectObject -> ObservableProxy -> Metric`;
- at least one live rival or null model exists;
- predictions distinguish the models;
- evidence that would reject the leading model is named;
- measurement and proxy limits are explicit;
- expected effective-Cbit gain exceeds proposed complexity cost;
- implementation variables are derivable from theory variables;
- the experiment has a stop and rollback condition;
- PM/HumanGate review explicitly approves the freeze.

No autonomous Runtime, Provider, Harness, or test result can grant this status.

## 3. Engineering Is a Validation Instrument

After theory freeze, engineering may:

- encode frozen theory variables;
- collect declared observables;
- enforce evidence, safety, replay, and no-write boundaries;
- implement the smallest discriminating arms;
- record costs, failures, and provenance;
- mechanically evaluate preregistered conditions.

Engineering may not:

- add a role because a prior role performed poorly;
- add a field because a case was misclassified;
- introduce a threshold after labels are revealed;
- change the target object to fit available code;
- treat schema validity as theory confirmation;
- use a benchmark metric as an ontology definition;
- convert fail-closed suppression into semantic correction;
- broaden a Runtime merely to make the experiment more feature-complete.

Every implementation object must trace to one frozen theory variable or one
mechanical governance obligation. Unmapped objects are unauthorized.

## 4. Theory-to-Engineering Derivation Contract

Each engineering object must have:

| Field | Requirement |
| --- | --- |
| Theory variable | The exact frozen object it instantiates or measures |
| Validation role | Which rival prediction it helps distinguish |
| Minimality | Why a smaller instrument is insufficient |
| Observable | What it records without interpreting beyond authority |
| Failure meaning | Mechanical failure, proxy failure, or theory evidence |
| Removal test | What is lost when the object is ablated |
| Authority | Candidate-only, no-write, and promotion boundary |

An object without a removal test or discriminating role is presumed
anti-additive.

## 5. Change Classification During Validation

### Class A: Mechanical Amendment

Allowed only when all are true:

- no Provider call or hidden-label exposure occurred for the affected arm;
- theory object, prediction, prompt semantics, schema semantics, metric, gate,
  holdout, and arm comparison remain unchanged;
- the defect is transport, serialization, path, import, or equivalent
  mechanical execution;
- old and new hashes and the amendment reason are preserved.

### Class B: Theory-Relevant Change

Any change to semantic fields, role access, prompt meaning, compiler policy,
threshold, metric, gate, evidence surface, or causal comparison is
theory-relevant.

It requires:

1. close the current version without repair;
2. update or revise the theory packet;
3. run Anti-Additive/ObjectUpgrading review;
4. freeze a new validation version;
5. use an eligible fresh surface where required.

Class B changes cannot be disguised as bug fixes.

## 6. Result Interpretation

Engineering validation produces observations. It does not directly produce
new architecture.

Every closure must separate:

1. formal facts;
2. observed phenomena;
3. mechanism inference;
4. rival explanations;
5. negative and counterintuitive results;
6. theory objects accepted, revised, rejected, or pending;
7. proxy and evidence-coordinate limits;
8. residual uncertainty;
9. next theoretical object.

Only after this theory update may another engineering validation be proposed.

The loop is:

```text
Observation
  -> Theory Possibility-Space Reduction
  -> Theory Revision or Retention
  -> New Prediction
  -> New Validation Design
```

It is not:

```text
Failure -> Patch -> New Failure -> Patch
```

## 7. Stop and Rollback Rules

Immediately stop engineering expansion when:

- the failure is at a different ontology level than the current proxy;
- two consecutive fixes move the bottleneck without reducing explanation
  complexity;
- a new stage adds cost without identifiable conditional information;
- a safety gain comes only from suppressing correct action;
- the experiment cannot distinguish its leading and rival models;
- baseline writeback requires growing caveats or exceptions.

The response is theory review or ObjectUpgradingAudit. The response is not a
larger Runtime.

Rollback returns engineering authority to the last theory-frozen,
replay-valid base while preserving all later observations as historical
evidence.

## 8. Provider, Runtime, and Harness Roles

- **Runtime:** cognitive subject; owns goals, object boundaries, composition,
  conflict, stopping, and candidate state.
- **Provider:** bounded semantic support for theory-defined operations.
- **Harness:** evidence access, execution, hidden references, and mechanical
  measurement.
- **Kernel:** safety, capability, state-transition, rollback, and final
  authority boundaries.
- **PM/HumanGate:** freezes theory and approves any promotion boundary.

Provider weakness may invalidate an instantiation without falsifying the
theory. Runtime correctness may preserve safety without demonstrating
cognitive gain.

## 9. Current AgentOS Application

The current authorized stage is R1:

`ARCHIVED_ORGANIZATIONAL_IDENTIFIABILITY_AUDIT`

R1 is theoretical evidence reconstruction and model identifiability analysis.
It makes zero Provider calls and introduces no Runtime modules.

After R1:

1. R2 freezes the organization theory packet;
2. R3 builds the minimum synthetic validation instrument;
3. R4 tests Provider adequacy;
4. R5 performs fresh matched-budget validation;
5. only positive theory-linked evidence can authorize a modular AgentOS
   candidate.

No v0.90 repair, new role, or fresh holdout is currently authorized.
