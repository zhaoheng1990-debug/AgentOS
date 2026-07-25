# R1 Archived Organizational Identifiability Audit

## Window Initialization

TheoryBaseline: `COLLECTIVE_COGNITION_THEORY_BASELINE_V0_1`

MethodologyKernel: `v1.1`

This window inherits MethodologyKernel v1.1.
If any experimental conclusion conflicts with this kernel, the conflict must
be explicitly stated and converted into a theory revision, downgrade, or
caveat.

Inherited objects:

- representation quality is necessary but is not organization;
- Provider output is cognitive support, not final authority;
- correction, suppression, and abstention are different events;
- rejected historical rounds remain rejected.

Preserved caveats:

- the archive does not contain matched independent cognitive actors;
- sequential stage ablation does not identify unique role information;
- private references support retrospective internal analysis only;
- no result in R1 authorizes Runtime, CoreSlim, retention, or baseline writes.

Specific objective:

> Determine which organizational quantities are identifiable from the frozen
> v0.65, v0.82, v0.84, v0.88, and v0.89 archives before designing another
> experiment.

Object-before-proxy declaration:

```text
CognitiveOrganization
  -> frozen same-unit stage transitions
  -> correction, introduced error, retention, suppression, oracle gap,
     paired error association, and marginal token cost
```

## Status

`R1_COMPLETE_BOUNDED`

Evidence coordinate: `INTERNAL_PROJECT_EVIDENCE`

All 27 inputs matched the frozen size and SHA-256 inventory. The audit made
zero Provider calls, consumed no fresh holdout, and changed no source output.

The reproducible local outputs are under:

`outputs/r1_organizational_identifiability_v0_1/`

## Metric Contract

For one frozen case or span:

```text
CORRECTED        = upstream wrong and downstream correct
INTRODUCED_ERROR = upstream correct and downstream wrong
RETAINED_CORRECT = upstream correct and downstream correct
RETAINED_ERROR   = upstream wrong and downstream wrong
NET_TRANSITION   = CORRECTED - INTRODUCED_ERROR
ORACLE_UNION     = correct in either observed output
```

`ORACLE_UNION` is descriptive hindsight. It is not a deployable selector.

`COMPOSITION_LOSS` is reported only when the downstream output is a true
sequential extension of the upstream state. For independent alternative arms,
the final-to-oracle gap is reported but is not called causal composition loss.

Paired error phi measures association between observed upstream and downstream
errors. It does not establish independent role error correlation.

Token costs remain separate from cognitive outcomes. R1 does not collapse them
into a scalar with an arbitrary exchange rate.

## Main Results

| Round | Comparison grain | Corrected | Introduced error | Retained correct | Net | Upstream -> downstream accuracy | Incremental tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v0.65 | 36 cases | 0 | 1 | 33 | -1 | 0.944 -> 0.917 | 64,295 |
| v0.82 | 48 spans | 19 | 0 | 23 | +19 | 0.479 -> 0.875 | 22,277 |
| v0.84 | 48 spans | 0 | 4 | 39 | -4 | 0.896 -> 0.812 | 27,842 |
| v0.88 | 18 cases | 3 | 3 | 11 | 0 | 0.778 -> 0.778 | 59,084 |
| v0.89 | 18 cases | 0 | 11 | 6 | -11 | 0.944 -> 0.333 | 122,257 |

Only one of the five final comparisons has positive net correction. One is
neutral and three are negative.

## Round Findings

### v0.65: richer evidence did not conserve the decision

The staged arm improves evidence F1 on 8 cases and harms it on 2. It makes no
decision correction, introduces one wrong decision, and returns one missing
label on a case that was already wrong.

The staged arm uses 122,063 tokens versus 57,768 for the one-pass arm. The
64,295-token increase therefore buys evidence improvement without net decision
gain.

Interpretation:

`REPRESENTATION_GAIN_WITHOUT_DECISION_CONSERVATION`

### v0.82: a real local correction operator

A16 changes 19 spans. All 19 changes correct an upstream error and none damage
an upstream-correct span. It retains all 23 upstream-correct spans and repairs
19 of 25 upstream errors.

This is the only positive stage result in R1:

```text
19 net corrections / 22,277 addon tokens
= 1,172.47 tokens per observed net correction
```

The result remains local. The true `RETAIN_CONTEXT` class is still not
recovered, and the historical gate remains rejected. The archive identifies a
useful representation-stage effect, not collective cognition.

Interpretation:

`LOCAL_REPRESENTATION_OPERATOR_SUPPORTED_WITH_CLASS_BOUNDARY_FAILURE`

### v0.84: review reverses conservation

The frozen score shows that the prior atomic-to-staged step produced 18
corrections and 2 harms. A18 then changes 4 additional spans, and all 4 changes
are harmful.

The review stage preserves 39 of 43 upstream-correct spans, for a conservation
rate of 0.907. Its 27,842 tokens create no correction.

Interpretation:

`REVIEW_STAGE_ADDS_JUDGMENT_WITHOUT_CONDITIONAL_INFORMATION`

### v0.88: complementarity appears, but organization does not

The direct and EvidenceSet+ClaimScope paths each score 14/18. Their errors are
different:

- the candidate path corrects 3 direct-path errors;
- it also breaks 3 direct-path correct decisions;
- only 1 case is wrong in both paths;
- the descriptive oracle union is 17/18;
- paired error phi is 0.036.

This is the most important positive structural signal in R1. The archive
contains output-level complementarity, but it has no matched coordinator arm
that can preserve the correct parts of both paths. The candidate path also
raises sentence recall from 0.571 to 0.667 while lowering precision from 0.800
to 0.538 and adding two harmful strong candidates.

The candidate workflow uses 96,051 tokens versus 36,967 for the direct path.

Interpretation:

`COMPLEMENTARITY_POTENTIAL_WITHOUT_COORDINATOR_IDENTIFICATION`

### v0.89: safety by suppression, not correction

The binding-and-challenger addon vetoes 12 upstream actions. It removes one
harmful strong candidate, but that removal comes from fail-closed invalid
binding rather than a valid semantic correction. All 9 valid semantic vetoes
are false vetoes under the frozen reference.

The addon retains only 6 of 17 upstream-correct decisions and introduces 11
errors. Correct strong-candidate retention is 1/12. The 122,257 addon tokens
therefore identify a suppression mechanism with severe conservation failure.

Interpretation:

`SAFETY_GAIN_BY_CORRECT_ACTION_SUPPRESSION`

This triggers mandatory theory review under
`THEORY_FIRST_RESEARCH_POLICY.json`.

## Theory Variable Update

### `R`: representation adequacy

Status: `HETEROGENEOUS_LOCAL_EFFECT_IDENTIFIED`

Representation can create large local gains, as in v0.82. More representation
stages do not monotonically improve the final answer. `R` is a prerequisite,
not an organization metric.

### `U`: unique conditional role information

Status: `NOT_IDENTIFIABLE`

The roles are sequential, share upstream framing, and usually judge different
objects. They do not provide blind, commensurate judgments under matched
information and matched budget. R1 identifies stage effects only.

### `K`: composition fidelity

Status: `PARTIALLY_IDENTIFIED`

The archive identifies conservation as an independent bottleneck:

- v0.82 preserves all upstream-correct spans;
- v0.84 loses 4 of 43 upstream-correct spans;
- v0.89 loses 11 of 17 upstream-correct cases.

A stage can be semantically elaborate while having low `K`.

### `E`: error dependence

Status: `OUTPUT_ASSOCIATION_ONLY`

Paired error phi is computable, but the actors are not independent. The low
v0.88 value is evidence of output complementarity, not proof of role
independence.

### `F`: coordination friction

Status: `OPERATIONAL_COST_IDENTIFIED_SEMANTIC_FRICTION_PARTIAL`

Every added workflow costs more tokens. Four of five final comparisons have
nonpositive net correction. Cost is not the primary failure in v0.84 or v0.89;
the primary failure is that added judgment is not conserved or is actively
harmful.

## Rival Explanations Preserved

1. `PIPELINE_DEPTH_NULL`: effects come from different prompts and extra
   computation, not organization.
2. `REPRESENTATION_ONLY`: the best local stage explains all gains; roles add no
   unique conditional information.
3. `SUPPRESSION_ONLY`: apparent safety comes from abstention or veto, with
   correct-action retention collapse.
4. `DIVERSITY_WITHOUT_COMPOSITION`: members have complementary errors, but the
   coordinator cannot identify and conserve the useful differences.
5. `COGNITIVE_ORGANIZATION`: independent conditional information is preserved
   by a coordinator and produces net Cbit beyond the best matched member.

R1 cannot discriminate model 5 from all rivals.

## Closure

Accepted bounded object:

> A cognitive organization requires both conditional role information and a
> conservation-capable coordinator. Role count, workflow depth, and semantic
> receipt count are not sufficient proxies.

Revised over-strong object:

> The archived multi-stage workflows do not demonstrate positive collective
> cognition.

Boundary:

- no best-member superiority estimate;
- no independent role error-correlation estimate;
- no unique role information estimate;
- no coordinator synergy estimate;
- no fresh-task generalization claim.

Baseline insertion:

`THEORY_FIRST_RESET_RESEARCH_LAYER_ONLY`

No Runtime, CoreSlim, retention, or production baseline update is justified.

Next unresolved object:

`R2_ORGANIZATION_THEORY_PACKET`
