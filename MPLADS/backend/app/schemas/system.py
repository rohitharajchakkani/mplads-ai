from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    dataset_status: Literal["not_loaded"]
    message: str

