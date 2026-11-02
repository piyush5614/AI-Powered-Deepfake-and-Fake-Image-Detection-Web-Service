import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.formparsers import MultiPartParser
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.config import settings
from backend.app.db import AnalysisDatabase
from backend.app.errors import register_error_handlers
from backend.app.routes import limiter, router
from ml.gradcam import load_model


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
MAX_REQUEST_BYTES = settings.max_upload_mb * 1024 * 1024 + 64 * 1024
MultiPartParser.spool_max_size = MAX_REQUEST_BYTES


class UploadSizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/api/v1/analyze":
            await self.app(scope, receive, send)
            return

        content_length = next(
            (value for name, value in scope.get("headers", []) if name.lower() == b"content-length"),
            None,
        )
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError:
                await self._reject(send, status_code=400, code="invalid_request", message="Invalid request size header.")
                return
            if declared_length > MAX_REQUEST_BYTES:
                await self._reject(send)
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_REQUEST_BYTES:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            await self._reject(send)

    @staticmethod
    async def _reject(
        send: Send,
        status_code: int = 413,
        code: str = "file_too_large",
        message: str = "Request exceeds the configured image upload limit.",
    ) -> None:
        import json

        body = json.dumps({"error": {"code": code, "message": message}}).encode("utf-8")
        await send({"type": "http.response.start", "status": status_code, "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": body})


class RequestBodyTooLarge(Exception):
    pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database = AnalysisDatabase(settings.db_path)
    app.state.database.initialize()
    try:
        app.state.predictor = load_model(settings.model_path)
    except FileNotFoundError:
        logging.getLogger("truthlens").warning("Model checkpoint not found at %s; analysis is disabled.", settings.model_path)
        app.state.predictor = None
    yield


app = FastAPI(title="TruthLens API", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(UploadSizeLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)
register_error_handlers(app)
app.include_router(router)


@app.middleware("http")
async def security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Request-ID"] = request.state.request_id
    return response


static_dir = Path(__file__).resolve().parents[1] / "static"
if static_dir.is_dir():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "The requested resource was not found."}})
        index_file = static_dir / "index.html"
        requested_file = (static_dir / full_path).resolve()
        if requested_file.is_relative_to(static_dir.resolve()) and requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(index_file)

    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
