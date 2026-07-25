# Factorized Benchmark Acquisition v0.86

## Status

`CLOSED_AS_BENCHMARK_ENTRY_ONLY`

This stage establishes a benchmark-neutral, external-data evaluation entry.
It does not run a Provider experiment, alter v0.85, or claim that Kernel state
utility has been externally validated.

## Why this stage exists

The v0.85 study-relation screen showed that structural binding can be locally
correct while the resulting admission mutation is semantically harmful. The
next experiment therefore cannot continue to use one PICO-shaped receipt as
the evaluation surface for all cognitive responsibilities.

v0.86 separates three observable layers:

| Layer | External source | What it can test | What it cannot authorize |
|---|---|---|---|
| Study-object binding | EBM-NLP | Participant, intervention, and outcome span binding | Evidence support or runtime state mutation |
| Semantic warrant | SciFact | Claim support, contradiction, and rationale selection | AgentOS candidate promotion |
| Context utility | QASPER fixture | Question-conditioned evidence usefulness and answerability | Kernel utility or retention promotion |

No selected benchmark directly supplies an AgentOS state-transition reference.
`KernelUtilityCompiler` must therefore remain a deterministic AgentOS-owned
layer evaluated against frozen outcome rules after upstream benchmark scoring.

## Source and license boundary

### SciFact

- Repository: <https://github.com/allenai/scifact>
- Data archive:
  <https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz>
- Frozen SHA-256:
  `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be`
- Claims and evidence annotations are CC BY 4.0.
- Corpus abstracts are ODC-By 1.0.
- Repository code is Apache-2.0.
- Disposition: external reference allowed with attribution; no dataset files
  are committed to AgentOS.

### EBM-NLP

- Repository: <https://github.com/bepnye/EBM-NLP>
- Pinned archive revision:
  `43a4a1ea3f0a21cfb8820c040b843dfaf66192d0`
- Frozen SHA-256:
  `b7357503911ba9f708d04e24c1ab3fe9e0a79833910e53e2472ed21214a44e3f`
- The repository describes the data but exposes no license file or GitHub
  license metadata.
- Disposition: `BLOCKED_LICENSE_UNCLEAR`. Local schema smoke is retained as a
  candidate observation; benchmark publication and redistribution are blocked.

### QASPER

- Baseline repository:
  <https://github.com/allenai/qasper-led-baseline>
- Pinned fixture revision:
  `afd0fb96bf78ce8cd8157639c6f6a6995e4f9089`
- Frozen fixture SHA-256:
  `942ce1c63822568da0d77ddcbdcfa6f469dad17336cf003fee0e9dbd010ee9ba`
- The baseline repository is Apache-2.0.
- The official full-data page redirected to a rate-limited Hugging Face
  endpoint during acquisition.
- Disposition: the pinned repository fixture is `SMOKE_ONLY`; it is not a
  replacement for the full QASPER benchmark.

## Modular implementation

The new `factorized_benchmarks` subpackage contains:

- `contracts.py`: benchmark-neutral public case and private reference types;
- `catalog.py`: frozen sources, revisions, hashes, and license dispositions;
- `acquisition.py`: mechanical size and SHA-256 verification only;
- `scifact.py`: semantic-warrant adapter;
- `ebm_nlp.py`: study-object span-binding adapter;
- `qasper.py`: question-conditioned context-utility adapter;
- `smoke.py`: local cache inspection with zero Provider calls.

Public cases exclude gold states, rationale coordinates, answers, and object
span labels. Private references remain separate. Every public case explicitly
denies Core and retention writes.

## Smoke result

All three downloaded artifacts matched their frozen size and SHA-256:

| Source | Observed content |
|---|---|
| SciFact | 809 train claims, 300 dev claims, 300 unlabeled test claims, 5,183 corpus records |
| EBM-NLP | 4,993 documents, 4,993 token files, 216,089 annotation files |
| QASPER fixture | 1 article, 4 cases, 24 case-level evidence-unit instances |

The smoke made zero Provider calls and produced no CoreSlim, retention,
baseline, or production write.

## Experiment analysis

### Facts

- The external artifacts are locally readable and hash-stable.
- The adapters expose three distinct cognitive objects without forcing them
  into the v0.85 PICO admission schema.
- Private benchmark references remain outside Provider-visible public cases.
- EBM-NLP is not currently license-clear.
- Only a QASPER code fixture, not its full benchmark, is frozen.

### Phenomenon

The benchmark search confirms the v0.85 diagnosis: object recognition,
evidence warrant, and action utility are related but non-equivalent tasks.
Benchmarks naturally separate them because their gold annotations answer
different questions.

### Mechanism interpretation

The highest-Cbit architecture is a sequence of typed receipts rather than a
larger admission receipt:

1. `StudyObjectBindingReceipt` identifies the referenced object and relation.
2. `SemanticWarrantReceipt` judges whether evidence supports the target claim.
3. `KernelUtilityCompiler` applies AgentOS state rules to those receipts and
   retains final mutation authority.

Provider support belongs in the first two semantic layers and may estimate
utility, but the Kernel must compile final state under fixed safety,
provenance, replay, and rollback constraints.

### Rival explanations

- A sufficiently capable Provider might solve all three tasks in one prompt.
  v0.85 shows that schema-valid combined reasoning does not guarantee useful
  state mutation.
- A single benchmark score might correlate with end-to-end quality. It still
  cannot localize whether failure arose from object binding, warrant, or
  policy compilation.
- EBM-NLP's large annotation volume may appear ideal for immediate use, but
  unclear licensing prevents it from serving as a publishable frozen source.

### Negative result preserved

v0.86 does not validate Kernel utility, full QASPER generalization, or any
Provider-backed improvement. Those claims remain unavailable.

## Next preregistered stage

v0.87 should begin with SciFact dev data because its license and rationale
schema are explicit. It should:

1. freeze an unseen claim subset before Provider calls;
2. define a benchmark-neutral `SemanticWarrantReceipt`;
3. score label and rationale selection independently;
4. pass only validated warrant receipts to a no-write
   `KernelUtilityCompiler`;
5. report gross Cbit, harmful transitions, abstention, and token cost
   separately.

EBM-NLP remains blocked pending license clarification. Full QASPER acquisition
should be retried independently and must not block the SciFact warrant pilot.
