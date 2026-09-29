#!/usr/bin/env python3
"""Train T1/T2 models and persist to data/models/."""

from pathlib import Path

from ml.train import train_and_persist


def main() -> None:
    metrics = train_and_persist(Path("data/models"), n_samples=45_000)
    print("Training complete:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
