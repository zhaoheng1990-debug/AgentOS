# Workspace Cleanup Audit 2026-07-17

## Scope

Workspace: `C:\Users\ZH\Documents\Logos-AgentOS`

Cleanup goal: remove expired/generated workspace noise without damaging the AgentOS CoreSlim base or deleting research/handoff materials that may still be needed for audit lineage.

## Deleted

Only reproducible cache/temp material was deleted:

- Python `__pycache__` directories across the workspace, including generated caches under `outputs/`.
- `.pytest_cache` directories.
- `.pytest_tmp_provider_cognition`.
- Top-level `_tmp_*` clean-extract / return-pack-check directories.
- Top-level `tmp/` transient PDF render directory.
- Top-level transient solver/runtime log `Highs.log`.

Recorded cleanup removed at least `8,877,848` bytes from scripted deletion passes. Some parent temp directories were removed after nested cache deletion, so exact byte accounting should be treated as a conservative cleanup receipt rather than a release-size inventory.

## Preserved

The following were intentionally preserved:

- `agentos_core_slim_v0/`: current CoreSlim source and tests.
- `AgentOS_CoreRefactor_ProviderCognition_QualityLifecycle_Seed_v0_1.md`: received patch seed.
- `handoff_received/20260717_core_refactor_provider_cognition_quality_lifecycle/`: seed receipt and applied-scope record.
- `outputs/`: research/runtime artifacts, excluding cache subdirectories.
- `_incoming/`, `handoff/`, `seedpacks/`, `project_baselines/`: provenance and handoff materials.
- `scripts/`, `tools/`, root experiment scripts, `experiments/`: untracked research/runner material pending separate archival decision.
- `.codex/`, `.agents/`: local tool/app state.

## Safety Checks

Before recursive deletion, every resolved target path was checked to be inside the workspace and not equal to the workspace root.

No tracked CoreSlim source file was deleted.

## Verification

```text
pytest -q tests --basetemp C:\Users\ZH\Documents\Logos-AgentOS\.pytest_tmp_provider_cognition
32 passed

python -m compileall -q agentos_core_slim_v0
passed
```

Post-verification generated caches were scrubbed again.

## Remaining Untracked Material

The git worktree still contains many untracked historical scripts, configs, handoff folders, outputs, and tools. They are not treated as disposable noise in this cleanup pass because they may preserve research lineage or cross-project evidence. A later archival pass should classify them into:

- keep as source;
- move to provenance archive;
- move to domain plugin;
- package as historical return artifacts;
- delete only with explicit approval.
