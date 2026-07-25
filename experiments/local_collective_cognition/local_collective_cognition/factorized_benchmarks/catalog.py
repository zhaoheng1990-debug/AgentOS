"""Frozen source catalog for the v0.86 benchmark acquisition screen."""

from __future__ import annotations

from .contracts import BenchmarkLayer, BenchmarkSource, LicenseDisposition

CATALOG_VERSION = "factorized_benchmark_catalog_v0_86"

BENCHMARK_SOURCES = (
    BenchmarkSource(
        source_id="SCIFACT_RELEASE_LATEST_20210126",
        benchmark_name="SciFact",
        layer=BenchmarkLayer.SEMANTIC_WARRANT,
        repository_url="https://github.com/allenai/scifact",
        artifact_url=(
            "https://scifact.s3-us-west-2.amazonaws.com/"
            "release/latest/data.tar.gz"
        ),
        artifact_sha256=(
            "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be"
        ),
        artifact_size_bytes=3_115_079,
        license_disposition=LicenseDisposition.EXTERNAL_REFERENCE_ALLOWED,
        license_note=(
            "Claims/evidence: CC BY 4.0; corpus abstracts: ODC-By 1.0; "
            "code: Apache-2.0. Keep the dataset external and retain attribution."
        ),
        revision="68b98a56d93e0f9da0d2aab4e6c3294699a0f72e",
    ),
    BenchmarkSource(
        source_id="EBM_NLP_2_00",
        benchmark_name="EBM-NLP",
        layer=BenchmarkLayer.STUDY_OBJECT_BINDING,
        repository_url="https://github.com/bepnye/EBM-NLP",
        artifact_url=(
            "https://raw.githubusercontent.com/bepnye/EBM-NLP/"
            "43a4a1ea3f0a21cfb8820c040b843dfaf66192d0/"
            "ebm_nlp_2_00.tar.gz"
        ),
        artifact_sha256=(
            "b7357503911ba9f708d04e24c1ab3fe9e0a79833910e53e2472ed21214a44e3f"
        ),
        artifact_size_bytes=16_022_194,
        license_disposition=LicenseDisposition.BLOCKED_LICENSE_UNCLEAR,
        license_note=(
            "The repository describes the corpus but exposes no license file "
            "or GitHub license metadata. Local schema smoke only pending clarification."
        ),
        revision="43a4a1ea3f0a21cfb8820c040b843dfaf66192d0",
    ),
    BenchmarkSource(
        source_id="QASPER_LED_FIXTURE_AFD0FB9",
        benchmark_name="QASPER fixture",
        layer=BenchmarkLayer.CONTEXT_UTILITY,
        repository_url="https://github.com/allenai/qasper-led-baseline",
        artifact_url=(
            "https://raw.githubusercontent.com/allenai/qasper-led-baseline/"
            "afd0fb96bf78ce8cd8157639c6f6a6995e4f9089/"
            "fixtures/data/qasper_sample_small.json"
        ),
        artifact_sha256=(
            "942ce1c63822568da0d77ddcbdcfa6f469dad17336cf003fee0e9dbd010ee9ba"
        ),
        artifact_size_bytes=5_158,
        license_disposition=LicenseDisposition.SMOKE_ONLY,
        license_note=(
            "The baseline repository is Apache-2.0. This pinned fixture validates "
            "the adapter only; it is not a substitute for the full QASPER benchmark."
        ),
        revision="afd0fb96bf78ce8cd8157639c6f6a6995e4f9089",
    ),
)


def source_by_id(source_id: str) -> BenchmarkSource:
    for source in BENCHMARK_SOURCES:
        if source.source_id == source_id:
            return source
    raise KeyError(source_id)
