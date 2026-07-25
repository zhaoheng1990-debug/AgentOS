# AgentOS R4 Provider Adequacy Calibration

Standalone Provider experiment derived from the frozen R4 preregistration.

It tests one DeepSeek model under isolated role contexts and packet-only
coordination. It does not import AgentOS Runtime or consume a benchmark
holdout.

Offline tests:

```powershell
python -m pytest -q
```

Authorized live run:

```powershell
python -m theory_first_r4.cli
```

Local artifacts are written to the repository-level ignored directory
`outputs/r4_provider_adequacy_v0_1/`.

