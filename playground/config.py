"""Strict, bounded simulation inputs with no external dependencies."""
from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 42
    days: int = 30
    daily_signups: int = 30
    activation_rate: float = 0.65
    payment_rate: float = 0.35
    churn_rate: float = 0.02
    duplicate_rate: float = 0.03
    invalid_rate: float = 0.02

    def __post_init__(self):
        for name, low, high in (("seed", 0, 2147483647), ("days", 7, 90), ("daily_signups", 5, 100)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        for name in ("activation_rate", "payment_rate", "churn_rate", "duplicate_rate", "invalid_rate"):
            value = getattr(self, name)
            upper = 1 if name in ("activation_rate", "payment_rate") else 0.2
            if type(value) not in (int, float) or not 0 <= value <= upper or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number in [0, {upper}]")
            object.__setattr__(self, name, float(value))

    def to_dict(self):
        return asdict(self)
