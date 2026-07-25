# Theory Packet Template

## Identity

- packet id:
- theory baseline:
- research object:
- evidence coordinate:
- status: `DRAFT | FROZEN | REJECTED | REVISED`

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
