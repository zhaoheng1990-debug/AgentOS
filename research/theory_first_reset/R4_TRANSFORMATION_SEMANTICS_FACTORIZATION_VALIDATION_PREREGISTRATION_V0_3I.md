# R4 Transformation Semantics Factorization Validation Preregistration v0.3I

## Status

`PREREGISTERED_CORRECTED_ZERO_PROVIDER_VALIDATION`

## Inheritance

- unchanged v0.3H factorization theory;
- unchanged twenty cases;
- unchanged seven valid and seventeen invalid pair expectations;
- unchanged six removals;
- unchanged sixteen PASS gates;
- v0.3H construction-failure closure.

No semantic expectation, enum, compiler rule, threshold, relation state, or
Runtime action changes in v0.3I.

## Sole Instrument Correction

The evaluator must:

1. instantiate all 24 `TransformStatus x InformationEffect` pairs;
2. compile every pair through the real factorized compiler;
3. verify every invalid pair returns `UNRESOLVED -> BLOCK` and includes
   `STATUS_EFFECT_INCONSISTENT`;
4. inspect compiler source for case IDs, case-family branches, transform-name
   branches, Provider imports, network clients, and protected-write references;
5. derive the corresponding gates from those observations rather than constant
   booleans.

## Freeze Requirement

Corrected evaluator, tests, and implementation hashes must be committed before
the first v0.3I execution.

## Execution

- zero Provider calls;
- one formal execution after freeze;
- one deterministic replay;
- no CoreSlim, retention, or baseline writes.

## PASS And Stop Rules

The original sixteen v0.3H gates remain decisive.

Stop without same-version repair if:

- any invalid pair becomes actionable;
- source audit finds a shortcut or forbidden dependency;
- any frozen case or removal fails;
- replay differs;
- a semantic expectation requires change.
