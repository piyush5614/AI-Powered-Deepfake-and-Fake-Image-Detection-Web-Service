from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Verdict = Literal["REAL", "FAKE"]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Probabilities(BaseModel):
    REAL: float = Field(ge=0, le=1)
    FAKE: float = Field(ge=0, le=1)


class ImageInfo(BaseModel):
    filename: str
    width: int
    height: int
    size_kb: int
    format: str


class ModelInfo(BaseModel):
    name: str
    input_size: int = 224


class AnalyzeResponse(BaseModel):
    id: str
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    probabilities: Probabilities
    heatmap: str
    original: str
    image_info: ImageInfo
    model: ModelInfo
    processing_ms: int
    created_at: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    version: str


class HistoryItem(BaseModel):
    id: str
    verdict: Verdict
    confidence: float
    filename: str
    created_at: str
    thumbnail: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
