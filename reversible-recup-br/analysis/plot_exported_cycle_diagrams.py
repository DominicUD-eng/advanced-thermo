#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_solver_module() -> ModuleType:
    solver_path = Path(__file__).resolve().parents[1] / "reversible-recup-brayton.py"
    spec = importlib.util.spec_from_file_location("reversible_recup_brayton", solver_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load solver module from {solver_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _normalize_metadata_filename(metadata_name: str) -> str:
    cleaned = metadata_name.strip()
    if not cleaned:
        cleaned = "plot_metadata"
    if not cleaned.lower().endswith(".parquet"):
        cleaned = f"{cleaned}.parquet"
    return cleaned


def _collect_parquet_paths(export_root: Path, table: str | None, metadata_filename: str) -> list[Path]:
    root = export_root / table if table else export_root
    if not root.exists():
        return []

    return sorted(path for path in root.rglob(metadata_filename) if path.is_file())


def _read_single_row_parquet(path: Path) -> dict[str, Any]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError(
            "Plotting exported parquet rows requires 'pyarrow'. Install with: pip install pyarrow"
        ) from exc

    rows = pq.read_table(path).to_pylist()
    if not rows:
        raise ValueError(f"No rows found in parquet: {path}")
    if len(rows) > 1:
        print(f"[warn] Expected one row per parquet, found {len(rows)} in {path}; using first row")

    row = rows[0]
    if not isinstance(row, dict):
        raise ValueError(f"Unexpected parquet row type in {path}: {type(row).__name__}")
    return row


def _parse_config_from_row(row: dict[str, Any], parquet_path: Path) -> dict[str, Any]:
    raw_config = row.get("input_config_json")
    if not isinstance(raw_config, str) or not raw_config.strip():
        raise ValueError(f"Missing 'input_config_json' in {parquet_path}")

    try:
        config = json.loads(raw_config)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in 'input_config_json' for {parquet_path}: {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError(f"'input_config_json' is not a JSON object in {parquet_path}")
    return config


def _is_status_ok(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() == "ok"


def _is_close(a: float, b: float, tolerance: float) -> bool:
    if not math.isfinite(a) or not math.isfinite(b):
        return False
    return abs(a - b) <= tolerance * max(1.0, abs(b))


def _warn_drift(row: dict[str, Any], mode: str, result: Any, tolerance: float, parquet_path: Path) -> None:
    checks: list[tuple[str, float]] = [
        (f"{mode}_net_work_w", float(getattr(result, "net_work"))),
        (f"{mode}_q_hot_w", float(getattr(result, "Q_hot"))),
        (f"{mode}_q_cold_w", float(getattr(result, "Q_cold"))),
        (f"{mode}_cop_or_eta", float(getattr(result, "COP_or_eta"))),
        (f"{mode}_exergetic_efficiency", float(getattr(result, "exergetic_efficiency"))),
        (
            f"{mode}_cycle_isentropic_efficiency",
            float(getattr(result, "cycle_isentropic_efficiency")),
        ),
        (
            f"{mode}_isentropic_reference_net_work_w",
            float(getattr(result, "isentropic_reference_net_work")),
        ),
    ]

    drift_messages: list[str] = []
    for key, computed_value in checks:
        raw = row.get(key)
        if raw is None:
            continue
        try:
            stored_value = float(raw)
        except (TypeError, ValueError):
            continue

        if not _is_close(computed_value, stored_value, tolerance):
            drift_messages.append(
                f"{key}: stored={stored_value:.6g}, recomputed={computed_value:.6g}"
            )

    if drift_messages:
        print(f"[warn] metric drift for {mode} in {parquet_path}")
        for message in drift_messages:
            print(f"       - {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot charge/discharge cycle diagrams from exported parquet metadata rows. "
            "Each parquet row is recomputed from input_config_json and plotted into the row folder."
        )
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=Path(__file__).resolve().parent / "metadata",
        help="Root metadata export folder containing table/row parquet files",
    )
    parser.add_argument(
        "--table",
        type=str,
        default=None,
        help="Optional table folder under export-root to limit processing",
    )
    parser.add_argument(
        "--metadata-name",
        type=str,
        default="plot_metadata",
        help="Parquet metadata base filename (with or without .parquet)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate plots even if target files already exist",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of parquet rows to process",
    )
    parser.add_argument(
        "--no-vapor-dome",
        action="store_true",
        help="Disable vapor-dome overlay in generated plots",
    )
    parser.add_argument(
        "--skip-drift-check",
        action="store_true",
        help="Disable stored-vs-recomputed metric drift warnings",
    )
    parser.add_argument(
        "--drift-tolerance",
        type=float,
        default=1.0e-6,
        help="Relative tolerance for drift warnings",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    metadata_filename = _normalize_metadata_filename(args.metadata_name)
    parquet_paths = _collect_parquet_paths(args.export_root, args.table, metadata_filename)

    if args.limit is not None:
        parquet_paths = parquet_paths[: max(0, args.limit)]

    if not parquet_paths:
        root_display = args.export_root / args.table if args.table else args.export_root
        print(f"No parquet metadata files named '{metadata_filename}' found under {root_display}")
        return

    solver_module = _load_solver_module()
    build_cycle = solver_module.build_cycle
    plotter_class = solver_module.BraytonCyclePlotter

    total_rows = len(parquet_paths)
    plotted_rows = 0
    skipped_existing_rows = 0
    skipped_status_rows = 0
    failed_rows = 0
    plotted_files = 0

    for index, parquet_path in enumerate(parquet_paths, start=1):
        row_dir = parquet_path.parent
        try:
            row = _read_single_row_parquet(parquet_path)

            row_status = row.get("status")
            if row_status is not None and not _is_status_ok(row_status):
                skipped_status_rows += 1
                print(f"[{index}/{total_rows}] skip status!=ok -> {parquet_path}")
                continue

            charge_file = row_dir / "charge_co2_cycle_diagrams.png"
            discharge_file = row_dir / "discharge_co2_cycle_diagrams.png"
            if not args.overwrite and charge_file.exists() and discharge_file.exists():
                skipped_existing_rows += 1
                print(f"[{index}/{total_rows}] skip existing plots -> {parquet_path}")
                continue

            base_config = _parse_config_from_row(row, parquet_path)
            plotter = plotter_class(
                output_dir=row_dir,
                include_vapor_dome=not args.no_vapor_dome,
            )

            plotted_for_row = 0
            for mode_name in ["charge", "discharge"]:
                mode_status = row.get(f"{mode_name}_status")
                if mode_status is not None and not _is_status_ok(mode_status):
                    continue

                mode_config = copy.deepcopy(base_config)
                mode_config["mode"] = mode_name
                mode_result = build_cycle(mode_config)
                plotter.save_cycle_diagrams(mode_result)
                plotted_for_row += 1

                if not args.skip_drift_check:
                    _warn_drift(
                        row,
                        mode_name,
                        mode_result,
                        tolerance=max(args.drift_tolerance, 0.0),
                        parquet_path=parquet_path,
                    )

            if plotted_for_row == 0:
                skipped_status_rows += 1
                print(f"[{index}/{total_rows}] skip no ok modes -> {parquet_path}")
                continue

            plotted_rows += 1
            plotted_files += plotted_for_row
            print(f"[{index}/{total_rows}] plotted {plotted_for_row} mode(s) -> {row_dir}")

        except (RuntimeError, ValueError, OSError, TypeError, ImportError) as exc:
            failed_rows += 1
            print(f"[{index}/{total_rows}] failed -> {parquet_path}: {exc}")

    print("\nPlot export summary")
    print(f"rows discovered: {total_rows}")
    print(f"rows plotted: {plotted_rows}")
    print(f"rows skipped (status): {skipped_status_rows}")
    print(f"rows skipped (existing): {skipped_existing_rows}")
    print(f"rows failed: {failed_rows}")
    print(f"plot files generated: {plotted_files}")


if __name__ == "__main__":
    main()
