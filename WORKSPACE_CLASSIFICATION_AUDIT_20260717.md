# Workspace Classification Audit 2026-07-17

## Objective

Classify and clean non-Core workspace material without damaging the AgentOS CoreSlim base, its tests, or the active provider-cognition quality-lifecycle seed.

## Baseline Verification

Before migration:

```text
pytest -q tests --basetemp C:\Users\ZH\Documents\Logos-AgentOS\.pytest_tmp_provider_cognition
32 passed

python -m compileall -q agentos_core_slim_v0
passed
```

## Keep In Workspace Root

These remain active workspace components:

- `agentos_core_slim_v0/`
- `.git/`
- `.gitignore`
- `.codex/` local environment state
- `AgentOS_CoreRefactor_ProviderCognition_QualityLifecycle_Seed_v0_1.md`
- `handoff_received/20260717_core_refactor_provider_cognition_quality_lifecycle/`
- `WORKSPACE_CLEANUP_AUDIT_20260717.md`
- `WORKSPACE_CLASSIFICATION_AUDIT_20260717.md`

## Archive / Migrate

Moved to `archive/20260717_legacy_research_line/`.

Archive manifest:

```text
archive/20260717_legacy_research_line/ARCHIVE_MANIFEST_20260717.csv
file_count: 2215
bytes: 586620019
```

Moved groups:

- root historical experiment scripts -> `root_experiment_scripts/`
- `_incoming/`
- `configs/`
- `experiments/`
- `handoff/`
- older `handoff_received/` entries
- `outputs/`
- `project_baselines/`
- `scripts/`
- `seedpacks/`
- `tools/`
- empty `vc_domain_adapter` skeleton -> `workspace_materials/vc_domain_adapter_empty_skeleton/`
- `MIGRATED_TO_D_POINTER.md`

Rationale: these materials may preserve research lineage, seed history, or historical execution evidence, but they are not active CoreSlim source dependencies.

## Delete

Deleted only material classified as empty or reproducible noise:

- `.agents/` empty shell
- `logos_agent_os/` empty shell
- top-level `tests/` empty shell
- generated pytest temp directories
- generated `__pycache__` and `.pytest_cache` directories

## Safety Checks

- Recursive moves and deletes were path-checked to remain inside `C:\Users\ZH\Documents\Logos-AgentOS`.
- The workspace root itself was never a delete target.
- `archive/` is ignored by git to prevent large historical artifacts from entering the Core repository.
- The active seed receipt for 2026-07-17 was not moved.

## Post-Migration Verification

After moving root scripts:

```text
pytest -q tests --basetemp C:\Users\ZH\Documents\Logos-AgentOS\.pytest_tmp_provider_cognition
32 passed

python -m compileall -q agentos_core_slim_v0
passed
```

After moving historical directories:

```text
pytest -q tests --basetemp C:\Users\ZH\Documents\Logos-AgentOS\.pytest_tmp_provider_cognition
32 passed

python -m compileall -q agentos_core_slim_v0
passed
```

Final cache sweep:

```text
remaining __pycache__/.pytest_cache directories: 0
```

## Result

The workspace root now contains the active AgentOS CoreSlim base plus current seed/audit files. Historical research and output material remains locally available under `archive/20260717_legacy_research_line/`, with a hash manifest, but is no longer mixed into the active Core workspace.
