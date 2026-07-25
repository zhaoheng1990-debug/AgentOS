# AgentOS R3 Minimal Synthetic Validation

This is a standalone, zero-Provider experiment derived from the frozen R2 v0.2
theory packet and R3 preregistration.

It does not import AgentOS Runtime, CoreSlim, retention, memory, or Provider
code.

Run:

```powershell
python -m theory_first_r3.cli
```

Test:

```powershell
python -m pytest -q
```

Default derived outputs are written under the repository-level ignored
`outputs/r3_minimal_synthetic_v0_1/` directory.
