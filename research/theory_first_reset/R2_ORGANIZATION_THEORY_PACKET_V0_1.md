# R2 Cognitive Organization Theory Packet v0.1

## Status

`THEORY_CANDIDATE_PENDING_HUMAN_FREEZE`

This packet is a theory product. It does not authorize R3 engineering,
Provider calls, fresh holdout consumption, Runtime changes, or baseline
promotion.

## Inheritance

TheoryBaseline: `COLLECTIVE_COGNITION_THEORY_BASELINE_V0_1`

MethodologyKernel: `v1.1`

R1 evidence:

- local representation correction is possible;
- representation gain can fail to reach the final decision;
- complementary errors can exist without a preserving coordinator;
- suppression can reduce harm while destroying correct-action retention;
- unique role information and coordinator synergy remain unidentified.

## Ontology Object

```text
CognitiveOrganization
= cognitively nonredundant role instances
+ explicit composition process
+ bounded stopping rule
```

The organization claim is earned only when the composed system produces
positive task Cbit beyond both:

1. the best matched individual member;
2. a matched-budget single-agent iteration control.

More agents, more stages, more receipts, or more tokens do not define an
organization.

## Excluded Claims

This packet does not claim that:

- role prompts create independent cognitive actors;
- different stage names imply unique role information;
- an oracle union is a realizable coordinator;
- abstention is a correction;
- lower harm alone implies higher cognition;
- synthetic phase behavior establishes benchmark or real-world transfer;
- endogenous problem generation is solved.

Problem definition and agenda emergence are held fixed in R3 so that
organization can be identified before discovery is added.

## Minimal Variables

### `R_i`: role representation adequacy

The ability of role `i` to represent the frozen object and produce a calibrated
judgment over the shared decision contract.

`R_i` is measured before coordination.

### `U_i`: unique conditional role information

The out-of-sample reduction in uncertainty provided by role `i` after the
other role outputs are known.

Operationally:

```text
U_i = CE(Y | roles without i) - CE(Y | all roles)
```

The estimate must use held-out or cross-fitted data. In-sample improvement does
not count.

### `E`: role error dependence

The dependence among blind role errors on the same object under matched
evidence access.

Low correlation is not automatically useful. It matters only when the
differences contain reference-relevant information and can be composed.

### `K`: coordinator composition fidelity

The coordinator's ability to preserve valid member contributions, reject
invalid contributions, preserve unresolved disagreement, and avoid inventing
new unsupported claims.

Minimum readbacks:

```text
correct_retention = upstream-correct contributions preserved / available
correction_surplus = final corrections - final introduced errors
oracle_capture = final gain / descriptive oracle-union gain
unsupported_addition = new unsupported final claims
```

`oracle_capture` is diagnostic only. The oracle cannot be used as a policy.

### `F`: coordination friction

Token use, latency, message count, invalid packet rate, information loss, and
premature convergence introduced by collaboration.

Cost is reported as a Pareto coordinate. It is not subtracted from Cbit with an
unfrozen arbitrary coefficient.

### `T`: number of cognitive rounds

The number of role-coordinator iterations. `T` tests the hypothesis that a
small-model group may reach a similar cognitive quantity through more
iterations than a larger individual model.

The stopping object is:

```text
continue iff expected marginal task Cbit is positive
             and safety and budget boundaries remain satisfied
```

## Causal Mechanism

Leading model:

```text
object held fixed
  -> roles obtain partially nonredundant evidence-conditioned judgments
  -> structured disagreement exposes correctable uncertainty
  -> coordinator conserves valid contributions and unresolved conflict
  -> later rounds target residual uncertainty
  -> cumulative task Cbit exceeds matched individual controls
```

Necessary conditions:

```text
some U_i > 0
K above the conservation boundary
E not perfectly redundant
F below the available gain
T stops before marginal gain becomes nonpositive
```

## Rival Models

### H0: compute-depth equivalence

A matched-token single agent equals or exceeds the coordinated group.

Signature:

`GROUP_GAIN_DISAPPEARS_UNDER_MATCHED_BUDGET`

### H1: representation-only

The best role's `R_i` explains all performance. Other roles add no conditional
information.

Signature:

`U_i_APPROX_ZERO_AFTER_BEST_ROLE`

### H2: suppression-only safety

The group lowers harmful strong outputs by vetoing or abstaining broadly.

Signature:

`HARM_DOWN_AND_CORRECT_RETENTION_COLLAPSES`

### H3: diversity without composition

Roles make complementary errors, but the coordinator fails to preserve the
useful differences.

Signature:

`ORACLE_UNION_HIGH_AND_FINAL_GAIN_LOW`

### H4: cognitive organization

At least one role provides positive conditional information, and coordination
captures it without unacceptable harm or retention loss.

Signature:

`POSITIVE_OUT_OF_SAMPLE_U_AND_POSITIVE_COORDINATED_CBIT`

## Discriminating Predictions

1. When `U` is zero, increasing role count or rounds cannot create stable gain
   beyond matched single-agent iteration.
2. When `U` is positive but `K` is low, oracle-union potential rises while
   final performance remains flat or declines.
3. When `K` rises above a boundary, correct retention and oracle capture improve
   together rather than through broad suppression.
4. Increasing `T` initially accumulates Cbit, then reaches a plateau or turns
   negative as friction and correlated error dominate.
5. A suppression-only control can reduce harm but cannot satisfy both positive
   correction surplus and correct-retention constraints.

## R3 Minimal Synthetic Design

Vary only:

- conditional role information overlap;
- role error dependence;
- coordinator fidelity;
- communication cost;
- cognitive rounds.

Required arms:

1. best single member;
2. matched-budget single-agent iteration;
3. independent uncoordinated roles;
4. coordinated roles;
5. suppression-only control;
6. descriptive oracle union, never used for action.

Required outputs:

- proper-score task Cbit;
- hard-decision correction surplus;
- correct retention;
- harmful strong decisions;
- `U_i` estimates;
- paired error dependence;
- coordinator conservation and oracle capture;
- token, latency, and message cost;
- marginal gain by round.

## Falsification Conditions

The leading model is rejected or revised if any of the following holds:

1. coordinated roles do not exceed matched-budget single-agent iteration when
   synthetic `U` is known positive and `K` is controlled high;
2. estimated `U_i` does not track the injected conditional information;
3. coordinator fidelity has no discriminating effect on oracle capture;
4. apparent gain depends on suppression while correct retention collapses;
5. more rounds improve the score without any measurable reduction in residual
   uncertainty;
6. the result requires adding domain-specific exception rules.

## Anti-Additive Audit

Only five causal variables are admitted: `R/U`, `E`, `K`, `F`, and `T`.

No domain middleware, role registry, reputation ledger, agenda generator,
retention promotion, or Provider-specific adapter is eligible in R3.

Removal test:

- remove `U`: cannot distinguish useful role information from role count;
- remove `E`: cannot distinguish complementarity from redundancy;
- remove `K`: cannot explain v0.88-like oracle potential or v0.89-like loss;
- remove `F`: cannot locate the gain-cost boundary;
- remove `T`: cannot test iterative cognitive accumulation.

No additional variable is justified before one of these fails to explain a
preregistered observation.

## Stop And Rollback

Stop R3 and return to theory if:

- injected variables cannot be recovered by the chosen proxies;
- rival signatures are not discriminable;
- two consecutive failures migrate to a new proxy;
- the implementation needs benchmark-specific exceptions;
- a safety gain is obtained only by correct-action suppression.

Rollback target:

`R2_THEORY_ONLY_NO_ENGINEERING_AUTHORITY`

## Freeze Gate

Before R3, HumanGate must explicitly review:

- the definition of task Cbit;
- how `U_i` is estimated;
- the coordinator conservation metric;
- the cost budget and reporting rule;
- quantitative pass, fail, and retention thresholds;
- synthetic data generation and seed policy;
- stopping and rollback conditions.

Until then:

`NO_ENGINEERING_AUTHORITY`
