# Admission V2 External Typed Panel v0.77

## Status

**AWAITING_GPT_GEMINI_TYPED_ANNOTATIONS.**

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

## Adjudication

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

No Provider annotation result has been ingested yet, so v0.77 makes no claim
about Admission V2 semantic validity. The v0.75 holdout remains excluded and
cannot be rerun.
