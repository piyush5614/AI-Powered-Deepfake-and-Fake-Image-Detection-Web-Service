# Dataset setup

Training requires a locally downloaded dataset. Images are never committed.

## CIFAKE (default)

Install/configure Kaggle credentials, then from the repository root run:

```powershell
kaggle datasets download -d birdy654/cifake-real-and-ai-generated-synthetic-images --unzip -p ml/data/cifake
```

Manual download: https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images

## 140k real and fake faces

```powershell
kaggle datasets download -d xhlulu/140k-real-and-fake-faces --unzip -p ml/data/faces140k
```

Manual download: https://www.kaggle.com/datasets/xhlulu/140k-real-and-fake-faces

The loader searches case-insensitively for `real` and `fake` class directories inside training and test folders.
