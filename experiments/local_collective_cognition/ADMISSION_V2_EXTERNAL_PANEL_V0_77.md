# Admission V2 External Typed Panel v0.77

## Status

**EXTERNAL_TYPED_REFERENCE_CANDIDATE_FROZEN.**

v0.77 does not change the rejected v0.76 runtime. It freezes an independent
external reference workflow for the 12-case, 50-span development panel.

Two blinded lane packs were generated:

- OpenAI GPT-5.6, annotation lane A;
- Google Gemini-3.1, annotation lane B.

Each model receives only the target intervention-comparator-outcome object,
one target span, the frozen rubric, and its own response contract. Lane IDs and
item order differ. Neither pack contains case IDs, span IDs, benchmark gold,
v0.76 candidate outputs, prior scores, or the peer annotation.

## Rubric

The primary typed labels remain:

1. object relation: exact, contextual, or irrelevant;
2. evidence utility: effect-bearing, context-only, or none;
3. disposition: admit evidence, retain context, or reject.

An auxiliary `effect_basis_codes` field records why an effect-bearing span
qualifies:

- direction or magnitude;
- significance or uncertainty;
- null or no difference;
- quantitative corroboration.

The auxiliary field does not grant Runtime authority. It exists to resolve the
specific v0.76 ambiguity around zero effects and corroborating evidence.

Every span must be assessed independently. A more concise sibling span cannot
demote valid corroboration to context.

## Panel Result

Both annotation responses passed exact pack-hash, model-identity, blinding,
coverage, enum, and cross-field compatibility validation.

- complete typed-label agreement: 39/50 spans (78%);
- anonymous Kimi-K3 adjudication: 11/50 spans (22%);
- Kimi-K3 decisions selecting a supplied anonymous position: 11/11;
- independent reassessments: 0/11;
- mean adjudication confidence: 0.8764.

Ten of the eleven disagreements crossed the exact/contextual/irrelevant object
boundary together with the corresponding evidence-utility and disposition
boundary. Six were context-versus-reject disputes, four were
evidence-versus-context disputes, and one concerned only effect-basis coding.
This localizes the remaining semantic ambiguity primarily to object relation
and outcome separability rather than to whether null, uncertainty, or
corroborating evidence can be effect-bearing.

After private unblinding for analysis only, Kimi-K3 selected the GPT-5.6 lane
on nine disagreements and the Gemini-3.1 lane on two. Annotator identities
were not available during adjudication.

## Frozen Reference Candidate

The resulting 50-span reference candidate contains:

| Disposition | Count |
|---|---:|
| `ADMIT_EVIDENCE` | 24 |
| `RETAIN_CONTEXT` | 13 |
| `REJECT` | 13 |

Its artifact hash is:

`f63886ab3b0ab5ae5c44c322244ce47d26e96f262097300d9d614b6319f7c001`

The reference remains `EXTERNAL_TYPED_REFERENCE_CANDIDATE`. It makes no
ground-truth claim and grants no runtime-tuning, Core-write, retention-write,
or production authority.

## v0.76 Diagnostic Replay

The rejected v0.76 Admission V2 partitions were compared with the frozen
external reference candidate without changing the runtime:

| Measure | Result |
|---|---:|
| Span accuracy | 0.7600 |
| `ADMIT_EVIDENCE` F1 | 0.8444 |
| `RETAIN_CONTEXT` F1 | 0.6000 |
| `REJECT` F1 | 0.8000 |
| Macro F1 | 0.7481 |
| Case-level admission agreement | 10/12 |

The 12 span errors consist of five valid evidence spans demoted to context,
two contextual spans promoted to evidence, two contextual spans rejected, and
three irrelevant spans retained as context. The two case-level errors are:

- `EI-CAL-11806`: valid null/no-difference evidence was demoted to context;
- `EI-CAL-10177`: non-separable composite outcomes were promoted as direct
  cardiovascular-death evidence.

The panel therefore confirms both sides of the v0.76 failure: the runtime is
too conservative toward valid null/corroborating evidence while also being too
permissive when a target outcome is merely contained in a non-separable
composite. v0.76 remains rejected.

## Adjudication Workflow

The repository now contains validators and builders for the complete return
path:

1. validate both lane responses against exact pack hashes and label
   compatibility;
2. retain exact full-label agreements;
3. convert disagreements into anonymous `POSITION_1` and `POSITION_2` records;
4. ask Moonshot Kimi-K3 to select a position or independently reassess;
5. build an `EXTERNAL_TYPED_REFERENCE_CANDIDATE`.

Annotator identity, benchmark gold, and candidate outputs remain hidden from
Kimi. The final reference is candidate-only and has no automatic runtime
tuning, Core, retention, or production authority.

## Files

The external ZIPs are generated under:

`outputs/admission_v2_external_panel_v0_77/`

Only the corresponding lane ZIP should be given to each annotator. The private
panel manifest must remain local.

The v0.75 holdout remains excluded and cannot be rerun. The v0.77 panel is a
development reference candidate and must not be used as a fresh holdout after
this diagnostic comparison.
