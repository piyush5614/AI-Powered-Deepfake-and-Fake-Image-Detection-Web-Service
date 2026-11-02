import io
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app import main
from backend.app.config import settings
from backend.app.routes import limiter


class FakePredictor:
    def predict(self, image: Image.Image) -> dict:
        return {
            "label": "REAL",
            "confidence": 0.8,
            "probabilities": {"REAL": 0.8, "FAKE": 0.2},
            "heatmap": image.resize((224, 224)),
        }


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"))
    limiter.reset()
    with TestClient(main.app) as test_client:
        main.app.state.predictor = FakePredictor()
        yield test_client
    limiter.reset()


def jpeg_bytes(size: tuple[int, int] = (96, 80)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (50, 120, 200)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_health_contract(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model_loaded": True,
        "model_name": settings.model_arch,
        "version": "1.0.0",
    }


def test_missing_model_reports_not_loaded(client):
    main.app.state.predictor = None
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["model_loaded"] is False
    response = client.post("/api/v1/analyze", files={"file": ("sample.jpg", jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_not_loaded"


def test_valid_upload_response_contract(client):
    response = client.post("/api/v1/analyze", files={"file": ("sample.jpg", jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "id", "verdict", "confidence", "probabilities", "heatmap", "original",
        "image_info", "model", "processing_ms", "created_at",
    }
    uuid.UUID(body["id"])
    assert body["verdict"] in {"REAL", "FAKE"}
    assert isinstance(body["confidence"], float)
    assert set(body["probabilities"]) == {"REAL", "FAKE"}
    assert abs(sum(body["probabilities"].values()) - 1) < 0.001
    assert body["heatmap"].startswith("data:image/png;base64,")
    assert body["original"].startswith("data:image/jpeg;base64,")
    assert set(body["image_info"]) == {"filename", "width", "height", "size_kb", "format"}
    assert set(body["model"]) == {"name", "input_size"}
    assert isinstance(body["image_info"]["filename"], str)
    assert isinstance(body["image_info"]["width"], int)
    assert isinstance(body["image_info"]["height"], int)
    assert isinstance(body["image_info"]["size_kb"], int)
    assert isinstance(body["image_info"]["format"], str)
    assert isinstance(body["model"]["name"], str)
    assert isinstance(body["model"]["input_size"], int)
    assert isinstance(body["processing_ms"], int)
    assert isinstance(body["created_at"], str)


def test_missing_file_uses_api_error_shape(client):
    response = client.post("/api/v1/analyze")
    assert response.status_code == 400
    assert response.json() == {"error": {"code": "no_file", "message": "Choose an image to analyze."}}


def test_wrong_file_type_is_rejected(client):
    response = client.post("/api/v1/analyze", files={"file": ("photo.jpg", b"not an image", "image/jpeg")})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_file_type"


def test_oversized_upload_is_rejected(client):
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("large.jpg", b"x" * (6 * 1024 * 1024), "image/jpeg")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_corrupt_image_is_rejected(client):
    response = client.post("/api/v1/analyze", files={"file": ("broken.jpg", b"\xff\xd8\xffbroken", "image/jpeg")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "corrupt_image"


def test_rate_limit_returns_consistent_error(client):
    responses = [
        client.post("/api/v1/analyze", files={"file": ("sample.jpg", jpeg_bytes(), "image/jpeg")})
        for _ in range(11)
    ]
    assert responses[-1].status_code == 429
    assert responses[-1].json()["error"]["code"] == "rate_limited"
    assert responses[-1].headers.get("retry-after")


def test_history_delete(client):
    analysis = client.post("/api/v1/analyze", files={"file": ("sample.jpg", jpeg_bytes(), "image/jpeg")})
    analysis_id = analysis.json()["id"]
    history = client.get("/api/v1/history")
    assert history.status_code == 200
    assert history.json()["items"][0]["id"] == analysis_id
    deleted = client.delete(f"/api/v1/history/{analysis_id}")
    assert deleted.status_code == 204
    assert client.get("/api/v1/history").json()["items"] == []
