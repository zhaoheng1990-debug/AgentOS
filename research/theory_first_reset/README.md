# AgentOS Collective Cognition Theory-First Reset

## Status

`THEORY_FIRST_BASELINE_CANDIDATE`

This directory is the active research entry after the non-destructive rollback
from the v0.89 experiment branch.

The rollback does not erase experiments. It separates three things that had
gradually become conflated:

1. immutable observations produced by experiments;
2. candidate theoretical interpretations;
3. engineering objects that have earned implementation authority.

Only the first category is inherited without qualification. The theory in this
directory remains a reviewable candidate. No new role, receipt, compiler,
runtime, CoreSlim write, retention write, or production behavior is authorized.

## Rollback Coordinate

- active Git base: `af0cef20eaab9debf040b643c48a01995ba58e14`
- base meaning: v0.65 benchmark-bridge closure
- archived experiment tip:
  `14e1a60ec27c13d1a321038d35c475a5d5f2f370`
- archived branch: `codex/v0.89-claim-atom-binding`
- new branch: `codex/theory-first-reset-v0.65`

The active base preserves the last clean external benchmark result before the
v0.66-v0.75 surface-repair chain. Later evidence is cited by immutable commit
and blob identity, but its candidate code is not part of this branch.

## Read Order

1. `EXPERIMENT_RETROSPECTIVE_V0_65_TO_V0_89.md`
2. `PER_ROUND_THEORY_MODELS_V0_1.md`
3. `PRE_V0_64_PROVENANCE_BOUNDARY.md`
4. `SERIES_THEORY_REANALYSIS_V0_1.md`
5. `THEORY_FIRST_ENGINEERING_VALIDATION_PRINCIPLE.md`
6. `THEORY_FIRST_RESEARCH_POLICY.json`
7. `COLLECTIVE_COGNITION_THEORY_BASELINE_V0_1.md`
8. `THEORY_RESEARCH_ROADMAP_V0_2.md`
9. `R1_IDENTIFIABILITY_PREFLIGHT.md`
10. `R1_ARCHIVE_INPUT_MANIFEST.json`
11. `R1_ORGANIZATIONAL_IDENTIFIABILITY_AUDIT.md`
12. `R1_VERIFICATION_REPORT.md`
13. `R2_ORGANIZATION_THEORY_PACKET_V0_1.md`
14. `R2_SYMBOL_AND_PROXY_AUDIT.md`
15. `R2_ORGANIZATION_THEORY_PACKET_V0_2.md`
16. `R2_FORMAL_VERIFICATION_REPORT.md`
17. `R2_HUMAN_GATE_FREEZE_RECEIPT.json`
18. `R3_MINIMAL_SYNTHETIC_PREREGISTRATION_V0_1.md`
19. `R3_MINIMAL_SYNTHETIC_CLOSURE_V0_1.md`
20. `R4_PROVIDER_AUTHORIZATION_RECEIPT.json`
21. `R4_PROVIDER_ADEQUACY_PREREGISTRATION_V0_1.md`
22. `R4_PROVIDER_ADEQUACY_CLOSURE_V0_1.md`
23. `R4_MINIMAL_SUFFICIENT_RECEIPT_THEORY_V0_2.md`
24. `R4_PROVIDER_PROTOCOL_DIAGNOSTIC_AUTHORIZATION_V0_2.json`
25. `R4_PROVIDER_ADEQUACY_PREREGISTRATION_V0_2.md`
26. `R4_PROVIDER_ADEQUACY_CLOSURE_V0_2.md`
27. `R4_SEMANTIC_RELATION_COMPOSITION_THEORY_V0_3.md`
28. `R4_ENGINEERING_OBJECT_MAP_V0_3.md`
29. `R4_RELATION_BOUNDARY_AUTHORIZATION_V0_3A.json`
30. `R4_RELATION_BOUNDARY_SYNTHETIC_PREREGISTRATION_V0_3A.md`
31. `R4_RELATION_BOUNDARY_SYNTHETIC_CLOSURE_V0_3A.md`
32. `R4_PROVIDER_SEMANTIC_RELATION_AUTHORIZATION_V0_3B.json`
33. `R4_PROVIDER_SEMANTIC_RELATION_PREREGISTRATION_V0_3B.md`
34. `R4_PROVIDER_SEMANTIC_RELATION_CORPUS_MANIFEST_V0_3B.json`
35. `R4_PROVIDER_SEMANTIC_RELATION_CLOSURE_V0_3B.md`
36. `R4_RECEIPT_ENVELOPE_CANONICALIZATION_THEORY_V0_3C.md`
37. `R4_RECEIPT_ENVELOPE_CANONICALIZATION_AUTHORIZATION_V0_3C.json`
38. `R4_RECEIPT_ENVELOPE_CANONICALIZATION_PREREGISTRATION_V0_3C.md`
39. `R4_RECEIPT_ENVELOPE_CANONICALIZATION_CLOSURE_V0_3C.md`
40. `R4_HYBRID_PRESENTATION_ROBUSTNESS_THEORY_V0_3D.md`
41. `R4_HYBRID_PRESENTATION_ROBUSTNESS_AUTHORIZATION_V0_3D.json`
42. `R4_HYBRID_PRESENTATION_ROBUSTNESS_PREREGISTRATION_V0_3D.md`
43. `R4_HYBRID_PRESENTATION_IMPLEMENTATION_MANIFEST_V0_3D.json`
44. `R4_HYBRID_PRESENTATION_ROBUSTNESS_CLOSURE_V0_3D.md`
45. `R4_FRESH_HARD_RELATION_GENERALIZATION_THEORY_V0_3E.md`
46. `R4_FRESH_HARD_RELATION_GENERALIZATION_AUTHORIZATION_V0_3E.json`
47. `R4_FRESH_HARD_RELATION_GENERALIZATION_PREREGISTRATION_V0_3E.md`
48. `R4_FRESH_HARD_RELATION_CORPUS_MANIFEST_V0_3E.json`
49. `R4_FRESH_HARD_RELATION_GENERALIZATION_CLOSURE_V0_3E.md`
50. `R4_EVIDENCE_TRANSFORMATION_EQUIVALENCE_THEORY_V0_3F.md`
51. `R4_EVIDENCE_TRANSFORMATION_EQUIVALENCE_AUTHORIZATION_V0_3F.json`
52. `R4_EVIDENCE_TRANSFORMATION_EQUIVALENCE_PREREGISTRATION_V0_3F.md`
53. `R4_EVIDENCE_TRANSFORMATION_EQUIVALENCE_CLOSURE_V0_3F.md`
54. `R4_PROVIDER_TRANSFORMATION_ATTRIBUTE_INFERENCE_THEORY_V0_3G.md`
55. `R4_PROVIDER_TRANSFORMATION_ATTRIBUTE_INFERENCE_AUTHORIZATION_V0_3G.json`
56. `R4_PROVIDER_TRANSFORMATION_ATTRIBUTE_INFERENCE_PREREGISTRATION_V0_3G.md`
57. `R4_PROVIDER_TRANSFORMATION_ATTRIBUTE_INFERENCE_CORPUS_MANIFEST_V0_3G.json`
58. `R4_PROVIDER_TRANSFORMATION_ATTRIBUTE_INFERENCE_CLOSURE_V0_3G.md`
59. `R4_TRANSFORMATION_SEMANTICS_FACTORIZATION_THEORY_V0_3H.md`
60. `R4_TRANSFORMATION_SEMANTICS_FACTORIZATION_AUTHORIZATION_V0_3H.json`
61. `R4_TRANSFORMATION_SEMANTICS_FACTORIZATION_PREREGISTRATION_V0_3H.md`
62. `R4_TRANSFORMATION_SEMANTICS_FACTORIZATION_CLOSURE_V0_3H.md`
63. `R4_TRANSFORMATION_SEMANTICS_FACTORIZATION_VALIDATION_AUTHORIZATION_V0_3I.json`
64. `R4_TRANSFORMATION_SEMANTICS_FACTORIZATION_VALIDATION_PREREGISTRATION_V0_3I.md`
65. `R4_TRANSFORMATION_SEMANTICS_FACTORIZATION_VALIDATION_MANIFEST_V0_3I.json`
66. `R4_TRANSFORMATION_SEMANTICS_FACTORIZATION_VALIDATION_CLOSURE_V0_3I.md`
67. `R4_FACTORIZATION_CAUSAL_BENEFIT_THEORY_V0_3J.md`
68. `R4_FACTORIZATION_CAUSAL_BENEFIT_AUTHORIZATION_V0_3J.json`
69. `R4_FACTORIZATION_CAUSAL_BENEFIT_PREREGISTRATION_V0_3J.md`
70. `R4_FACTORIZATION_CAUSAL_BENEFIT_CORPUS_MANIFEST_V0_3J.json`
71. `R4_FACTORIZATION_CAUSAL_BENEFIT_CLOSURE_V0_3J.md`
72. `R4_ROLE_DECOMPOSED_SEMANTIC_INFERENCE_THEORY_V0_3K.md`
73. `R4_ROLE_DECOMPOSED_SEMANTIC_INFERENCE_AUTHORIZATION_V0_3K.json`
74. `R4_ROLE_DECOMPOSED_SEMANTIC_INFERENCE_PREREGISTRATION_V0_3K.md`
75. `THEORY_PACKET_TEMPLATE.md`
76. `ROLLBACK_POINTER.json`

## Research Boundary

Until a theory packet passes review:

- Provider calls are paused;
- fresh holdouts remain untouched;
- no benchmark failure may directly generate a module;
- no metric improvement may be promoted into an ontology claim;
- no fail-closed action may be counted as a cognitive correction;
- all v0.66-v0.89 runtime objects remain historical candidates only.

R1 is complete with bounded internal-project evidence. It identifies one
positive local representation stage, one output-complementarity signal, and
multiple composition or suppression failures. It does not identify positive
collective cognition.

R2 v0.2 was frozen by HumanGate with the bounded option A. The authorization
permits only the preregistered R3 finite synthetic validation and a standalone
experiment instrument.

Provider calls, fresh holdouts, Runtime/CoreSlim changes, retention writes, and
baseline writes remain blocked.

R3 is complete with a bounded synthetic-formal pass. It validates the exact
measurement and phase construction, while adding a necessary dual gate:
positive task compression does not by itself imply action admissibility.

R4 v0.1 stopped after two invalid attempts on its first role call. The Provider
returned a probability-direction inconsistency at the exact neutral boundary.
No semantic adequacy outcome is scorable. The failure exposes a
minimal-sufficient-receipt requirement: deterministic projections should be
owned by the Runtime instead of redundantly generated by the Provider.

R4 v0.2 freezes that theory revision as a one-factor paired diagnostic. It may
remove only Provider-generated direction, derive direction locally, and retain
the v0.1 numeric, composition, stability, leakage, and budget gates.

R4 v0.2 closed with six valid role calls and a coordinator-layer failure. Role
probabilities were accurate and stable; the Provider coordinator returned
invalid roots and poor numeric composition. Zero-call deterministic composition
recovered the packet information. The next theory object separates semantic
relation judgment from deterministic packet composition.

R4 v0.3 optimizes that boundary without creating a second coordinator Runtime.
It freezes `SemanticPacketRelation` as the Provider-supported object, while
Runtime alone compiles relation graphs, derives plans, composes probabilities,
and emits replayable receipts. v0.3A is a zero-Provider construction test.

R4 v0.3A passed all 14 frozen construction gates. Four actionable graphs
composed exactly and eight inadmissible graphs blocked. Naive duplicate
composition produced 0.141 to 0.222 probability overconfidence, establishing
the value of relation-aware deduplication without validating Provider semantics.

R4 v0.3B is preregistered on twelve new semantic micro-worlds. It compares two
counterbalanced batch calls with twelve single-case calls and requires zero
false combine or false deduplicate actions.

R4 v0.3B stopped after two invalid Batch A envelopes. Both unaccepted responses
used a `cases` array instead of `receipts`, but post-hoc item diagnostics were
12/12 exact twice with zero harmful Runtime actions. The result is a mechanical
construction failure, not a completed semantic adequacy result.

R4 v0.3C freezes the representation-level object as a unique homogeneous
receipt collection rather than a list of accepted key aliases. It authorizes
only zero-Provider adversarial shape validation and read-only replay of the two
preserved v0.3B responses.

R4 v0.3C passed all 15 frozen gates. Five admissible shapes canonicalized, nine
ambiguous or malformed shapes blocked, and both preserved v0.3B responses
replayed unchanged at 12/12 relation accuracy. This closes the mechanical
envelope anomaly only; Provider presentation robustness remains pending.

R4 v0.3D is preregistered as a hybrid-time presentation diagnostic. It reuses
the immutable Batch A responses, forbids a repeated Batch A call, and authorizes
only one reversed Batch B plus twelve isolated Single calls.

R4 v0.3D passed all 15 gates. Historical Batch A, reversed Batch B, and twelve
isolated Single judgments agreed 12/12 with zero harmful action. Single calls
cost 2.447 times more tokens per receipt without improving relation labels;
fresh hard-corpus generalization remains untested.

R4 v0.3E freezes a second unseen 18-case corpus construction. It removes direct
relation wording, preserves the six-state ontology, and authorizes only one
cost-efficient Batch call after deterministic adjudication and leakage audits.

R4 v0.3E passed all 13 gates with 17/18 relation accuracy and zero harmful
action. The only error conservatively blocked a raw-telemetry versus calibrated
value pair, exposing transformation equivalence as the next ontology object.

R4 v0.3F freezes transformation equivalence as five typed attributes with
required witnesses. It authorizes only a zero-Provider 18-case formal grid and
removal tests to determine whether the attributes compile into existing states.

R4 v0.3F passed all 14 frozen gates. All 18 relations and actions compiled
exactly, all six witness-removal or attribute-perturbation tests revoked or
redirected authority, and two runs were byte-identical. The construction
supports claim-relative, witness-bound equivalence on a formal grid only.
Provider attribute inference and future-claim reuse safety remain untested.

R4 v0.3G freezes the next semantic object: Provider-supported inference of the
five transformation attributes with case-local evidence references. Provider
may propose attributes only; Runtime retains validation, relation compilation,
action, and state authority. One fresh twelve-case batch is authorized only
after corpus and implementation preflight.

The v0.3G corpus and implementation passed all eight deterministic preflight
gates and are frozen by manifest. One bounded Provider batch is authorized.

R4 v0.3G closed as a preserved semantic failure with zero Runtime action harm.
Four attributes and all evidence bindings scored 12/12, while the overloaded
`InformationRelation` scored 8/12. Runtime actions remained 12/12 with no false
deduplication. Provider calls are paused pending a theory-first factorization
of transform status and information effect.

R4 v0.3H freezes that factorization as a zero-Provider formal object. It must
resolve the four v0.3G disagreement families, reject all invalid cross-axis
combinations, preserve the existing action surface, and pass an explicit
anti-additive complexity gate.

R4 v0.3H stopped as an experiment-instrument construction failure. The first
test run exposed constant audit booleans and did not actually compile all
seventeen invalid status-effect pairs. The apparent pass is void; the theory
remains unadjudicated and requires a newly preregistered validation version.

R4 v0.3I inherits the unchanged factorization theory and frozen cases. It
authorizes only a corrected executable invalid-pair audit, source-derived
shortcut audit, implementation hash freeze, one formal execution, and one
replay.

The corrected v0.3I evaluator and tests are hash-frozen. Static inspection found
no case shortcut, Provider dependency, network dependency, or protected-write
reference in the compiler. One zero-Provider formal execution is authorized.

R4 v0.3I passed all sixteen corrected gates. All twenty cases, six removals,
and seventeen executable invalid-pair audits passed; replay was byte-identical.
The factorization is formally coherent but has not yet shown causal benefit
over the legacy single enum in Provider inference.

R4 v0.3J freezes a matched fresh-corpus comparison between the legacy enum and
factorized axes. Two forward/reverse rounds use `L-F-F-L` call order and
separate representation ceiling, Provider inference, Runtime action safety,
revalidation resolution, and token cost.

The fresh twelve-case dual-reference corpus and comparative implementation
passed 71 tests and are hash-frozen. Legacy and factorized private references
compile to identical immediate relations and actions. Four bounded calls are
authorized in `L-F-F-L` order.

R4 v0.3J closed at 13/18 gates. Factorization improved revalidation by 2/12 in
both rounds and added only 4.8 percent token cost, but wider receipts degraded
provenance inference and witness binding. Factorized action agreement was 9/12
versus legacy 12/12, including one false combine. Provider calls are paused
pending theory-first role decomposition.

R4 v0.3K is HumanGate-approved and theory-frozen. It defines roles as bounded
semantic responsibilities rather than personas and preregisters a matched
two-context wide-versus-split comparison. Provider calls remain conditional on
a committed corpus and implementation hash freeze with passing deterministic
preflight.
