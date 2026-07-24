# Apply and rollback

## Captured preimage gates

Apply the isolated patch only when these preimage hashes match:

```text
agentos_core_slim_v0/agentos_kernel/__init__.py
e6e6056158edc8bed22b9ea5181082aa5e19d61b4d24680d70eb062f87df81e1

agentos_core_slim_v0/agentos_kernel/provider_cognition_layer.py
f9577eceac67a4423a99db27f8b5ac50887f639633b1e7a6a7d1e68e96e241c2
```

The following unchanged anchors were also captured:

```text
constraint_aligned_retention.py
0a07f3d918e0f62d26f217c479dc4654a4d1798bc6eebc0cb41dbccb0bcdcf36

version.py
f2846089862171cc76f614d71014894af733d00f556851fc6579348c2cdb5872
```

If the preimage differs, do not overwrite with `overlay/`; rebase the two small
tracked-file hunks manually and rerun the full suite.

## Replay apply

From repository root:

```powershell
git apply --check handoff_received/20260719_sro_retention_kernel_patch_v0_1/patch/AgentOS_SRORetentionKernel_Patch_v0_1.patch
git apply handoff_received/20260719_sro_retention_kernel_patch_v0_1/patch/AgentOS_SRORetentionKernel_Patch_v0_1.patch
Set-Location agentos_core_slim_v0
python -m pytest -q tests --basetemp ..\.pytest_tmp_sro_retention_replay
python -m compileall -q agentos_kernel tests examples
```

The active worktree already contains the applied patch; these commands are for
clean replay or another AgentOS engineering worktree.

## Rollback only this patch

From a worktree where this isolated patch was applied:

```powershell
git apply --check -R handoff_received/20260719_sro_retention_kernel_patch_v0_1/patch/AgentOS_SRORetentionKernel_Patch_v0_1.patch
git apply -R handoff_received/20260719_sro_retention_kernel_patch_v0_1/patch/AgentOS_SRORetentionKernel_Patch_v0_1.patch
```

This removes the three new files and reverses only the public-export and
Provider-contract hunks. It does not revert unrelated dirty-worktree changes.

## Release-owner decision

This package intentionally does not change `version.py`, README or CHANGELOG.
After engineering review, the AgentOS release owner may version the feature and
decide whether the candidate enters a release.
