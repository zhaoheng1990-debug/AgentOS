# Verification report

Date: 2026-07-19

## Pre-patch relevant baseline

```text
python -m pytest -q \
  tests/test_constraint_aligned_retention.py \
  tests/test_provider_cognition_layer.py

18 passed
```

## Targeted patch verification

```text
python -m pytest -q \
  tests/test_sro_retention_runtime.py \
  tests/test_provider_cognition_layer.py \
  tests/test_constraint_aligned_retention.py

33 passed
```

The 15 new tests cover:

- witness precommit/outcome separation;
- immutable immediate and delayed lifecycle revisions;
- direct reuse;
- synthetic-evidence downgrade;
- observe versus abstain;
- structural-role collision rejection;
- validity drift revision;
- local reconstruction downgrade;
- malformed probability and boolean-metric rejection;
- missing Provider support;
- Provider operation registration and fail-closed behavior;
- delayed prediction/reveal order, duplicate blocking and event hash chain.

## Full regression

```text
python -m pytest -q tests --basetemp ..\.pytest_tmp_sro_retention_full

235 passed in 5.08s
```

## Compilation and diff checks

```text
python -m compileall -q agentos_kernel tests/test_sro_retention_runtime.py
git diff --check -- <patch paths>

PASS
```

## Residual validation boundary

The tests validate contracts and deterministic routing, not real-world matcher
quality. Production calibration, latency, concurrency, persistent-ledger
integration and external Harness evaluation remain pending.
