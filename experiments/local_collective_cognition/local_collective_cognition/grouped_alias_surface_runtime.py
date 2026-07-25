"""v0.74 prospective surface runtime with grouped-object aliases."""

from __future__ import annotations

from .grouped_arm_aliases import (
    build_grouped_alias_catalog,
    validate_grouped_witness_frame,
)
from .prospective_surface_pipeline import run_surface_pipeline


def run_grouped_alias_surface_panel(
    *, panel, preregistration, admission_receipts, adapter
):
    return run_surface_pipeline(
        panel=panel,
        preregistration=preregistration,
        admission_receipts=admission_receipts,
        adapter=adapter,
        runtime_version="grouped_alias_surface_runtime_v0_74",
        arm_id="A10_GROUPED_ALIAS_SURFACE_PROJECTION",
        frame_metadata_factory=build_grouped_alias_catalog,
        frame_validator=validate_grouped_witness_frame,
    )
