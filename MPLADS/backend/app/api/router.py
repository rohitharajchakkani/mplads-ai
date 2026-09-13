"""Versioned FastAPI surface over database-backed analytical services."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.analytics.dashboard_service import core_metrics, house_comparison
from app.analytics.data_quality_service import data_quality_metrics
from app.analytics.financial_analytics_service import expenditure_by, expenditure_summary
from app.analytics.geography_analytics_service import summarize_by
from app.analytics.lifecycle_analytics_service import lifecycle_summary
from app.analytics.filter_options_service import filter_options
from app.analytics.normalization import normalize_house, normalize_text
from app.analytics.trend_analytics_service import completion_trend, expenditure_trend, works_trend
from app.analytics.visualization_service import explore_visualization
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.analytics.work_analytics_service import status_distribution
from app.api.deps import get_db, require_active_dataset
from app.schemas.api import AnalyticsResponse, HealthResponse, PaginatedResponse
from app.services.dataset_service import active_metadata, list_versions
from app.services.entity_service import (
    district_detail, list_districts, list_mps, list_states, list_works, mp_detail,
    search, state_detail, work_detail,
)
from app.services.versioning_service import LifecycleError, resolve_active_scope

router = APIRouter()
ACTIVE = [Depends(require_active_dataset)]


def filters(
    house: str | None = Query(None), state: str | None = Query(None),
    district_or_ida: str | None = Query(None), mp: str | None = Query(None), work: str | None = Query(None),
    constituency: str | None = Query(None), financial_year: str | None = Query(None),
    sector: str | None = Query(None), subsector: str | None = Query(None),
    work_status: str | None = Query(None),
) -> AnalyticsFilters:
    return AnalyticsFilters(
        house=normalize_house(house), state=normalize_text(state), district_or_ida=normalize_text(district_or_ida),
        mp=normalize_text(mp), work=normalize_text(work), constituency=normalize_text(constituency), financial_year=normalize_text(financial_year),
        sector=normalize_text(sector), subsector=normalize_text(subsector), work_status=normalize_text(work_status),
    )


def _analytics(result) -> dict:
    return {"data": result.data, "provenance": result.provenance.__dict__}


def _page(result) -> dict:
    return {
        "items": result.data["items"], "pagination": result.data["pagination"],
        "provenance": result.provenance.__dict__,
    }


def _run(operation):
    try:
        return operation()
    except LifecycleError as exc:
        raise HTTPException(503, detail={"code": "NO_ACTIVE_DATASET", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "INVALID_OR_UNSUPPORTED_FILTER", "message": str(exc)}) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Database is unavailable."}) from exc


def _metadata(db: Session, data: dict, service: str) -> dict:
    scope = resolve_active_scope(db)
    return {
        "data": data,
        "provenance": {
            "service": service, "release_version": scope.release_version,
            "batch_id": scope.batch_id, "filters": {},
            "generated_at": datetime.now(UTC).isoformat(),
        },
    }


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(db: Session = Depends(get_db)) -> HealthResponse:
    """Report application, database, release, and migration health from live state."""
    try:
        db.execute(text("SELECT 1"))
        scope = resolve_active_scope(db)
        return HealthResponse(
            status="ok", database_status="ok", active_dataset_status="ACTIVE",
            active_release_version=scope.release_version,
            migration_version=db.execute(text("SELECT version_num FROM alembic_version")).scalar(),
            message="Application, database, and active dataset are available.",
        )
    except LifecycleError as exc:
        return HealthResponse(
            status="degraded", database_status="ok", active_dataset_status="UNAVAILABLE",
            active_release_version=None, migration_version=None, message=str(exc),
        )
    except Exception as exc:
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Database is unavailable."}) from exc


@router.get("/dashboard/summary", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["dashboard"])
def dashboard_summary(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(core_metrics(db, f)))


@router.get("/dashboard/work-status", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["dashboard"])
def dashboard_work_status(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(status_distribution(db, f)))


@router.get("/dashboard/house-comparison", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["dashboard"])
def dashboard_house_comparison(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(house_comparison(db, f)))


@router.get("/dashboard/state-summary", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["dashboard"])
def dashboard_state_summary(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(summarize_by(db, "state", f)))


@router.get("/dashboard/expenditure-trend", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["dashboard"])
def dashboard_expenditure_trend(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(expenditure_trend(db, f)))


@router.get("/dashboard/completion-summary", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["dashboard"])
def dashboard_completion_summary(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(completion_trend(db, f)))


@router.get("/filters/options", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["filters"])
def filter_options_endpoint(
    field: str = Query(...), query: str | None = Query(None), limit: int = Query(50, ge=1, le=100),
    f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db),
):
    return _run(lambda: _analytics(filter_options(db, field, f, normalize_text(query), limit)))


@router.get("/visualizations/explore", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["visualizations"])
def visualizations_explore(
    metric: str = Query(...), group_by: str = Query(...),
    f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db),
):
    return _run(lambda: _analytics(explore_visualization(db, metric, group_by, f)))


@router.get("/dashboard/sector-summary", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["dashboard"])
def dashboard_sector_summary(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(AnalyticsResult(
        {"data_available": False, "message": "Not available from the current source data; no verified sector or subsector field exists."},
        provenance("dashboard_service.sector_summary", resolve_active_scope(db), f),
    )))


@router.get("/mps", response_model=PaginatedResponse, dependencies=ACTIVE, tags=["mps"])
def mps(
    f: AnalyticsFilters = Depends(filters), search_query: str | None = Query(None, alias="search"),
    page: int = Query(1), page_size: int = Query(25, le=100), sort: str = Query("name"),
    db: Session = Depends(get_db),
):
    return _run(lambda: _page(list_mps(db, f, search_query, page, page_size, sort)))


@router.get("/mps/{mp_id}", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["mps"])
def get_mp(mp_id: str, db: Session = Depends(get_db)):
    result = _run(lambda: mp_detail(db, mp_id))
    if result is None:
        raise HTTPException(404, detail={"code": "MP_NOT_FOUND", "message": "MP not found."})
    return _analytics(result)


@router.get("/states", response_model=PaginatedResponse, dependencies=ACTIVE, tags=["states"])
def states(f: AnalyticsFilters = Depends(filters), page: int = Query(1), page_size: int = Query(25, le=100), db: Session = Depends(get_db)):
    return _run(lambda: _page(list_states(db, f, page, page_size)))


@router.get("/states/{state_id}", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["states"])
def get_state(state_id: str, db: Session = Depends(get_db)):
    result = _run(lambda: state_detail(db, state_id))
    if result is None:
        raise HTTPException(404, detail={"code": "STATE_NOT_FOUND", "message": "State not found."})
    return _analytics(result)


@router.get("/districts", response_model=PaginatedResponse, dependencies=ACTIVE, tags=["districts"])
def districts(f: AnalyticsFilters = Depends(filters), page: int = Query(1), page_size: int = Query(25, le=100), db: Session = Depends(get_db)):
    return _run(lambda: _page(list_districts(db, f, page, page_size)))


@router.get("/districts/{district_id}", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["districts"])
def get_district(district_id: str, db: Session = Depends(get_db)):
    result = _run(lambda: district_detail(db, district_id))
    if result is None:
        raise HTTPException(404, detail={"code": "DISTRICT_NOT_FOUND", "message": "District/IDA not found."})
    return _analytics(result)


@router.get("/works", response_model=PaginatedResponse, dependencies=ACTIVE, tags=["works"])
def works(
    f: AnalyticsFilters = Depends(filters), search_query: str | None = Query(None, alias="search"),
    page: int = Query(1), page_size: int = Query(25, le=100), sort: str = Query("work_id"),
    db: Session = Depends(get_db),
):
    return _run(lambda: _page(list_works(db, f, search_query, page, page_size, sort)))


@router.get("/works/{work_key:path}", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["works"])
def get_work(work_key: str, db: Session = Depends(get_db)):
    result = _run(lambda: work_detail(db, work_key))
    if result is None:
        raise HTTPException(404, detail={"code": "WORK_NOT_FOUND", "message": "Work not found."})
    return _analytics(result)


@router.get("/financial/summary", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["financial"])
def financial_summary(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(expenditure_summary(db, f)))


@router.get("/financial/by-house", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["financial"])
def financial_by_house(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(expenditure_by(db, "house", f)))


@router.get("/financial/by-state", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["financial"])
def financial_by_state(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(expenditure_by(db, "state", f)))


@router.get("/financial/by-mp", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["financial"])
def financial_by_mp(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(expenditure_by(db, "mp", f)))


@router.get("/financial/by-district", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["financial"])
def financial_by_district(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(expenditure_by(db, "district_or_ida", f)))


@router.get("/trends/lifecycle", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["trends"])
def trends_lifecycle(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(lifecycle_summary(db, f)))


@router.get("/trends/works", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["trends"])
def trends_works(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(works_trend(db, f)))


@router.get("/trends/expenditure", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["trends"])
def trends_expenditure(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(expenditure_trend(db, f)))


@router.get("/trends/completion", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["trends"])
def trends_completion(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(completion_trend(db, f)))


@router.get("/search", response_model=PaginatedResponse, dependencies=ACTIVE, tags=["search"])
def global_search(q: str = Query(..., min_length=1), page: int = Query(1), page_size: int = Query(25, le=100), db: Session = Depends(get_db)):
    return _run(lambda: _page(search(db, q, page, page_size)))


@router.get("/data-quality/summary", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["data quality"])
def quality_summary(f: AnalyticsFilters = Depends(filters), db: Session = Depends(get_db)):
    return _run(lambda: _analytics(data_quality_metrics(db, f)))


@router.get("/datasets/active", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["datasets"])
def datasets_active(db: Session = Depends(get_db)):
    return _run(lambda: _metadata(db, active_metadata(db), "dataset_service.active_metadata"))


@router.get("/datasets/versions", response_model=AnalyticsResponse, dependencies=ACTIVE, tags=["datasets"])
def datasets_versions(db: Session = Depends(get_db)):
    return _run(lambda: _metadata(db, list_versions(db), "dataset_service.list_versions"))
