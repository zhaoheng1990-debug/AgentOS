# R1 Verification Report

## Scope

Verification applies only to:

- the read-only R1 archive audit instrument;
- the five frozen comparisons;
- the R1 theory report;
- the R2 theory packet draft;
- research governance state.

It does not validate a new Runtime, Provider, CoreSlim, retention, or production
behavior because none was added.

## Input Integrity

Result: `PASS`

- expected frozen files: 27;
- files present: 27;
- size matches: 27;
- SHA-256 matches: 27;
- source files modified by audit: 0.

The input manifest remains:

`R1_ARCHIVE_INPUT_MANIFEST.json`

## Audit Instrument

Result: `PASS`

- Python syntax compilation passed;
- analysis completed with zero Provider calls;
- transition comparisons: 5;
- transition ledger rows: 168;
- closure status: `R1_COMPLETE_BOUNDED`;
- fresh holdout consumed: false;
- Runtime/CoreSlim/retention writes: false.

## Deterministic Replay

Result: `PASS`

The audit was run twice against the same frozen inputs. SHA-256 values were
unchanged for:

- `input_validation.json`;
- `transition_ledger.json`;
- `summary.json`;
- `hash_inventory.json`;
- `closure.json`.

Local derived outputs are intentionally ignored by Git under:

`outputs/r1_organizational_identifiability_v0_1/`

## Result Assertions

Result: `PASS`

- v0.65 net transition: -1;
- v0.82 net transition: +19;
- v0.84 net transition: -4;
- v0.88 net transition: 0;
- v0.89 net transition: -11;
- positive comparisons: 1;
- zero comparisons: 1;
- negative comparisons: 3;
- policy stage: `R2_ORGANIZATION_THEORY_PACKET_DRAFTING`.

## Existing Bridge Regression

Initial collection result: `BLOCKED_BY_ENVIRONMENT`

The first invocation did not include `agentos_core_slim_v0` in `PYTHONPATH`, so
three v0.65 test modules could not import `agentos_kernel`. No test body ran.

Corrected environment result: `PASS`

After adding the repository CoreSlim and experiment package roots to the
process-local module path:

```text
12 passed in 14.07s
```

Covered files:

- `test_benchmark_bridge_contracts_v0_65.py`;
- `test_benchmark_bridge_replay_v0_65.py`;
- `test_benchmark_bridge_v0_65.py`.

## Boundary

This verification establishes deterministic retrospective analysis and
research-document consistency. It does not convert internal archive evidence
into external validity, authorize R3, or revive any rejected historical round.
