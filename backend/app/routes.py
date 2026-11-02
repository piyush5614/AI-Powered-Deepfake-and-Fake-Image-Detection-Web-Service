import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.app.config import CLASS_NAMES, settings
from backend.app.db import AnalysisDatabase
from backend.app.errors import ApiException
from backend.app.images import decode_image, image_data_url, make_original, make_thumbnail, read_upload
from backend.app.schemas import AnalyzeResponse, HealthResponse, HistoryItem, HistoryResponse, ImageInfo, ModelInfo, Probabilities


logger = logging.getLogger("truthlens")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    predictor = getattr(request.app.state, "predictor", None)
    return HealthResponse(
        status="ok",
        model_loaded=predictor is not None,
        model_name=getattr(predictor, "arch", settings.model_arch),
        version="1.0.0",
    )


@router.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit(settings.rate_limit)
async def analyze(request: Request, file: Annotated[UploadFile | None, File()] = None) -> AnalyzeResponse:
    if file is None:
        raise ApiException(400, "no_file", "Choose an image to analyze.")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await read_upload(file, max_bytes)
    decoded = decode_image(data, file.filename)
    predictor = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise ApiException(503, "model_not_loaded", "The detection model is not available yet.")

    started = time.perf_counter()
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        prediction = await run_in_threadpool(predictor.predict, decoded.image)
    except Exception as exc:
        logger.exception("Inference failed (request_id=%s)", request_id, exc_info=exc)
        raise ApiException(500, "inference_failed", "The image could not be analyzed. Please try again.") from exc

    elapsed_ms = max(0, round((time.perf_counter() - started) * 1000))
    analysis_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    original_buffer = make_original(decoded.image)
    thumbnail = make_thumbnail(decoded.image)
    heatmap = prediction["heatmap"]
    probabilities = prediction["probabilities"]
    result = AnalyzeResponse(
        id=analysis_id,
        verdict=prediction["label"],
        confidence=prediction["confidence"],
        probabilities=Probabilities(REAL=probabilities["REAL"], FAKE=probabilities["FAKE"]),
        heatmap=image_data_url(heatmap, "PNG"),
        original=image_data_url_from_bytes(original_buffer),
        image_info=ImageInfo(
            filename=decoded.filename,
            width=decoded.image.width,
            height=decoded.image.height,
            size_kb=round(decoded.raw_size / 1024),
            format=decoded.image_format,
        ),
        model=ModelInfo(name=getattr(predictor, "arch", settings.model_arch)),
        processing_ms=elapsed_ms,
        created_at=created_at,
    )
    db: AnalysisDatabase = request.app.state.database
    db.add(analysis_id, result.verdict, result.confidence, decoded.filename, thumbnail, created_at)
    return result


def image_data_url_from_bytes(data: bytes) -> str:
    import base64

    return f"data:image/jpeg;base64,{base64.b64encode(data).decode('ascii')}"


@router.get("/history", response_model=HistoryResponse)
async def get_history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> HistoryResponse:
    db: AnalysisDatabase = request.app.state.database
    return HistoryResponse(items=[HistoryItem(**item) for item in db.list(limit)])


@router.delete("/history/{analysis_id}", status_code=204)
async def delete_history_item(request: Request, analysis_id: str) -> None:
    db: AnalysisDatabase = request.app.state.database
    if not db.delete(analysis_id):
        raise ApiException(404, "not_found", "This analysis is no longer in history.")


@router.delete("/history", status_code=204)
async def clear_history(request: Request) -> None:
    db: AnalysisDatabase = request.app.state.database
    db.clear()
