# Pre-v0.64 Provenance Boundary

## Decision

`SEPARATE_EXPERIMENT_FAMILIES_NOT_ONE_LINEAR_VERSION_SERIES`

The pre-v0.64 archive must not be modeled as a single v0.1-v0.63 progression.
The same version numbers were restarted in multiple experiment families and
were imported into Git together in the CoreSlim `0.4.0-alpha.21` release
commit.

## Distinct Families

| Family | Local numbering observed | Main object |
| --- | --- | --- |
| Selective collaboration and disagreement resolution | protocol v0.2-v0.25 | routing, review, disagreement, candidate revision, constrained action, and problem formulation |
| Structural-prior and ambiguity calibration | several v0.1-v0.4 restarts | structure elicitation, semantic judge calibration, unstated ambiguity, and coordinator specificity |
| Negative-evidence and clarification | negative-evidence v0.1-v0.5; clarification v0.3-v0.15 | negative evidence, clarification action, requested object, semantic basis, and joint coordination |
| Cognitive-action role routing | v0.15-v0.25 | cognitive-action ontology, source recognition, selective escalation, evidence-first routing, and immutable evidence identity |
| Organization and portfolio mainline | v0.26-v0.63 | problem emergence, gray admission, collaboration value, portfolio displacement, warrant, scarcity, relation binding, and typed evidence |

For example, `clarification v0.11`, `collective protocol v0.11`, and a
construction audit named `v0.11` are different experiments. Ordering them by
the numeric suffix would invent causal ancestry that the archive does not
establish.

## Current Modeling Scope

`PER_ROUND_THEORY_MODELS_V0_1.md` covers v0.64-v0.89 because:

1. those rounds form one Git-ancestry chain;
2. each round has a stable commit or frozen local output;
3. this is the series whose engineering authority was rolled back;
4. the route decision concerns its transition from representation repair to
   role composition.

All 26 rounds in that target series are modeled. No version is omitted.

## How Prehistory Is Used

Pre-v0.64 results are retained as theory priors and family-level evidence:

- role labels alone do not establish cognitive distinction;
- disagreement routing can preserve or harm correct answers;
- structural specialization can outperform fixed member selection on bounded
  holdouts;
- problem formulation and ambiguity detection are upstream cognitive objects;
- safety gates and lineage can succeed while cognitive gain remains zero;
- portfolio and retention value require transfer and delayed evidence.

These priors inform the candidate theory but do not receive fabricated
per-round positions in the v0.64-v0.89 sequence.

## Separate Reconstruction Requirement

A genuine per-round theory reconstruction of the prehistory would require:

- a family-specific experiment ID for every output;
- manifest and artifact-hash binding;
- ordering within each family;
- explicit cross-family dependency edges;
- separate model cards per family namespace.

That is a different archival-reconstruction project. It is not required to
identify the next step in the v0.64-v0.89 rollback series, and it must not be
silently approximated by sorting duplicated version labels.
