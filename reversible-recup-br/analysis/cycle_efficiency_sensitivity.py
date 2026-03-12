#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_solver_module() -> ModuleType:
    solver_path = Path(__file__).resolve().parents[1] / "reversible-recup-brayton.py"
    spec = importlib.util.spec_from_file_location("reversible_recup_brayton", solver_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load solver module from {solver_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sweep_values(minimum: float, maximum: float, step: float) -> list[float]:
    if step <= 0.0:
        raise ValueError("Sweep step must be > 0")
    if maximum < minimum:
        raise ValueError("Sweep maximum must be >= minimum")

    values: list[float] = []
    current = minimum
    epsilon = step * 1e-6
    while current <= maximum + epsilon:
        values.append(round(current, 10))
        current += step
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sensitivity sweep for reversible recuperated Brayton cycle using "
            "turbomachine isentropic efficiencies"
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "config.json",
        help="Path to cycle configuration JSON file",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["charge", "discharge"],
        default=None,
        help="Optional mode override for the sweep",
    )

    parser.add_argument("--eta-a-min", type=float, default=0.70)
    parser.add_argument("--eta-a-max", type=float, default=1.00)
    parser.add_argument("--eta-a-step", type=float, default=0.05)

    parser.add_argument("--eta-b-min", type=float, default=0.70)
    parser.add_argument("--eta-b-max", type=float, default=1.00)
    parser.add_argument("--eta-b-step", type=float, default=0.05)

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "cycle_efficiency_sensitivity.csv",
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    module = _load_solver_module()

    load_config = module.load_config
    build_cycle = module.build_cycle

    base_config = load_config(args.config, args.mode)
    base_config.setdefault("turbomachine_A", {})
    base_config.setdefault("turbomachine_B", {})

    eta_a_values = _sweep_values(args.eta_a_min, args.eta_a_max, args.eta_a_step)
    eta_b_values = _sweep_values(args.eta_b_min, args.eta_b_max, args.eta_b_step)

    rows: list[dict[str, object]] = []

    for eta_a in eta_a_values:
        for eta_b in eta_b_values:
            run_config = copy.deepcopy(base_config)
            run_config["turbomachine_A"]["eta_isentropic"] = eta_a
            run_config["turbomachine_B"]["eta_isentropic"] = eta_b

            row: dict[str, object] = {
                "mode": run_config.get("mode", "charge"),
                "eta_a": eta_a,
                "eta_b": eta_b,
                "status": "ok",
                "error": "",
                "net_work_W": "",
                "Q_hot_W": "",
                "Q_cold_W": "",
                "COP_or_eta": "",
                "exergetic_efficiency": "",
                "cycle_isentropic_efficiency": "",
                "total_exergy_destruction_W": "",
            }

            try:
                result = build_cycle(run_config)
                row.update(
                    {
                        "net_work_W": result.net_work,
                        "Q_hot_W": result.Q_hot,
                        "Q_cold_W": result.Q_cold,
                        "COP_or_eta": result.COP_or_eta,
                        "exergetic_efficiency": result.exergetic_efficiency,
                        "cycle_isentropic_efficiency": result.cycle_isentropic_efficiency,
                        "total_exergy_destruction_W": result.total_exergy_destruction,
                    }
                )
            except (RuntimeError, ValueError) as exc:
                row["status"] = "error"
                row["error"] = str(exc)

            rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "mode",
        "eta_a",
        "eta_b",
        "status",
        "error",
        "net_work_W",
        "Q_hot_W",
        "Q_cold_W",
        "COP_or_eta",
        "exergetic_efficiency",
        "cycle_isentropic_efficiency",
        "total_exergy_destruction_W",
    ]

    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    success_rows = [row for row in rows if row["status"] == "ok"]
    print(f"Wrote {len(rows)} sweep cases to {args.output}")
    if not success_rows:
        print("No successful cases to summarize.")
        return

    best_row = max(
        success_rows,
        key=lambda item: float(item["exergetic_efficiency"]),
    )
    print("Best case by exergetic_efficiency")
    print(
        f"  eta_a={best_row['eta_a']:.3f}, eta_b={best_row['eta_b']:.3f}, "
        f"ex_eff={float(best_row['exergetic_efficiency']):.6f}, "
        f"cycle_eta_is={float(best_row['cycle_isentropic_efficiency']):.6f}"
    )


if __name__ == "__main__":
    main()