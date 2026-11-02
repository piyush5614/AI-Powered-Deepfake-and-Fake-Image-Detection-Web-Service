from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from ml.data import create_loaders
from ml.gradcam import CLASS_NAMES, create_model


ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def labels_for(dataset: Dataset) -> list[int]:
    if hasattr(dataset, "samples"):
        return [label for _, label in dataset.samples]  # type: ignore[attr-defined]
    if hasattr(dataset, "dataset") and hasattr(dataset, "indices"):
        parent = labels_for(dataset.dataset)  # type: ignore[attr-defined]
        return [parent[index] for index in dataset.indices]  # type: ignore[attr-defined]
    return []


def _set_trainable_layers(model: nn.Module, arch: str, phase: str) -> None:
    for parameter in model.parameters():
        parameter.requires_grad = phase == "head"
    if phase == "fine_tune":
        blocks = model.features if arch == "mobilenet_v2" else model.layer4  # type: ignore[attr-defined]
        for parameter in blocks[-1].parameters():
            parameter.requires_grad = True
        head = model.classifier if arch == "mobilenet_v2" else model.fc  # type: ignore[attr-defined]
        for parameter in head.parameters():
            parameter.requires_grad = True


def _run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: Adam | None,
    description: str,
) -> tuple[float, float]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    correct = 0
    count = 0
    for images, labels in tqdm(loader, desc=description, leave=False):
        images = images.to(device)
        labels = labels.to(device)
        if optimizer:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(training):
            output = model(images)
            loss = criterion(output, labels)
            if optimizer:
                loss.backward()
                optimizer.step()
        total_loss += float(loss.item()) * len(labels)
        correct += int((output.argmax(dim=1) == labels).sum().item())
        count += len(labels)
    if not count:
        raise ValueError("The data loader contains no images.")
    return total_loss / count, correct / count


def train(args: argparse.Namespace) -> Path | None:
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    try:
        train_loader, validation_loader, _ = create_loaders(
            dataset_name=args.dataset,
            max_samples=args.max_samples,
            batch_size=args.batch_size,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return None
    train_labels = labels_for(train_loader.dataset)
    validation_labels = labels_for(validation_loader.dataset)
    print(
        "Class counts: "
        + json.dumps(
            {
                "train": {name: train_labels.count(index) for index, name in enumerate(CLASS_NAMES)},
                "validation": {name: validation_labels.count(index) for index, name in enumerate(CLASS_NAMES)},
            }
        )
    )
    first_images, _ = next(iter(train_loader))
    print(f"Batch shape: {list(first_images.shape)}")
    if args.dry_run:
        return Path()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = create_model(args.arch, pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss()
    scheduler: ReduceLROnPlateau | None = None
    optimizer: Adam | None = None
    current_phase: str | None = None
    best_accuracy = -1.0
    best_path = ARTIFACTS / f"{args.arch}.pt"
    history: list[dict[str, float | int | str]] = []
    stale_epochs = 0
    for epoch in range(args.epochs):
        phase = "head" if epoch < min(2, args.epochs) else "fine_tune"
        _set_trainable_layers(model, args.arch, phase)
        learning_rate = 1e-3 if phase == "head" else 1e-4
        if optimizer is None or phase != current_phase:
            optimizer = Adam((p for p in model.parameters() if p.requires_grad), lr=learning_rate)
            scheduler = ReduceLROnPlateau(optimizer, mode="min", patience=1)
            current_phase = phase
        train_loss, train_accuracy = _run_epoch(model, train_loader, criterion, device, optimizer, f"train {epoch + 1}")
        val_loss, val_accuracy = _run_epoch(model, validation_loader, criterion, device, None, f"valid {epoch + 1}")
        scheduler.step(val_loss)
        history.append(
            {
                "epoch": epoch + 1,
                "phase": phase,
                "train_loss": train_loss,
                "train_acc": train_accuracy,
                "val_loss": val_loss,
                "val_acc": val_accuracy,
            }
        )
        print(
            f"Epoch {epoch + 1}/{args.epochs} [{phase}] "
            f"train_loss={train_loss:.4f} train_acc={train_accuracy:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_accuracy:.4f}"
        )
        if val_accuracy > best_accuracy:
            best_accuracy = val_accuracy
            ARTIFACTS.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "arch": args.arch,
                    "class_names": CLASS_NAMES,
                    "val_acc": val_accuracy,
                    "history": history,
                },
                best_path,
            )
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= 3:
                print("Early stopping: validation accuracy has not improved for three epochs.")
                break

    with (ARTIFACTS / f"training_{args.arch}.json").open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2)
    return best_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune a TruthLens image classifier.")
    parser.add_argument("--arch", choices=("mobilenet_v2", "resnet50"), default="mobilenet_v2")
    parser.add_argument("--dataset", choices=("cifake", "faces140k"), default="cifake")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    if train(parse_args()) is None:
        raise SystemExit(2)
