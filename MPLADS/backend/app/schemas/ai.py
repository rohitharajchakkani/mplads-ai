"""Strict read-only Ask AI API contracts."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.ai.registry import ToolResult


class AskAiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=2, max_length=1000)
    context: dict[str, str] = Field(default_factory=dict, max_length=6)
    conversation: list[str] = Field(default_factory=list, max_length=4)


class AskAiResponse(BaseModel):
    request_id: str
    answer: str
    intent: str
    tool_results_summary: dict
    tool_result: ToolResult | None = None
    visualization: dict | None = None
    grounding: dict[str, str]
    provenance: dict
    dataset_version: str | None
    generated_at: datetime
    scope: dict[str, str | None]
    warnings: list[str]
    navigation_links: list[dict[str, str]]
    clarification_required: bool = False
    clarification_options: list[dict[str, object]] = Field(default_factory=list)
