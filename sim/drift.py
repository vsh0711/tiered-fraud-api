"""Optional concept drift hook for simulator demos."""

from sim.generator import GeneratorConfig, generate_transactions


def generate_with_drift(n_samples: int = 5000, drift_strength: float = 0.35):
    return generate_transactions(
        GeneratorConfig(n_samples=n_samples, seed=101, drift_strength=drift_strength)
    )
