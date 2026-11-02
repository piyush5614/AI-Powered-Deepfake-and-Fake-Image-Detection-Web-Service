from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from torch.utils.data import DataLoader

from ml.data import create_datasets
from ml.gradcam import CLASS_NAMES, create_model


ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def evaluate_arch(arch: str, dataset: str, max_samples: int | None) -> dict:
    checkpoint_path = ARTIFACTS / f"{arch}.pt"
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}. Train {arch} first.")
    _, _, test_set = create_datasets(dataset_name=dataset, max_samples=max_samples)
    loader = DataLoader(test_set, batch_size=32, shuffle=False, num_workers=0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if checkpoint.get("class_names") != CLASS_NAMES or checkpoint.get("arch") != arch:
        raise ValueError(f"Checkpoint metadata does not match {arch} and {CLASS_NAMES}.")
    model = create_model(arch, pretrained=False).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    expected: list[int] = []
    predicted: list[int] = []
    timings: list[float] = []
    for images, labels in loader:
        images = images.to(device)
        if device.type == "cuda":
            torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.no_grad():
            output = model(images)
        if device.type == "cuda":
            torch.cuda.synchronize()
        timings.append((time.perf_counter() - started) / len(labels))
        expected.extend(labels.tolist())
        predicted.extend(output.argmax(dim=1).cpu().tolist())
    precision, recall, f1, support = precision_recall_fscore_support(
        expected, predicted, labels=[0, 1], zero_division=0
    )
    matrix = confusion_matrix(expected, predicted, labels=[0, 1])
    result = {
        "accuracy": float(accuracy_score(expected, predicted)),
        "precision": {"macro": float(precision.mean()), **{name: float(precision[i]) for i, name in enumerate(CLASS_NAMES)}},
        "recall": {"macro": float(recall.mean()), **{name: float(recall[i]) for i, name in enumerate(CLASS_NAMES)}},
        "f1": {"macro": float(f1.mean()), **{name: float(f1[i]) for i, name in enumerate(CLASS_NAMES)}},
        "support": {name: int(support[i]) for i, name in enumerate(CLASS_NAMES)},
        "confusion_matrix": matrix.tolist(),
        "params": sum(parameter.numel() for parameter in model.parameters()),
        "ms_per_image": float(np.mean(timings) * 1000),
    }
    _save_plots(arch, matrix, checkpoint.get("history", []))
    return result


def _save_plots(arch: str, matrix: np.ndarray, history: list[dict]) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(4, 4))
    axis.imshow(matrix, cmap="Blues")
    axis.set_xticks(range(2), CLASS_NAMES)
    axis.set_yticks(range(2), CLASS_NAMES)
    axis.set_xlabel("Predicted")
    axis.set_ylabel("Actual")
    for row in range(2):
        for column in range(2):
            axis.text(column, row, str(matrix[row, column]), ha="center", va="center")
    figure.tight_layout()
    figure.savefig(ARTIFACTS / f"confusion_matrix_{arch}.png", dpi=150)
    plt.close(figure)
    if not history:
        history_path = ARTIFACTS / f"training_{arch}.json"
        if history_path.exists():
            history = json.loads(history_path.read_text(encoding="utf-8"))
    if history:
        figure, axis = plt.subplots(figsize=(6, 4))
        axis.plot([row["epoch"] for row in history], [row["train_loss"] for row in history], label="Train")
        axis.plot([row["epoch"] for row in history], [row["val_loss"] for row in history], label="Validation")
        axis.set_xlabel("Epoch")
        axis.set_ylabel("Loss")
        axis.legend()
        figure.tight_layout()
        figure.savefig(ARTIFACTS / f"training_curves_{arch}.png", dpi=150)
        plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=("cifake", "faces140k"), default="cifake")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--arch", choices=("mobilenet_v2", "resnet50"))
    parser.add_argument("--max-samples", type=int)
    args = parser.parse_args()
    architectures = ["mobilenet_v2", "resnet50"] if args.compare else [args.arch or "mobilenet_v2"]
    results = {arch: evaluate_arch(arch, args.dataset, args.max_samples) for arch in architectures}
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    metrics_path = ARTIFACTS / "metrics.json"
    current: dict = {}
    if metrics_path.exists():
        current = json.loads(metrics_path.read_text(encoding="utf-8"))
    current.update(results)
    metrics_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    ranked = sorted(results.items(), key=lambda item: (item[1]["f1"]["macro"], item[1]["accuracy"]), reverse=True)
    winner = ranked[0][0]
    shutil.copyfile(ARTIFACTS / f"{winner}.pt", ARTIFACTS / "best.pt")
    rows = ["| Architecture | Params | Accuracy | Macro F1 | ms / image |", "|---|---:|---:|---:|---:|"]
    for arch, data in ranked:
        rows.append(f"| {arch} | {data['params']:,} | {data['accuracy']:.4f} | {data['f1']['macro']:.4f} | {data['ms_per_image']:.2f} |")
    (ARTIFACTS / "comparison.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    frontend_metrics = Path(__file__).resolve().parents[1] / "frontend" / "src" / "data" / "metrics.json"
    frontend_metrics.parent.mkdir(parents=True, exist_ok=True)
    frontend_metrics.write_text(
        json.dumps({"models": current, "best_model": winner}, indent=2),
        encoding="utf-8",
    )
    print(f"Best model: {winner}")


if __name__ == "__main__":
    main()
