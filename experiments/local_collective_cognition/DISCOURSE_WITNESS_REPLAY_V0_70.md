# Discourse Witness Replay v0.70

## Decision

**CLOSED: zero-call replay rejected.**

v0.70 replayed the frozen v0.69 Provider outputs while allowing subject and
relation witnesses to come from any admitted span in the same case.

- Valid receipts: `8/12`, up from `7/12`
- Label accuracy: `0.5000`
- Evidence F1: `0.6667`
- Effective Cbit: `0.6111`
- Additional Provider calls: `0`

Only `EI-CAL-8861` was structurally recovered. `13790`, `5842`, `13793`, and
`11179` remained blocked. The residual failures show two mechanisms:

1. Provider relation surfaces were paraphrases rather than exact substrings.
2. Frame alias lists did not always contain the actual source surface.

Therefore anchor inheritance alone is insufficient. v0.71 should locally
enumerate immutable source-surface candidates, assign IDs and hashes, and ask
the Provider only to bind semantic roles to candidate IDs. This removes
free-text copying from the contract while retaining Provider-backed semantics.

The fresh holdout remained untouched and CoreSlim was not modified.
