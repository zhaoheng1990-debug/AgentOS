# R1 Organizational Identifiability Preflight

## Decision

`R1_FEASIBLE_WITH_EXPLICIT_IDENTIFIABILITY_LIMITS`

The local archive contains the frozen case-level runs and private references
needed for a zero-Provider transition audit. It does not contain the
counterfactual design needed to estimate every role's unique cognitive
contribution.

## Available Comparisons

| Round | Matched comparison | Identifiable |
| --- | --- | --- |
| v0.65 | A0 one-pass vs A1 staged on 36 cases | decision/evidence transitions, harm, token delta |
| v0.82 | A14 atomic vs A14+A16 staged context on 12 cases | exact addon mutations, corrected/harmed spans, evidence invariance, token delta |
| v0.84 | A14+A16 vs A14+A16+A18 on 12 cases | reviewer mutations, corrected/harmed spans, token delta |
| v0.88 | direct warrant vs EvidenceSet+ClaimScope on 18 cases | end-to-end transitions, sentence changes, harm, cost |
| v0.89 | scope baseline vs binding+challenge veto on 18 cases | suppression, valid/invalid veto mechanism, retained-correct loss, cost |

Every comparison has:

- case-aligned run artifacts;
- private references or frozen typed references;
- task-level call records with token usage;
- frozen evaluation output;
- explicit no-write and candidate-only boundaries.

## What R1 Can Identify

1. **Stage transition effect:** which cases or spans changed after a stage.
2. **Valid correction:** a changed output that matches the frozen reference.
3. **Introduced error:** a previously correct output made incorrect.
4. **Retained correct:** correct upstream outputs preserved downstream.
5. **Suppression:** strong upstream outputs removed without a valid semantic
   correction.
6. **Marginal operational cost:** task calls and token use added by a stage.
7. **Composition loss:** locally correct stage evidence not reflected in the
   final candidate, where the artifact chain exposes both states.
8. **Oracle transition ceiling:** the best result achievable by accepting only
   reference-correct observed transitions. This is descriptive and cannot act
   as a deployable policy.

## What R1 Cannot Fully Identify

### Unique role information `U`

The roles usually perform different sequential tasks. They do not each emit a
commensurate, blind final judgment over the same object. A role-withheld
counterfactual is available for some stages, but this estimates stage effect,
not the conditional mutual information of an independent cognitive actor.

Status: `PARTIALLY_IDENTIFIABLE_AS_STAGE_ABLATION_ONLY`

### Error correlation

Same-case outputs exist, but EvidenceSet, ClaimScope, Binding, and Challenger
often judge different variables and inherit shared upstream framing. Their
errors cannot be treated as independent Bernoulli judgments over one label.

Status: `PARTIALLY_IDENTIFIABLE_FOR_SHARED_DECISIONS_ONLY`

### Best-member superiority

The archive does not consistently provide multiple independent members with
matched evidence, matched tokens, and the same final decision contract.

Status: `NOT_IDENTIFIABLE`

### Coordinator synergy

The Runtime compilers are present, but no matched conserving-versus-lossy
coordinator arm was frozen.

Status: `NOT_IDENTIFIABLE`

## Consequence for the Research Route

R1 remains the correct next step because it can quantify composition and
suppression before a new experiment. Its closure must not claim that the
archive measures true collective cognition.

The expected R1 outcome is a boundary map:

```text
identified from archive:
  representation transitions
  stage corrections and harms
  suppression
  composition loss
  friction

requires new controlled experiment:
  unique role information
  matched best-member advantage
  role error independence
  coordinator synergy
```

This boundary will determine the minimal variables in R3. It prevents the
synthetic experiment from recreating every historical module.

## Input Integrity

`R1_ARCHIVE_INPUT_MANIFEST.json` freezes 27 local input files by SHA-256.
The manifest records only paths, sizes, and file hashes. It does not copy,
modify, or promote any output artifact.
