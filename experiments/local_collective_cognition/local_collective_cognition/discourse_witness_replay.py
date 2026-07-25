"""Zero-Provider replay of v0.69 witnesses over admitted discourse units."""

from __future__ import annotations

from .provider_telemetry import hash_payload


def build_discourse_replay(*, panel, source_run):
    invalid = {
        failure["case_id"]: failure["invalid_receipt"]
        for failure in source_run["contract_failures"]
        if "invalid_receipt" in failure
    }
    receipts, bases, failures, diagnostics = {}, {}, [], {}
    items = {
        item["case_id"]: item
        for item in panel["public_surface"]["items"]
    }
    for case_id, item in items.items():
        basis = source_run["basis_receipts"].get(case_id) or invalid.get(case_id)
        frame = source_run["frame_receipts"][case_id]
        if basis is None:
            failures.append({"case_id": case_id, "reason": "NO_BASIS_RECEIPT"})
            continue
        result = _ground_records(item, frame, basis["basis_records"])
        diagnostics[case_id] = result["diagnostics"]
        if result["failures"]:
            failures.append({
                "case_id": case_id,
                "reason": "DISCOURSE_WITNESS_UNGROUNDED",
                "contract_failures": result["failures"],
            })
            continue
        bases[case_id] = basis
        receipts[case_id] = _compile(
            item=item,
            source_run=source_run,
            basis=basis,
            grounded=result["records"],
        )
    value = {
        "runtime_version": "discourse_witness_replay_v0_70",
        "arm_id": "A6_DISCOURSE_WITNESS_REPLAY",
        "source_panel_hash": panel["artifact_hash"],
        "source_run_hash": source_run["run_hash"],
        "task_calls": source_run["task_calls"],
        "frame_receipts": source_run["frame_receipts"],
        "basis_receipts": bases,
        "receipts": receipts,
        "contract_failures": failures,
        "compiler_failures": [],
        "discourse_diagnostics": diagnostics,
        "provider_calls_added": 0,
        "private_gold_exposed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "run_hash": hash_payload(value)}


def _ground_records(item, frame, records):
    spans = {
        span["span_id"]: span["text"].casefold()
        for span in item["candidate_spans"]
    }
    aliases = {
        "FOCAL_INTERVENTION": {
            value.casefold() for value in frame["intervention_aliases"]
        },
        "FOCAL_COMPARATOR": {
            value.casefold() for value in frame["comparator_aliases"]
        },
    }
    grounded, failures, diagnostics = [], [], []
    for record in records:
        subject = record["subject_surface"].casefold()
        relation = record["relation_surface"].casefold()
        subject_spans = [
            span_id for span_id, text in spans.items()
            if subject and subject in text
        ]
        relation_spans = [
            span_id for span_id, text in spans.items()
            if relation and relation in text
        ]
        implicit = record["subject_surface_mode"] == "FRAME_IMPLICIT"
        subject_ok = implicit or (
            bool(subject_spans)
            and subject in aliases.get(record["subject_group_id"], set())
        )
        relation_ok = bool(relation_spans)
        if not subject_ok:
            failures.append(
                f"{record['span_id']}:SUBJECT_DISCOURSE_WITNESS_MISSING"
            )
        if not relation_ok:
            failures.append(
                f"{record['span_id']}:RELATION_DISCOURSE_WITNESS_MISSING"
            )
        witness_ids = sorted(set(subject_spans + relation_spans))
        grounded.append({**record, "witness_span_ids": witness_ids})
        diagnostics.append({
            "span_id": record["span_id"],
            "subject_witness_span_ids": subject_spans,
            "relation_witness_span_ids": relation_spans,
        })
    return {
        "records": grounded,
        "failures": failures,
        "diagnostics": diagnostics,
    }


def _compile(*, item, source_run, basis, grounded):
    usable = [
        record for record in grounded
        if record["evidence_relevance"] == "EXACT_OBJECT"
        and record["evidence_role"] in {"DECISIVE", "SUPPORTING"}
        and record["timepoint_binding"] not in {"DIFFERENT", "UNRESOLVED"}
        and record["measurement_binding"] not in {"DIFFERENT", "UNRESOLVED"}
    ]
    decisive = [
        record for record in usable if record["evidence_role"] == "DECISIVE"
    ]
    authoritative = decisive or usable
    labels = [_normalize(record) for record in authoritative]
    unique = {value for value in labels if value is not None}
    label = (
        next(iter(unique))
        if labels and None not in labels and len(unique) == 1
        else "UNRESOLVED_MATERIAL_AMBIGUITY"
    )
    partition = _partition(grounded)
    frame = source_run["frame_receipts"][item["case_id"]]
    catalog = source_run["arm_catalogs"][item["case_id"]]
    return {
        "case_id": item["case_id"],
        "mechanism": "A6_DISCOURSE_WITNESS_COMPILER",
        "source_item_hash": hash_payload(item),
        "source_arm_catalog_hash": catalog["catalog_hash"],
        "source_frame_hash": hash_payload(frame),
        "source_basis_hash": hash_payload(basis),
        "decision_state": (
            "DECISIVE" if label != "UNRESOLVED_MATERIAL_AMBIGUITY"
            else "UNRESOLVED_MATERIAL_AMBIGUITY"
        ),
        "predicted_label": label,
        "material_ambiguity": (
            "NONE" if label != "UNRESOLVED_MATERIAL_AMBIGUITY"
            else "INSUFFICIENT_BASIS"
        ),
        **partition,
        "normalized_basis": labels,
        "rationale": f"Discourse witness labels: {labels}.",
        "evidence_refs": source_run["receipts"].get(
            item["case_id"], {}
        ).get("evidence_refs", []),
        "provider_override_allowed": False,
    }


def _normalize(record):
    relation = record["observed_relation"]
    if relation == "NO_COMPARATIVE_EFFECT_REPORTED":
        return "NO_DIFFERENCE"
    if record["significance_state"] in {
        "NOT_SIGNIFICANT",
        "TREND_OR_BORDERLINE",
    } or relation == "NO_MATERIAL_DIFFERENCE":
        return "NO_DIFFERENCE"
    if record["significance_state"] != "SIGNIFICANT":
        return None
    direct = record["subject_group_id"] == "FOCAL_INTERVENTION"
    if direct:
        return {
            "SUBJECT_HIGHER": "INCREASED",
            "SUBJECT_LOWER": "DECREASED",
        }.get(relation)
    return {
        "SUBJECT_HIGHER": "DECREASED",
        "SUBJECT_LOWER": "INCREASED",
    }.get(relation)


def _partition(records):
    mapping = {
        "DECISIVE": "primary_span_ids",
        "SUPPORTING": "corroborating_span_ids",
        "COUNTER": "counter_span_ids",
        "EXCLUDE_UNRELATED": "rejected_after_basis_span_ids",
    }
    result = {field: [] for field in mapping.values()}
    for record in records:
        result[mapping[record["evidence_role"]]].append(record["span_id"])
    return result
