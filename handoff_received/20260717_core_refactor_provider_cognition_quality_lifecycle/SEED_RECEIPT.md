# AgentOS Core Refactor Provider Cognition Quality Lifecycle Seed Receipt

## Receipt

- received_at: `2026-07-17T09:23:22.0976675+08:00`
- seed_file: `C:\Users\ZH\Documents\Logos-AgentOS\AgentOS_CoreRefactor_ProviderCognition_QualityLifecycle_Seed_v0_1.md`
- seed_sha256: `480D92A92BCBCA37F80C4B0F84D98955554F7931BAB4199236E362D569D56CB9`
- patch_seed_version: `v0.1`
- applied_core_version: `0.2.0`

## Applied Scope

- Provider cognitive execution plane.
- Quality decision matrix.
- Append-only artifact revision and publication pointer retention model.
- Runtime task lifecycle and recovery model.
- Cognitive asset ledger and read-only projection contract.
- Evidence dimension registry and source hygiene helpers.
- Core package domain-neutrality cleanup.

## Verification

```text
pytest -q tests --basetemp C:\Users\ZH\Documents\Logos-AgentOS\.pytest_tmp_provider_cognition
32 passed

python -m compileall -q agentos_core_slim_v0
passed
```

## Boundary

This patch implements the generic AgentOS Core substrate only. VCOS-specific ontology, prompts, workflows, report renderers, UI conventions, and provider prompt content remain domain-plugin responsibilities.
