"""Pinned external sources for the v0.65 benchmark bridge."""

from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


EVIDENCE_INFERENCE_COMMIT = "a661e8c14f973398380c8865cf2f27a535aaaf6d"
ERASER_COMMIT = "36467f1662812cbd4fbdd66879946cd7338e08ec"


@dataclass(frozen=True)
class SourceFile:
    name: str
    relative_path: str
    sha256: str
    size: int

    @property
    def url(self) -> str:
        return (
            "https://raw.githubusercontent.com/jayded/evidence-inference/"
            f"{EVIDENCE_INFERENCE_COMMIT}/{self.relative_path}"
        )


SOURCE_FILES = (
    SourceFile(
        "prompts.csv",
        "annotations/prompts_merged.csv",
        "0d70d9e1e78d113fdbbd4919310eab7768d6a328368f7d8f9d5a3b48f99c25d3",
        1498509,
    ),
    SourceFile(
        "annotations.csv",
        "annotations/annotations_merged.csv",
        "a5dd1a3583e5105a0f77d3e1c695008879859425c9a93dfbc07054ef462e0255",
        6570816,
    ),
    SourceFile(
        "validation_article_ids.txt",
        "annotations/splits/validation_article_ids.txt",
        "98a397d26cf97c8df7a847c5faae18a2747d0c3e7c324381efa31b3dc2ee1069",
        3981,
    ),
)

HOLDOUT_SPLIT_FILE = SourceFile(
    "test_article_ids.txt",
    "annotations/splits/test_article_ids.txt",
    "4fe6c633ba8f077a68a8feea48d4408c1749175e1c46f2b77d96727d291ef9d8",
    4029,
)


def default_cache_dir() -> Path:
    base = Path(
        os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    )
    return base / "AgentOS" / "benchmark_cache" / (
        f"evidence-inference-{EVIDENCE_INFERENCE_COMMIT}"
    )


def ensure_sources(cache_dir: Path | None = None) -> dict[str, Path]:
    root = (cache_dir or default_cache_dir()).resolve()
    root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for source in SOURCE_FILES:
        path = root / source.name
        if not path.exists() or _hash(path) != source.sha256:
            temporary = path.with_suffix(path.suffix + ".download")
            urllib.request.urlretrieve(source.url, temporary)
            if temporary.stat().st_size != source.size:
                temporary.unlink(missing_ok=True)
                raise ValueError(f"benchmark_source_size_mismatch:{source.name}")
            if _hash(temporary) != source.sha256:
                temporary.unlink(missing_ok=True)
                raise ValueError(f"benchmark_source_hash_mismatch:{source.name}")
            temporary.replace(path)
        paths[source.name] = path
    return paths


def ensure_holdout_source(cache_dir: Path | None = None) -> Path:
    root = (cache_dir or default_cache_dir()).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source = HOLDOUT_SPLIT_FILE
    path = root / source.name
    if not path.exists() or _hash(path) != source.sha256:
        temporary = path.with_suffix(path.suffix + ".download")
        urllib.request.urlretrieve(source.url, temporary)
        if temporary.stat().st_size != source.size:
            temporary.unlink(missing_ok=True)
            raise ValueError("benchmark_holdout_split_size_mismatch")
        if _hash(temporary) != source.sha256:
            temporary.unlink(missing_ok=True)
            raise ValueError("benchmark_holdout_split_hash_mismatch")
        temporary.replace(path)
    return path


def holdout_source_manifest() -> dict:
    base = source_manifest()
    return {
        **base,
        "evidence_inference_test_split": {
            "name": HOLDOUT_SPLIT_FILE.name,
            "relative_path": HOLDOUT_SPLIT_FILE.relative_path,
            "sha256": HOLDOUT_SPLIT_FILE.sha256,
            "size": HOLDOUT_SPLIT_FILE.size,
        },
    }


def source_manifest() -> dict:
    return {
        "evidence_inference": {
            "repository": "https://github.com/jayded/evidence-inference",
            "commit": EVIDENCE_INFERENCE_COMMIT,
            "license": "MIT",
            "files": [
                {
                    "name": source.name,
                    "relative_path": source.relative_path,
                    "sha256": source.sha256,
                    "size": source.size,
                }
                for source in SOURCE_FILES
            ],
        },
        "eraser_metric_reference": {
            "repository": "https://github.com/jayded/eraserbenchmark",
            "commit": ERASER_COMMIT,
            "license": "Apache-2.0",
            "use": "metric_semantics_only",
        },
        "raw_data_repository_write_allowed": False,
        "raw_data_cache_scope": "LOCAL_EXTERNAL_CACHE_ONLY",
    }


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
