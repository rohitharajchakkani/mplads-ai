"""Deterministic, source-preserving Phase 5 ingestion service."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.inspect import load_xlsx_table_with_provenance
from app.ingestion.normalization import canonical_work_key, classify_work_reference, clean_text, parse_date, parse_money
from app.models import (
    AllocatedLimitRecord, CalamityRecord, CanonicalWork, CompletedWorkRecord, DatasetVersion,
    ExpenditureTransaction, IngestionBatch, RecommendedWorkRecord, SanctionedWorkRecord,
    StagingAllocatedLimit, StagingCalamity, StagingCompletedWork, StagingExpenditure,
    StagingRecommendedWork, StagingSanctionedWork, ValidationFinding,
)

APPLICATION_VERSION = "0.1.0"
INGESTION_VERSION = "phase5-v2"
FINANCIAL_YEAR_PATTERN = re.compile(r"WS/MP\d+/(\d{4}-\d{4})/\d+", re.IGNORECASE)


def _raw(row: dict[str, Any], name: str) -> Any:
    return row.get(name)


def _field_errors(row: dict[str, Any], names: Iterable[str]) -> list[tuple[str, str, str, str]]:
    return [("ERROR", "MISSING_CRITICAL_FIELD", name, f"Required source field '{name}' is blank.") for name in names if clean_text(_raw(row, name)) is None]


def _date(value: Any, field: str, required: bool = False) -> tuple[str | None, list[tuple[str, str, str, str]]]:
    parsed, issue = parse_date(value)
    if issue is None:
        return parsed, []
    severity = "ERROR" if required else "WARNING"
    return None, [(severity, issue, field, f"{field} could not be parsed from the preserved source value.")]


def _money(value: Any, field: str, required: bool = False):
    parsed, issue = parse_money(value)
    if issue is None:
        return parsed, []
    severity = "ERROR" if required else "WARNING"
    return None, [(severity, issue, field, f"{field} could not be parsed from the preserved source value.")]


def _status(findings: list[tuple[str, str, str, str]]) -> str:
    if any(item[0] == "ERROR" for item in findings):
        return "REJECTED"
    if any(item[0] == "WARNING" for item in findings):
        return "VALID_WITH_WARNINGS"
    return "VALID"


def _common(row: dict[str, Any], house: str, work_value: Any | None = None) -> tuple[dict[str, Any], list[tuple[str, str, str, str]]]:
    findings = []
    if work_value is None:
        return {}, findings
    work_id, work_status = classify_work_reference(work_value)
    if work_status != "RESOLVED":
        code = "BLANK_SOURCE_WORK_REFERENCE" if work_status.startswith("BLANK") else "UNRESOLVED_SOURCE_WORK_REFERENCE"
        findings.append(("WARNING", code, "Work ID", "Source work reference is retained but cannot be linked to a canonical work."))
    return {"normalized_work_id": work_id, "work_reference_status": work_status}, findings


def build_staging_record(dataset_type: str, house: str, row: dict[str, Any], context: dict[str, Any]):
    """Return a domain-specific staging object plus deterministic validation findings."""
    base = {
        **context,
        "source_sequence": clean_text(_raw(row, "Sr. No.")),
        "house": house,
        "source_values": row,
    }
    findings: list[tuple[str, str, str, str]] = []
    if dataset_type == "ALLOCATED_LIMIT":
        amount, issues = _money(_raw(row, "Allocated AMOUNT ( ₹ )"), "Allocated AMOUNT ( ₹ )", required=True)
        findings += _field_errors(row, ["State", "Hon'ble Members of Parliaments" if house == "LOK_SABHA" else "Hon'ble Members of Parliament"])
        findings += issues
        values = {"state_name": clean_text(_raw(row, "State")), "mp_source_name": clean_text(_raw(row, "Hon'ble Members of Parliaments") or _raw(row, "Hon'ble Members of Parliament")), "constituency_name": clean_text(_raw(row, "Constituency")), "membership_type": clean_text(_raw(row, "Elected/Nominated")), "allocated_amount": amount}
        model = StagingAllocatedLimit
    elif dataset_type == "CALAMITY":
        consent_date, date_issues = _date(_raw(row, "Date of Consent"), "Date of Consent")
        amount, money_issues = _money(_raw(row, "Consent Amount ( ₹ )"), "Consent Amount ( ₹ )", required=True)
        findings += date_issues + money_issues
        values = {"calamity_type": clean_text(_raw(row, "Calamity Type")), "calamity_name": clean_text(_raw(row, "Calamity Name")), "mp_source_name": clean_text(_raw(row, "Hon'ble Members of Parliament")), "consent_date_raw": clean_text(_raw(row, "Date of Consent")), "consent_date": consent_date, "consent_amount": amount}
        model = StagingCalamity
    elif dataset_type in {"WORKS_RECOMMENDED", "WORKS_SANCTIONED"}:
        work_value = _raw(row, "WORK") if dataset_type == "WORKS_RECOMMENDED" else _raw(row, "Work")
        work, work_issues = _common(row, house, work_value)
        recommended_date, recommended_issues = _date(_raw(row, "Recommended date"), "Recommended date")
        sanction_date, sanction_issues = _date(_raw(row, "Sanction Date"), "Sanction Date")
        findings += _field_errors(row, ["State", "IDA", "Hon'ble Members of Parliament", "Work description"])
        findings += work_issues + recommended_issues + sanction_issues
        values = {**work, "work_category_source": clean_text(_raw(row, "Work category")), "work_source_label": clean_text(work_value), "state_name": clean_text(_raw(row, "State")), "district_or_ida": clean_text(_raw(row, "IDA")), "mp_source_name": clean_text(_raw(row, "Hon'ble Members of Parliament")), "constituency_name": clean_text(_raw(row, "Constituency")), "membership_type": clean_text(_raw(row, "Elected/Nominated")), "work_description": clean_text(_raw(row, "Work description")), "recommended_date_raw": clean_text(_raw(row, "Recommended date")), "recommended_date": recommended_date, "sanction_date_raw": clean_text(_raw(row, "Sanction Date")), "sanction_date": sanction_date}
        if dataset_type == "WORKS_RECOMMENDED":
            amount, issues = _money(_raw(row, "RECOMMENDED AMOUNT   ( ₹ )"), "RECOMMENDED AMOUNT   ( ₹ )")
            findings += issues
            values["recommended_amount"] = amount
            model = StagingRecommendedWork
        else:
            amount, issues = _money(_raw(row, "Sanction Amount ( ₹ )"), "Sanction Amount ( ₹ )")
            findings += issues
            values.update({"sanction_amount": amount, "work_status_source": clean_text(_raw(row, "Work Status"))})
            model = StagingSanctionedWork
    elif dataset_type == "EXPENDITURE":
        work, work_issues = _common(row, house, _raw(row, "Work ID"))
        expense_date, date_issues = _date(_raw(row, "Expenditure Date"), "Expenditure Date")
        amount, money_issues = _money(_raw(row, "Fund Disbursed Amount ( ₹ )"), "Fund Disbursed Amount ( ₹ )", required=True)
        findings += _field_errors(row, ["State", "IDA", "Hon'ble Members of Parliament"])
        findings += work_issues + date_issues + money_issues
        values = {**work, "work_source_label": clean_text(_raw(row, "Work")), "state_name": clean_text(_raw(row, "State")), "district_or_ida": clean_text(_raw(row, "IDA")), "mp_source_name": clean_text(_raw(row, "Hon'ble Members of Parliament")), "constituency_name": clean_text(_raw(row, "Constituency")), "membership_type": clean_text(_raw(row, "Elected/Nominated")), "expenditure_date_raw": clean_text(_raw(row, "Expenditure Date")), "expenditure_date": expense_date, "vendor_name": clean_text(_raw(row, "Vendor Name")), "payment_status_source": clean_text(_raw(row, "Payment Status")), "disbursed_amount": amount}
        model = StagingExpenditure
    elif dataset_type == "WORKS_COMPLETED":
        work, work_issues = _common(row, house, _raw(row, "Work"))
        completion_date, date_issues = _date(_raw(row, "Completion Date"), "Completion Date")
        amount, money_issues = _money(_raw(row, "Amount Disbursed ( ₹ )"), "Amount Disbursed ( ₹ )")
        findings += _field_errors(row, ["State", "IDA", "Hon'ble Members of Parliament", "Work Description"])
        findings += work_issues + date_issues + money_issues
        values = {**work, "work_category_source": clean_text(_raw(row, "Work Category")), "work_source_label": clean_text(_raw(row, "Work")), "state_name": clean_text(_raw(row, "State")), "district_or_ida": clean_text(_raw(row, "IDA")), "work_description": clean_text(_raw(row, "Work Description")), "mp_source_name": clean_text(_raw(row, "Hon'ble Members of Parliament")), "constituency_name": clean_text(_raw(row, "Constituency")), "membership_type": clean_text(_raw(row, "Elected/Nominated")), "image_availability_source": clean_text(_raw(row, "Image")), "completion_date_raw": clean_text(_raw(row, "Completion Date")), "completion_date": completion_date, "completed_reported_disbursed_amount": amount}
        model = StagingCompletedWork
    else:
        raise ValueError(f"Unsupported audited dataset type: {dataset_type}")
    base["normalized_candidates"] = {key: str(value) if value is not None else None for key, value in values.items()}
    base["validation_status"] = _status(findings)
    base["work_reference_status"] = values.pop("work_reference_status", None)
    return model(**base, **values), findings


def source_fingerprint(manifest: dict[str, Any], data_root: Path) -> str:
    entries = []
    for item in sorted(manifest["datasets"], key=lambda value: value["order"]):
        source = data_root / item["source_file"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        entries.append({"order": item["order"], "checksum": digest, "path": item["source_file"]})
    return hashlib.sha256(json.dumps({"ingestion_version": INGESTION_VERSION, "sources": entries}, sort_keys=True).encode()).hexdigest()


def ingest_sources(session: Session, manifest: dict[str, Any], data_root: Path, operator: str = "system") -> dict[str, Any]:
    fingerprint = source_fingerprint(manifest, data_root)
    batch_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{INGESTION_VERSION}:{fingerprint}"))
    existing = session.get(IngestionBatch, batch_id)
    if existing and existing.status in {"VALIDATED", "APPROVED", "PROMOTED", "ACTIVE", "HISTORICAL"}:
        return {**(existing.summary or {}), "batch_id": existing.id, "idempotent_reuse": True}
    if existing:
        raise RuntimeError(f"Existing batch {batch_id} is in status {existing.status}; it will not be overwritten.")
    now = datetime.now(UTC)
    batch = IngestionBatch(id=batch_id, source_set_fingerprint=fingerprint, ingestion_version=INGESTION_VERSION, application_version=APPLICATION_VERSION, status="DISCOVERED", operator=operator, started_at=now, finished_at=None, error_summary=None, summary=None)
    session.add(batch)
    session.flush()
    summaries: list[dict[str, Any]] = []
    try:
        for definition in sorted(manifest["datasets"], key=lambda value: value["order"]):
            source_path = data_root / definition["source_file"]
            headers, source_rows = load_xlsx_table_with_provenance(source_path, header_source_row=manifest["header_source_row"])
            rows = [(number, values) for number, values in source_rows if any(value is not None and str(value).strip() for value in values)]
            digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            dataset_version = DatasetVersion(batch_id=batch_id, dataset_type=definition["dataset_type"], house=definition["house"], version=f"{manifest['manifest_version']}:{INGESTION_VERSION}", source_filename=source_path.name, source_sheet="Sheet1", source_checksum=digest, source_row_count=len(rows), staged_row_count=0, valid_row_count=0, warning_row_count=0, rejected_row_count=0, status="DISCOVERED")
            session.add(dataset_version)
            session.flush()
            counters: Counter[str] = Counter()
            pending = []
            for source_row_number, values in rows:
                row = dict(zip(headers, values))
                record, findings = build_staging_record(definition["dataset_type"], definition["house"], row, {"batch_id": batch_id, "dataset_version_id": dataset_version.id, "source_row_number": source_row_number})
                pending.append(record)
                for severity, code, field, message in findings:
                    pending.append(ValidationFinding(batch_id=batch_id, dataset_version_id=dataset_version.id, source_row_number=source_row_number, severity=severity, code=code, field_name=field, message=message))
                counters[record.validation_status] += 1
                counters[record.work_reference_status or "NOT_APPLICABLE"] += 1
                if len(pending) >= 2000:
                    session.add_all(pending)
                    session.flush()
                    pending.clear()
            if pending:
                session.add_all(pending)
                session.flush()
            dataset_version.staged_row_count = len(rows)
            dataset_version.valid_row_count = counters["VALID"]
            dataset_version.warning_row_count = counters["VALID_WITH_WARNINGS"]
            dataset_version.rejected_row_count = counters["REJECTED"]
            dataset_version.status = "VALIDATED"
            summaries.append({"order": definition["order"], "house": definition["house"], "dataset_type": definition["dataset_type"], "source_rows": len(rows), "staged_rows": len(rows), "valid_rows": counters["VALID"], "warning_rows": counters["VALID_WITH_WARNINGS"], "rejected_rows": counters["REJECTED"], "unresolved_rows": counters["UNRESOLVED_SOURCE_WORK_REFERENCE"], "blank_id_rows": counters["BLANK_OR_UNRESOLVED_SOURCE_RECORD"]})
            session.commit()
        batch.status = "STAGED"
        session.commit()
        canonical_summary = canonicalize(session, batch_id)
        batch.status = "VALIDATED"
        batch.finished_at = datetime.now(UTC)
        summary = {"batch_id": batch_id, "idempotent_reuse": False, "source_rows": sum(item["source_rows"] for item in summaries), "staged_rows": sum(item["staged_rows"] for item in summaries), "datasets": summaries, "canonical": canonical_summary}
        batch.summary = summary
        session.commit()
        return summary
    except Exception as exc:
        session.rollback()
        failed = session.get(IngestionBatch, batch_id)
        if failed:
            failed.status = "FAILED"
            failed.error_summary = str(exc)
            failed.finished_at = datetime.now(UTC)
            session.commit()
        raise


def canonicalize(session: Session, batch_id: str) -> dict[str, int]:
    stage_models = [StagingRecommendedWork, StagingSanctionedWork, StagingExpenditure, StagingCompletedWork]
    works: dict[str, dict[str, Any]] = {}
    for model in stage_models:
        columns = [model.house, model.normalized_work_id, model.dataset_version_id, model.state_name, model.district_or_ida, model.mp_source_name]
        if hasattr(model, "constituency_name"):
            columns.append(model.constituency_name)
        if hasattr(model, "membership_type"):
            columns.append(model.membership_type)
        if hasattr(model, "work_category_source"):
            columns.append(model.work_category_source)
        if hasattr(model, "work_description"):
            columns.append(model.work_description)
        for values in session.execute(select(*columns).where(model.batch_id == batch_id, model.normalized_work_id.is_not(None), model.validation_status != "REJECTED")).yield_per(2000):
            data = values._mapping
            key = canonical_work_key(data[model.house], data[model.normalized_work_id])
            source_work_id = data[model.normalized_work_id]
            financial_year = FINANCIAL_YEAR_PATTERN.search(source_work_id)
            works.setdefault(key, {"canonical_work_key": key, "house": data[model.house], "normalized_work_id": source_work_id, "financial_year": financial_year.group(1) if financial_year else None, "state_name": data.get("state_name"), "district_or_ida": data.get("district_or_ida"), "mp_source_name": data.get("mp_source_name"), "constituency_name": data.get("constituency_name"), "membership_type": data.get("membership_type"), "work_category_source": data.get("work_category_source"), "work_description": data.get("work_description"), "first_dataset_version_id": data[model.dataset_version_id]})
    session.add_all(CanonicalWork(**values) for values in works.values())
    session.flush()
    mappings = [
        (StagingRecommendedWork, RecommendedWorkRecord, lambda row, key: {"recommended_date": row.recommended_date, "recommended_amount": row.recommended_amount, "work_reference_status": row.work_reference_status or "NOT_APPLICABLE"}),
        (StagingSanctionedWork, SanctionedWorkRecord, lambda row, key: {"recommended_date": row.recommended_date, "sanction_date": row.sanction_date, "sanction_amount": row.sanction_amount, "work_status_source": row.work_status_source, "work_reference_status": row.work_reference_status or "NOT_APPLICABLE"}),
        (StagingCompletedWork, CompletedWorkRecord, lambda row, key: {"completion_date": row.completion_date, "completed_reported_disbursed_amount": row.completed_reported_disbursed_amount, "work_reference_status": row.work_reference_status or "NOT_APPLICABLE"}),
        (StagingExpenditure, ExpenditureTransaction, lambda row, key: {"expenditure_date": row.expenditure_date, "vendor_name": row.vendor_name, "payment_status_source": row.payment_status_source, "disbursed_amount": row.disbursed_amount, "work_reference_status": row.work_reference_status or "NOT_APPLICABLE"}),
    ]
    for stage_model, canonical_model, extra in mappings:
        for row in session.scalars(select(stage_model).where(stage_model.batch_id == batch_id, stage_model.validation_status != "REJECTED")).yield_per(1000):
            key = canonical_work_key(row.house, row.normalized_work_id)
            session.add(canonical_model(staging_id=row.id, canonical_work_key=key, house=row.house, source_dataset_version_id=row.dataset_version_id, **extra(row, key)))
    for row in session.scalars(select(StagingAllocatedLimit).where(StagingAllocatedLimit.batch_id == batch_id, StagingAllocatedLimit.validation_status != "REJECTED")).yield_per(1000):
        session.add(AllocatedLimitRecord(staging_id=row.id, house=row.house, source_dataset_version_id=row.dataset_version_id, state_name=row.state_name, mp_source_name=row.mp_source_name, constituency_name=row.constituency_name, membership_type=row.membership_type, allocated_amount=row.allocated_amount))
    for row in session.scalars(select(StagingCalamity).where(StagingCalamity.batch_id == batch_id, StagingCalamity.validation_status != "REJECTED")).yield_per(1000):
        session.add(CalamityRecord(staging_id=row.id, house=row.house, source_dataset_version_id=row.dataset_version_id, calamity_type=row.calamity_type, calamity_name=row.calamity_name, mp_source_name=row.mp_source_name, consent_date=row.consent_date, consent_amount=row.consent_amount))
    session.commit()
    tables = {"canonical_works": CanonicalWork, "recommended_records": RecommendedWorkRecord, "sanctioned_records": SanctionedWorkRecord, "completed_records": CompletedWorkRecord, "expenditure_transactions": ExpenditureTransaction, "allocated_limit_records": AllocatedLimitRecord, "calamity_records": CalamityRecord}
    return {name: int(session.scalar(select(func.count()).select_from(model))) for name, model in tables.items()}
