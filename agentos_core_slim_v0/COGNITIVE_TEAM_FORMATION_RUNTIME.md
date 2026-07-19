# Cognitive Team Formation Runtime

AgentOS CoreSlim 0.4.0-alpha.5 added a Provider-supported, Kernel-authorized runtime for forming a cognitive team around a specific problem. Alpha.6 now consumes that authorization in the separate execution runtime documented in `COGNITIVE_TEAM_EXECUTION_RUNTIME.md`.

## Runtime boundary

The Provider proposes which registered agents fit the problem. It may use role capability, context independence, provider diversity, scope, cost, risk, and advisory credit. It cannot register identities, grant execution authority, alter the budget, or decide final epistemic state.

The Kernel validates every selected ID against `AgentRegistry`, canonicalizes the team into required-role order, checks capability and evidence scope, enforces context and provider diversity, and issues a separate authorization receipt. A proposal remains non-executing until that gate passes.

## Lifecycle

1. Two or more `PROBLEM_FRAMER` agents receive the same complete evidence surface in isolated contexts. They do not see a seeded candidate question or peer output.
2. Each Provider returns one falsifiable candidate with a receipt-level Provider/model binding.
3. A formation Provider sees registered public profiles and proposes exactly one agent per required role.
4. The Kernel validates the proposal and freezes an authorized team and budget.
5. The Runtime records three equal-protocol arms: best independent member, fixed team, and dynamic team.
6. Provider semantic assessment supports each arm, while the Harness owns observed Cbit, normalized cost, convergence steps, evidence, and protocol identity.
7. A deterministic evaluator compares the dynamic team against both baselines.
8. The credit ledger records the best member as an `agent` subject and the selected combination as a `team` subject. Pure parity is neutral and does not earn positive team credit. Neither profile has route-selection authority.

## Fail-closed invariants

- Unknown, disabled, role-mismatched, capability-mismatched, or out-of-scope agent IDs are rejected.
- Baseline Providers and models must match immutable invocation receipts, not model-authored fields.
- Every independent baseline and proposal must cover the same complete admitted-evidence set.
- Provider output cannot carry acceptance, publication, permission, execution, or route-selection authority.
- Counterfactual arms must share trial ID, Harness protocol, budget hash, and evidence.
- Provider-backed observations must be recorded by the same Runtime; a receipt-looking string is insufficient.
- Provider changes to Harness-owned Cbit, cost, or convergence values are rejected.

## Current evidence boundary

The LIFE-COG3R live smoke generated independent DeepSeek and Kimi problem baselines, formed a role-complete two-provider team, passed Kernel authorization, and completed the three-arm formation-readiness comparison. All arms were at parity and observed Cbit was frozen at zero because no downstream research experiment was run.

Alpha.6 completed that next control-path step on LIFE-Cog3R, MATH_CBIT1, and OCS1R2 project sources. The first live LIFE-Cog3R trial did not show cognitive multiplication: the dynamic team underperformed both baselines after cost. Repeated cross-provider and cross-project live trials remain necessary before any performance claim.
