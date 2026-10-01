"""Versioned reproducible presets and atomic artifact export."""
import json
import os
from pathlib import Path
import tempfile
from . import ENGINE_VERSION, SCHEMA_VERSION
from .config import SimulationConfig
from .pipeline import run_simulation

SCENARIOS = (
    ("baseline", "Baseline", "Typical acquisition, conversion and customer churn.", {}),
    ("acquisition", "Acquisition surge", "More signups with lower activation and payment conversion.", dict(daily_signups=65, activation_rate=0.5, payment_rate=0.25)),
    ("retention", "Stronger retention", "The same acquisition funnel with a lower daily customer churn hazard.", dict(churn_rate=0.005)),
    ("quality", "Data quality incident", "The baseline business stream with more duplicate and malformed records.", dict(duplicate_rate=0.18, invalid_rate=0.18)),
)


def build_catalog():
    return dict(schema_version=SCHEMA_VERSION, engine_version=ENGINE_VERSION,
                source=dict(repository="https://github.com/jckail/data_playground", command="python -m playground export --output artifacts/catalog.json"),
                runs=[run_simulation(SimulationConfig(**overrides), dict(id=key, name=name, description=description))
                      for key, name, description, overrides in SCENARIOS])


def write_json_atomic(payload, output):
    """Replace only after a complete, fsynced JSON file exists on the same volume."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        # Catalogs contain public synthetic data and must be readable by image users.
        os.chmod(temp_name, 0o644)
        os.replace(temp_name, output)
    finally:
        if temp_name is not None and os.path.exists(temp_name):
            os.unlink(temp_name)
