from app.ingestion.audit import normalized_work_id


def test_work_id_normalization_removes_incidental_source_spaces() -> None:
    assert normalized_work_id("WS/ MP620/2024-2025/133166-Example") == "WS/MP620/2024-2025/133166"


def test_work_id_normalization_rejects_non_work_values() -> None:
    assert normalized_work_id("No work identity supplied") is None
