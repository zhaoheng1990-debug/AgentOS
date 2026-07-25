# Theory Packet Template

## Identity

- packet id:
- theory baseline:
- research object:
- evidence coordinate:
- status:
  `DRAFT | REVIEW_READY | FROZEN_FOR_ENGINEERING_VALIDATION | VALIDATED |
  REJECTED | REVISED | INCONCLUSIVE`

## Object Chain

```text
UpperOntologyObject
  -> ProjectObject
  -> ObservableProxy
  -> Metric
```

Define each term. State which layer the experiment can and cannot update.

## Possibility Space

- leading theory:
- rival 1:
- rival 2:
- null model:
- unresolved dimensions:

## Discriminating Predictions

For each model, freeze:

- predicted direction;
- predicted failure signature;
- observation that would reject it;
- observation that would remain ambiguous.

## Experimental Operator

- smallest experiment that distinguishes the models:
- why no smaller formal or replay test is sufficient:
- Provider necessity:
- fresh data necessity:

## Theory Freeze Gate

- ontology object defined:
- rival or null model present:
- discriminating predictions frozen:
- falsification conditions frozen:
- proxy limits explicit:
- expected theory Cbit margin positive:
- stop and rollback condition frozen:
- PM/HumanGate decision:
- freeze artifact hash:

Engineering is unauthorized unless the decision is
`FROZEN_FOR_ENGINEERING_VALIDATION`.

## Engineering Derivation Contract

For every proposed implementation object:

| Engineering object | Frozen theory variable | Rival discrimination | Minimality | Removal test | Authority |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Any unmapped object blocks validation start.

## Validation Versus Discovery Boundary

- theory questions fixed before implementation:
- observables collected mechanically:
- changes allowed as Class A mechanical amendments:
- changes requiring Class B theory revision:
- semantic fields/thresholds that cannot change after freeze:
- operations explicitly forbidden during validation:

## Cbit and Cost

- expected gross information gain:
- harmful-certainty penalty:
- retained-correct penalty:
- redundancy penalty:
- coordination friction:
- complexity cost:
- token/latency budget:
- stopping condition:

## Anti-Additive Audit

- active patch-accumulation triggers:
- current object level:
- proposed object level:
- variables or modules removed by the proposal:
- new free parameters introduced:
- abstraction-fog risk:
- expected theoretical Cbit margin:

## Authority Boundary

- allowed writes:
- forbidden writes:
- replay boundary:
- rollback pointer:
- promotion authority:

## Closure Contract

Every closure must report:

1. facts;
2. phenomena;
3. mechanism interpretation;
4. rival explanations;
5. negative results;
6. theory objects accepted, revised, rejected, or still pending;
7. residual uncertainty;
8. the next unresolved object.

If the result does not reduce the theory possibility space, close it as
`NO_THEORY_UPDATE` and do not derive a module from it.
