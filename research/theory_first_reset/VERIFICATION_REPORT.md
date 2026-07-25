# Theory-First Reset Verification

## Result

`PASS`

## Git Boundary

- active branch: `codex/theory-first-reset-v0.65`
- active base:
  `af0cef20eaab9debf040b643c48a01995ba58e14`
- archived tip:
  `14e1a60ec27c13d1a321038d35c475a5d5f2f370`
- active base is an ancestor of archived tip: yes
- archived branches or commits deleted: no
- v0.66-v0.89 candidate files restored into active branch: no

## Pointer Integrity

- `ROLLBACK_POINTER.json` parses as JSON.
- Every preserved commit resolves as a Git commit.
- Every closure path resolves at its declared commit.
- Every resolved closure blob matches the declared blob identity.

## Regression

### CoreSlim

```text
python -m pytest agentos_core_slim_v0\tests -q --basetemp C:\pt\aos65c2
394 passed in 6.47s
```

### v0.65 local experiment pack

```text
python -m pytest tests -q --basetemp C:\pt\aos65e
427 passed in 19.79s
```

The first CoreSlim invocation used a repository-local temporary path and
encountered Windows path-length failure after 393 passing tests. A second
attempt used `C:\pt` before that parent existed and failed during fixture
setup. Neither result entered the regression judgment. The final short-path
run executed the complete suite and passed.

## Authority Check

Verification establishes:

- the rollback is mechanically reproducible;
- the v0.65 base remains usable;
- later evidence remains reachable;
- the active change is documentation and research governance only.

It does not establish:

- that the candidate collective-cognition theory is true;
- that v0.65 is a successful collective-cognition capability;
- that v0.86-v0.89 candidate modules should be restored;
- that any fresh benchmark or Provider experiment is authorized.
