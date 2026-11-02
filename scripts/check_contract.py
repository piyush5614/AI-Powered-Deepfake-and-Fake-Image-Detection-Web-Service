from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx


def check(base_url: str, image_path: Path) -> None:
    if not image_path.is_file():
        raise FileNotFoundError(f"Sample image does not exist: {image_path}")
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=30) as client:
        health = client.get("/api/v1/health")
        health.raise_for_status()
        health_body = health.json()
        assert isinstance(health_body.get("status"), str)
        assert isinstance(health_body.get("model_loaded"), bool)
        assert isinstance(health_body.get("model_name"), str)
        assert isinstance(health_body.get("version"), str)
        if not health_body["model_loaded"]:
            raise RuntimeError("The API is healthy but no trained checkpoint is loaded; analysis contract cannot be checked.")

        with image_path.open("rb") as image_file:
            response = client.post(
                "/api/v1/analyze",
                files={"file": (image_path.name, image_file, "application/octet-stream")},
            )
        response.raise_for_status()
        body = response.json()
        expected = {
            "id": str,
            "verdict": str,
            "confidence": (int, float),
            "probabilities": dict,
            "heatmap": str,
            "original": str,
            "image_info": dict,
            "model": dict,
            "processing_ms": int,
            "created_at": str,
        }
        for name, kind in expected.items():
            assert isinstance(body.get(name), kind), f"Invalid or missing response field: {name}"
        assert body["verdict"] in {"REAL", "FAKE"}
        assert set(body["probabilities"]) == {"REAL", "FAKE"}
        assert abs(sum(body["probabilities"].values()) - 1) < 0.001
        assert body["heatmap"].startswith("data:image/png;base64,")
        assert body["original"].startswith("data:image/jpeg;base64,")
        assert set(body["image_info"]) == {"filename", "width", "height", "size_kb", "format"}
        assert set(body["model"]) == {"name", "input_size"}
    print("TruthLens API response contract passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the deployed TruthLens API response contract.")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--image", type=Path, required=True, help="Local JPEG, PNG or WebP sample image")
    args = parser.parse_args()
    try:
        check(args.url, args.image)
    except (httpx.HTTPError, AssertionError, FileNotFoundError, RuntimeError) as exc:
        print(f"Contract check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
