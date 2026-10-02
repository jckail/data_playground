"""Run with python -m playground; no services or credentials required."""
import argparse
import json
from .catalog import build_catalog, write_json_atomic
from .config import SimulationConfig
from .pipeline import run_simulation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="Export the four reproducible synthetic scenarios")
    export.add_argument("--output", default="artifacts/catalog.json")
    simulate = commands.add_parser("simulate", help="Run a custom bounded synthetic simulation")
    simulate.add_argument("--output")
    for name, value in SimulationConfig().to_dict().items():
        simulate.add_argument("--" + name.replace("_", "-"), type=int if type(value) is int else float, default=value)
    args = vars(parser.parse_args())
    command, output = args.pop("command"), args.pop("output")
    try:
        payload = build_catalog() if command == "export" else run_simulation(SimulationConfig(**args))
        if output:
            write_json_atomic(payload, output)
            print(f"Exported synthetic data to {output}")
        else:
            print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
