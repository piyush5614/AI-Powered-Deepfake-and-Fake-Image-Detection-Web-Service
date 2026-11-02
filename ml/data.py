from __future__ import annotations

import random
from pathlib import Path
from typing import Callable

import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision import transforms

from ml.gradcam import CLASS_NAMES


DATASET_IDS = {
    "cifake": (
        "birdy654/cifake-real-and-ai-generated-synthetic-images",
        "https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images",
    ),
    "faces140k": ("xhlulu/140k-real-and-fake-faces", "https://www.kaggle.com/datasets/xhlulu/140k-real-and-fake-faces"),
}
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def image_transforms(training: bool) -> transforms.Compose:
    steps: list[Callable] = [transforms.Resize((224, 224))]
    if training:
        steps.extend(
            [
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(10),
                transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1, hue=0.1),
            ]
        )
    steps.extend([transforms.ToTensor(), transforms.Normalize(MEAN, STD)])
    return transforms.Compose(steps)


class ImageFolderByClass(Dataset[tuple[torch.Tensor, int]]):
    def __init__(self, root: Path, transform: transforms.Compose) -> None:
        self.root = root
        self.transform = transform
        class_dirs = {path.name.casefold(): path for path in root.rglob("*") if path.is_dir() and path.name.casefold() in {"real", "fake"}}
        self.samples: list[tuple[Path, int]] = []
        for class_name, label in (("real", 0), ("fake", 1)):
            class_dir = class_dirs.get(class_name)
            if class_dir is None:
                continue
            for path in sorted(class_dir.rglob("*")):
                if path.is_file() and path.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                    self.samples.append((path, label))
        present_labels = {label for _, label in self.samples}
        if present_labels != {0, 1}:
            missing = [CLASS_NAMES[label] for label in (0, 1) if label not in present_labels]
            raise FileNotFoundError(f"Missing image files for class(es) {', '.join(missing)} under {root}.")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        path, label = self.samples[index]
        with Image.open(path) as source:
            image = source.convert("RGB")
        return self.transform(image), label


def find_split(root: Path, names: set[str]) -> Path | None:
    for path in sorted(root.rglob("*")):
        if path.is_dir() and path.name.casefold() in names:
            class_names = {child.name.casefold() for child in path.iterdir() if child.is_dir()}
            if class_names.intersection({"real", "fake"}):
                return path
    return None


def resolve_dataset(root: Path, dataset_name: str) -> tuple[Path, Path | None]:
    dataset_root = root / "ml" / "data" / dataset_name
    if not dataset_root.exists():
        dataset_id, url = DATASET_IDS[dataset_name]
        raise FileNotFoundError(
            f"Dataset '{dataset_name}' is missing. Download it to {dataset_root}.\n"
            f"With Kaggle credentials: kaggle datasets download -d {dataset_id} --unzip -p {dataset_root}\n"
            f"Manual download: {url}"
        )
    train_dir = find_split(dataset_root, {"train", "training"}) or find_split(dataset_root, {"real", "fake"})
    test_dir = find_split(dataset_root, {"test", "testing", "valid", "validation"})
    if train_dir is None:
        dataset_id, url = DATASET_IDS[dataset_name]
        raise FileNotFoundError(f"No training REAL/FAKE folders found in {dataset_root}. See {url}")
    return train_dir, test_dir


def _selected_indices(dataset: ImageFolderByClass, max_samples: int | None, seed: int) -> list[int]:
    if max_samples is None or max_samples >= len(dataset):
        indexes = list(range(len(dataset)))
    else:
        generator = random.Random(seed)
        by_label = {label: [i for i, (_, sample_label) in enumerate(dataset.samples) if sample_label == label] for label in (0, 1)}
        per_class = max(1, max_samples // 2)
        indexes = [i for label in (0, 1) for i in generator.sample(by_label[label], min(per_class, len(by_label[label])))]
        indexes = sorted(indexes[:max_samples])
    return indexes


def create_datasets(
    dataset_name: str = "cifake",
    max_samples: int | None = None,
    seed: int = 42,
    root: Path | None = None,
) -> tuple[Dataset, Dataset, Dataset]:
    repo_root = root or Path(__file__).resolve().parents[1]
    train_dir, test_dir = resolve_dataset(repo_root, dataset_name)
    training = ImageFolderByClass(train_dir, image_transforms(True))
    validation = ImageFolderByClass(train_dir, image_transforms(False))
    indexes = _selected_indices(training, max_samples, seed)
    generator = torch.Generator().manual_seed(seed)
    permutation = torch.randperm(len(indexes), generator=generator).tolist()
    shuffled_indexes = [indexes[index] for index in permutation]
    dedicated_test = test_dir is not None
    test_indexes: list[int] = []
    if not dedicated_test:
        test_size = max(1, round(len(shuffled_indexes) * 0.1))
        if len(shuffled_indexes) - test_size < 2:
            raise ValueError("At least three images are required when no dedicated test folder exists.")
        test_indexes = shuffled_indexes[-test_size:]
        shuffled_indexes = shuffled_indexes[:-test_size]
    validation_size = max(1, round(len(shuffled_indexes) * 0.2))
    train_size = len(shuffled_indexes) - validation_size
    if train_size < 1:
        raise ValueError("At least two images are required to create a training and validation split.")
    train_set = Subset(training, shuffled_indexes[:train_size])
    validation_set = Subset(validation, shuffled_indexes[train_size:])
    if test_dir is not None:
        test_set: Dataset = ImageFolderByClass(test_dir, image_transforms(False))
        if isinstance(test_set, ImageFolderByClass) and max_samples is not None and max_samples < len(test_set):
            test_set = Subset(test_set, _selected_indices(test_set, max_samples, seed))
    else:
        test_set = Subset(validation, test_indexes)
    return train_set, validation_set, test_set


def create_loaders(
    dataset_name: str = "cifake",
    max_samples: int | None = None,
    batch_size: int = 32,
    seed: int = 42,
    root: Path | None = None,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    datasets = create_datasets(dataset_name, max_samples, seed, root)
    loaders = [
        DataLoader(dataset, batch_size=batch_size, shuffle=index == 0, num_workers=0, pin_memory=torch.cuda.is_available())
        for index, dataset in enumerate(datasets)
    ]
    return loaders[0], loaders[1], loaders[2]
