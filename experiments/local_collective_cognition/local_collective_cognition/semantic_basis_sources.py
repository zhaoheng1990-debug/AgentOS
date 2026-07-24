"""Pinned fresh-split source for v0.66."""

from __future__ import annotations

import urllib.request
from hashlib import sha256
from pathlib import Path

from .benchmark_bridge_sources import (
    EVIDENCE_INFERENCE_COMMIT,
    SourceFile,
    default_cache_dir,
    ensure_sources,
    source_manifest,
)


TRAIN_SPLIT_FILE = SourceFile(
    "train_article_ids.txt",
    "annotations/splits/train_article_ids.txt",
    "c72635d92c988e431403439eb9e4ce3fbb2ca0df84005fc9387b1eb2b035c3cc",
    31966,
)


def ensure_semantic_basis_sources() -> dict[str, Path]:
    paths = ensure_sources()
    root = default_cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    source = TRAIN_SPLIT_FILE
    path = root / source.name
    if not path.exists() or _hash(path) != source.sha256:
        temporary = path.with_suffix(path.suffix + ".download")
        url = (
            "https://raw.githubusercontent.com/jayded/evidence-inference/"
            f"{EVIDENCE_INFERENCE_COMMIT}/{source.relative_path}"
        )
        urllib.request.urlretrieve(url, temporary)
        if temporary.stat().st_size != source.size:
            temporary.unlink(missing_ok=True)
            raise ValueError("semantic_basis_train_split_size_mismatch")
        if _hash(temporary) != source.sha256:
            temporary.unlink(missing_ok=True)
            raise ValueError("semantic_basis_train_split_hash_mismatch")
        temporary.replace(path)
    paths[source.name] = path
    return paths


def semantic_basis_source_manifest() -> dict:
    return {
        **source_manifest(),
        "evidence_inference_fresh_split": {
            "name": TRAIN_SPLIT_FILE.name,
            "relative_path": TRAIN_SPLIT_FILE.relative_path,
            "sha256": TRAIN_SPLIT_FILE.sha256,
            "size": TRAIN_SPLIT_FILE.size,
            "benchmark_split_name": "train",
            "agentos_use": "previously_unused_frozen_transfer_holdout",
        },
    }


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
