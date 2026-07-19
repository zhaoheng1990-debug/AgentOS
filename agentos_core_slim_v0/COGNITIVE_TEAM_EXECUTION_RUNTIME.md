# Cognitive Team Execution Runtime

AgentOS CoreSlim 0.4.0-alpha.6 turns a Kernel-authorized team formation decision into an actual, replayable cognitive trial. It executes a best-member arm, a fixed four-role team, and a dynamically formed four-role team under one evidence surface, budget, finding protocol, and Harness.

## Ownership boundary

Team Formation owns who may execute. The Execution Runtime binds those authorized registry descriptors to isolated agents and runs the trial. Providers support role cognition, coordination, candidate normalization, and blinded semantic quality assessment. The Kernel owns authorization, evidence scope, budgets, replay admission, conflict boundaries, and candidate state.

The hidden finding truth belongs only to `FrozenFindingTrialHarness`. Providers receive the public finding catalog and evidence, never `expected_state` or an arm identity. The Harness mechanically computes finding accuracy, rejection accuracy, uncertainty preservation, observed Cbit, error correction, negative-transfer interception, normalized cost, and convergence steps.

## Three-arm protocol

1. **Best member**: one independently selected baseline agent answers the frozen trial through its bound Provider.
2. **Fixed team**: a stable Generator, Reviewer, Replicator, and Synthesizer execute through isolated contexts and formal messages.
3. **Dynamic team**: the Kernel-authorized formation assignment executes the same four-role protocol.
4. Both team arms use the same coordination contract when coordination is enabled.
5. A synthesizer-bound Provider normalizes formal team receipts into the public finding schema.
6. Every arm is replay-verified again immediately before Harness evaluation.
7. Semantic assessment receives an opaque arm ID and cannot see agent, subject, or arm identity.
8. The deterministic evaluator compares the dynamic team with both baselines after quality, observed Cbit, correction, interception, cost, and convergence are admitted.
9. Credit is recorded separately for the best member, fixed team, dynamic team, and formation Provider. It remains advisory and has no route-selection authority.

## Fail-closed invariants

- An execution trial must match the exact Kernel-authorized budget, project scope, and evidence coordinate.
- Team adapters must cover exactly the authorized fixed and dynamic member IDs; normalizers must match the selected synthesizers.
- Agent Provider/model binding is checked from invocation receipts.
- Candidate finding IDs must cover the public catalog exactly once.
- Provider-cited evidence must be a non-empty subset of admitted evidence; the Runtime mechanically binds the complete frozen evidence surface.
- Hidden truth and acceptance, publication, permission, or route-selection claims are forbidden in Provider candidates.
- Solo and team event stores are hash chained. A replay failure blocks evaluation and credit.
- Provider semantic assessment may not alter Harness-owned metrics.

## Project-source evidence

The repeatable smoke runner is `examples/cognitive_team_execution_project_source_smoke.py`. It reads three frozen source coordinates: LIFE-Cog3R, MATH_CBIT1, and OCS1R2. Scripted fixture mode validates the full control path and artifact contract. Live mode uses external Provider calls for role work, coordination, normalization, and blind assessment.

The first complete LIFE-Cog3R live run made 27 Provider calls and passed all runtime gates. Its result was negative: best-member observed Cbit was `1.00`, while both team arms scored `0.60`; after semantic quality and cost, the dynamic team underperformed the best member by `0.5375` and the fixed team by `0.13`. This is evidence that the Runtime can expose and penalize failed cognitive multiplication, not evidence that multi-Agent cognition already outperforms its best member.

The successful live run used independent roles and two DeepSeek model bindings after a separate preserved Moonshot run failed twice with `PROVIDER_UNAVAILABLE`. It therefore validates live multi-role execution, not live multi-provider robustness.

## Verification

```powershell
pytest -q tests/test_cognitive_team_execution_runtime.py
pytest -q tests/test_cognitive_team_execution_project_source_smoke.py
python examples/cognitive_team_execution_project_source_smoke.py --case life-cog3r --provider-mode scripted
```
