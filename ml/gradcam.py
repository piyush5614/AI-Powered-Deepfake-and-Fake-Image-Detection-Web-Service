from __future__ import annotations

import argparse
import threading
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any

from PIL import Image

if TYPE_CHECKING:
    import torch

CLASS_NAMES = ["REAL", "FAKE"]
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def create_model(arch: str, pretrained: bool = True) -> Any:
    from torchvision import models

    if arch == "mobilenet_v2":
        weights = models.MobileNet_V2_Weights.DEFAULT if pretrained else None
        model = models.mobilenet_v2(weights=weights)
        input_features = model.classifier[-1].in_features
        model.classifier = torch.nn.Sequential(
            torch.nn.Dropout(0.3),
            torch.nn.Linear(input_features, 2),
        )
        return model
    if arch == "resnet50":
        weights = models.ResNet50_Weights.DEFAULT if pretrained else None
        model = models.resnet50(weights=weights)
        input_features = model.fc.in_features
        model.fc = torch.nn.Sequential(torch.nn.Dropout(0.3), torch.nn.Linear(input_features, 2))
        return model
    raise ValueError(f"Unsupported model architecture: {arch}")


def target_layer(model: Any, arch: str) -> Any:
    if arch == "mobilenet_v2":
        return model.features[-1]  # type: ignore[attr-defined]
    if arch == "resnet50":
        return model.layer4[-1]  # type: ignore[attr-defined]
    raise ValueError(f"Unsupported model architecture: {arch}")


class Predictor:
    def __init__(self, model: Any, arch: str, device: Any) -> None:
        import torch
        from torchvision import transforms

        self.model = model.to(device).eval()
        self.arch = arch
        self.device = device
        self.torch = torch
        self.lock = threading.Lock()
        self.transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ]
        )
        self.target_layers = [target_layer(model, arch)]

    def predict(self, pil_image: Image.Image) -> dict[str, Any]:
        from pytorch_grad_cam import GradCAM
        from pytorch_grad_cam.utils.image import show_cam_on_image
        from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
        import numpy as np

        image = pil_image.convert("RGB").resize((224, 224), Image.Resampling.LANCZOS)
        tensor = self.transform(image).unsqueeze(0).to(self.device)
        with self.lock:
            with self.torch.no_grad():
                logits = self.model(tensor)
                probabilities = torch.softmax(logits, dim=1)[0].cpu().numpy()
                predicted_class = int(np.argmax(probabilities))
            with GradCAM(model=self.model, target_layers=self.target_layers) as cam:
                activation = cam(
                    input_tensor=tensor,
                    targets=[ClassifierOutputTarget(predicted_class)],
                )[0]
        rgb = np.asarray(image, dtype=np.float32) / 255.0
        overlay = show_cam_on_image(rgb, activation, use_rgb=True, image_weight=0.55)
        return {
            "label": CLASS_NAMES[predicted_class],
            "confidence": float(probabilities[predicted_class]),
            "probabilities": {
                CLASS_NAMES[index]: float(probabilities[index]) for index in range(len(CLASS_NAMES))
            },
            "heatmap": Image.fromarray(overlay, mode="RGB"),
        }


def load_model(checkpoint_path: str | Path) -> Predictor:
    path = Path(checkpoint_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("state_dict"), dict):
        raise ValueError(f"Checkpoint at {path} does not contain a state_dict.")
    arch = checkpoint.get("arch")
    if arch not in {"mobilenet_v2", "resnet50"}:
        raise ValueError(f"Checkpoint at {path} has an unsupported architecture.")
    if checkpoint.get("class_names") != CLASS_NAMES:
        raise ValueError(f"Checkpoint class mapping must be {CLASS_NAMES}.")
    model = create_model(arch, pretrained=False)
    model.load_state_dict(checkpoint["state_dict"])
    return Predictor(model, arch, device)


def save_example_heatmaps(checkpoint_path: Path, test_dir: Path, output_dir: Path) -> None:
    predictor = load_model(checkpoint_path)
    samples: dict[str, Path] = {}
    for path in sorted(test_dir.rglob("*")):
        if not path.is_file():
            continue
        class_name = next((name for name in CLASS_NAMES if name.casefold() in {part.casefold() for part in path.parts}), None)
        if class_name and path.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}:
            samples.setdefault(class_name, path)
    missing = [name for name in CLASS_NAMES if name not in samples]
    if missing:
        raise FileNotFoundError(f"Could not find sample images for {missing} under {test_dir}.")
    output_dir.mkdir(parents=True, exist_ok=True)
    for class_name, path in samples.items():
        with Image.open(path) as source:
            result = predictor.predict(source.convert("RGB"))
        result["heatmap"].save(output_dir / f"{class_name.lower()}_heatmap.png")
        print(f"{class_name}: model predicted {result['label']} ({result['confidence']:.3f}) -> {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Grad-CAM examples for one REAL and one FAKE test image.")
    parser.add_argument("--checkpoint", type=Path, default=Path("ml/artifacts/best.pt"))
    parser.add_argument("--test-dir", type=Path, default=Path("ml/data/cifake/test"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml/artifacts/samples"))
    options = parser.parse_args()
    try:
        save_example_heatmaps(options.checkpoint, options.test_dir, options.output_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
