# Problem Quality Lifecycle Runtime

AgentOS CoreSlim 0.4.0-alpha.4 connects endogenous problem definition to an
observable learning loop. A generated question is no longer treated as valuable
because the group selected it. Its quality is predicted before execution,
tested under explicit Kernel authority, compared with observed information gain,
and fed back into the agenda and credit systems.

## Responsibilities

| Component | Owns | Does not own |
| --- | --- | --- |
| Provider quality assessment | semantic scores and rationale for one blinded problem | comparison, authorization, or promotion |
| `ProblemQualityEvalHarness` | deterministic score composition and baseline comparison | semantic judgment |
| `ProblemQualityLifecycleRuntime` | frozen forecast, lifecycle state, receipts, replay | self-authorization or publication |
| Independent Harness | bounded trial evidence and execution receipt | semantic outcome or final state |
| Provider outcome interpretation | observed Cbit, rival reduction, residual problems, risk | terminal state authority |
| Kernel feedback bridge | agenda, credit, residual problem, and invalidation updates | automatic route selection |

## Prospective Comparison

Every problem receives provider-backed scores for evidence grounding, premise
soundness, novelty, falsifiability, discriminatory power, Harness feasibility,
expected Cbit, normalized cost, and negative-transfer risk. Provider inputs use
opaque candidate IDs and omit `source_kind` and `source_subject_id`.

The deterministic evaluator requires exactly one group problem, at least one
member baseline, and at least one human baseline. It freezes the observations,
calculates the group delta against both baselines, and emits no execution
authority. A result can be `OUTPERFORMS`, `AT_PARITY`, or `UNDERPERFORMS`; one
trial does not establish a general ordering.

## Trial Lifecycle

```text
PENDING_AGENDA_REVIEW
          |
          | frozen quality evaluation + Kernel review
          v
APPROVED_FOR_TRIAL
          |
          | Kernel execution authorization + required Harness receipts
          v
        ACTIVE
          |
          | provider-backed interpretation of admitted trial evidence
          v
 RESOLVED | PARTIAL | INVALIDATED
```

The pending seed cannot activate itself. Approval requires the Harness set
declared by the seed, measurable outcomes, stop conditions, a budget, and a
rollback reference. Activation requires a separate Kernel authorization and a
distinct receipt for every required Harness.

An outcome receipt remains candidate-only. It records expected and Harness-measured
Cbit, prediction error, reduced rivals, residual problems, cost, negative
transfer, independent replication, provider provenance, and admitted evidence.
Residual problem IDs must be new, and a rival claimed as reduced cannot reappear
inside a residual problem. The Provider must return the exact Cbit value frozen
by the Harness measurement; a mismatch blocks the outcome.

When the prospective quality gate fails, the Kernel may issue a pre-trial
rejection receipt and move the problem to `INVALIDATED`. This path records no
observed Cbit because no trial occurred.

## Feedback

A terminal outcome can update four bounded stores:

- `EndogenousAgendaLoop` resolves, reopens, or invalidates the original problem;
- `CreditLedger` records whether the prospective forecast was calibrated;
- residual `OpenProblem` objects return to the problem space;
- `CascadingInvalidationGraph` blocks reuse when a problem is invalidated.

The feedback receipt has no route-selection authority. A subsequent problem or
trial still requires normal agenda and Kernel gates.

## Live Evidence

The LIFE-COG3R project-source smoke compared one group-selected question, two
raw Framer candidates, and one PM-derived human baseline under blinded provider
assessment. A Kernel-authorized source Harness independently parsed 12 negative
control rows as 7 pass and 5 fail. A frozen source-replay proxy measured Cbit
`0.50` against an expected `0.85`; the Provider returned the same value under a
consistency assertion. The runtime retained the problem as `PARTIAL` and
returned three residual problems. Repeated runs also exercised the pre-trial
quality-rejection path. This is evidence that the feedback loop works, not that
the current rating or Cbit proxy is universally calibrated.

Run the focused tests and live workflow from `agentos_core_slim_v0`:

```powershell
pytest -q tests/test_problem_quality_lifecycle.py
python examples/problem_quality_lifecycle_project_source_smoke.py
```

The live command requires `DEEPSEEK_API_KEY` and the archived LIFE-COG3R source
pack used by the existing project-source smoke examples.
