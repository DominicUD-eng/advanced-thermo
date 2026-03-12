#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
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


def _quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) * 2)}"'


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


def _safe_load_json_object(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")

    if not isinstance(raw, str) or not raw.strip():
        return None

    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None

    return value if isinstance(value, dict) else None


def _get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({_quote_identifier(table)})").fetchall()
    return {str(row[1]) for row in rows}


def _ensure_table_columns(
    conn: sqlite3.Connection,
    table: str,
    columns: list[tuple[str, str]],
) -> None:
    existing_columns = _get_table_columns(conn, table)
    for col_name, col_type in columns:
        if col_name in existing_columns:
            continue
        conn.execute(
            f"ALTER TABLE {_quote_identifier(table)} "
            f"ADD COLUMN {_quote_identifier(col_name)} {col_type}"
        )
    conn.commit()


INPUT_TABLE_COLUMNS: list[tuple[str, str]] = [
    ("case_id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("case_name", "TEXT UNIQUE"),
    ("enabled", "INTEGER NOT NULL DEFAULT 1"),
    ("fluid", "TEXT"),
    ("base_mode", "TEXT"),
    ("mass_flow_rate", "REAL"),
    ("p_low", "REAL"),
    ("p_high", "REAL"),
    ("t_source", "REAL"),
    ("t_sink", "REAL"),
    ("t0", "REAL"),
    ("p0", "REAL"),
    ("eta_a", "REAL"),
    ("eta_b", "REAL"),
    ("expander_mode", "TEXT"),
    ("eps_recup", "REAL"),
    ("eps_hot", "REAL"),
    ("eps_cold", "REAL"),
    ("solver_max_iterations", "INTEGER"),
    ("solver_tolerance", "REAL"),
    ("solver_enthalpy_tolerance", "REAL"),
    ("solver_relaxation", "REAL"),
    ("notes", "TEXT"),
    ("notes_json", "TEXT"),
    ("config_json", "TEXT"),
    ("created_at", "TEXT NOT NULL"),
    ("updated_at", "TEXT NOT NULL"),
]


def _mode_output_columns(mode_prefix: str) -> list[tuple[str, str]]:
    return [
        (f"{mode_prefix}_status", "TEXT"),
        (f"{mode_prefix}_error", "TEXT"),
        (f"{mode_prefix}_mode", "TEXT"),
        (f"{mode_prefix}_fluid", "TEXT"),
        (f"{mode_prefix}_converged", "INTEGER"),
        (f"{mode_prefix}_iterations", "INTEGER"),
        (f"{mode_prefix}_net_work_w", "REAL"),
        (f"{mode_prefix}_q_hot_w", "REAL"),
        (f"{mode_prefix}_q_cold_w", "REAL"),
        (f"{mode_prefix}_cop_or_eta", "REAL"),
        (f"{mode_prefix}_exergetic_efficiency", "REAL"),
        (f"{mode_prefix}_cycle_isentropic_efficiency", "REAL"),
        (f"{mode_prefix}_isentropic_reference_net_work_w", "REAL"),
        (f"{mode_prefix}_total_exergy_destruction_w", "REAL"),
        (f"{mode_prefix}_machine_a_mode", "TEXT"),
        (f"{mode_prefix}_machine_a_w_dot_w", "REAL"),
        (f"{mode_prefix}_machine_a_x_dest_w", "REAL"),
        (f"{mode_prefix}_machine_b_mode", "TEXT"),
        (f"{mode_prefix}_machine_b_w_dot_w", "REAL"),
        (f"{mode_prefix}_machine_b_x_dest_w", "REAL"),
        (f"{mode_prefix}_recuperator_q_dot_w", "REAL"),
        (f"{mode_prefix}_recuperator_x_dest_w", "REAL"),
        (f"{mode_prefix}_hot_hx_q_dot_w", "REAL"),
        (f"{mode_prefix}_hot_hx_x_dest_w", "REAL"),
        (f"{mode_prefix}_cold_hx_q_dot_w", "REAL"),
        (f"{mode_prefix}_cold_hx_x_dest_w", "REAL"),
    ]


def _essential_output_columns() -> list[tuple[str, str]]:
    columns: list[tuple[str, str]] = [
        ("case_id", "INTEGER PRIMARY KEY"),
        ("case_name", "TEXT"),
        ("status", "TEXT"),
        ("error", "TEXT"),
        ("run_timestamp", "TEXT NOT NULL"),
        ("input_case_name", "TEXT"),
        ("input_fluid", "TEXT"),
        ("input_base_mode", "TEXT"),
        ("input_mass_flow_rate_kg_per_s", "REAL"),
        ("input_p_low_pa", "REAL"),
        ("input_p_high_pa", "REAL"),
        ("input_t_source_k", "REAL"),
        ("input_t_sink_k", "REAL"),
        ("input_t0_k", "REAL"),
        ("input_p0_pa", "REAL"),
        ("input_eta_a", "REAL"),
        ("input_eta_b", "REAL"),
        ("input_expander_mode", "TEXT"),
        ("input_eps_recup", "REAL"),
        ("input_eps_hot", "REAL"),
        ("input_eps_cold", "REAL"),
        ("input_solver_max_iterations", "INTEGER"),
        ("input_solver_tolerance", "REAL"),
        ("input_solver_enthalpy_tolerance", "REAL"),
        ("input_solver_relaxation", "REAL"),
        ("input_notes_json", "TEXT"),
        ("input_config_json", "TEXT"),
    ]

    columns.extend(_mode_output_columns("charge"))
    columns.extend(_mode_output_columns("discharge"))
    columns.extend(
        [
            ("objective_ex_eff_min_both", "REAL"),
            ("objective_ex_eff_product", "REAL"),
            ("objective_ex_eff_delta_discharge_minus_charge", "REAL"),
            ("objective_ex_eff_harmonic_mean", "REAL"),
            ("objective_round_trip_proxy", "REAL"),
        ]
    )
    return columns


def _ensure_input_table(conn: sqlite3.Connection, table: str) -> None:
    column_defs = ",\n            ".join(
        f"{_quote_identifier(name)} {sql_type}" for name, sql_type in INPUT_TABLE_COLUMNS
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_quote_identifier(table)} (
            {column_defs}
        )
        """
    )
    conn.commit()

    migratable = [
        (name, sql_type)
        for name, sql_type in INPUT_TABLE_COLUMNS
        if "PRIMARY KEY" not in sql_type.upper()
    ]
    _ensure_table_columns(conn, table, migratable)


def _ensure_output_table(conn: sqlite3.Connection, table: str, *, reset: bool = False) -> None:
    if reset:
        conn.execute(f"DROP TABLE IF EXISTS {_quote_identifier(table)}")
        conn.commit()

    columns = _essential_output_columns()
    column_defs = ",\n            ".join(
        f"{_quote_identifier(name)} {sql_type}" for name, sql_type in columns
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_quote_identifier(table)} (
            {column_defs}
        )
        """
    )
    conn.commit()

    migratable = [
        (name, sql_type)
        for name, sql_type in columns
        if "PRIMARY KEY" not in sql_type.upper()
    ]
    _ensure_table_columns(conn, table, migratable)


def _normalize_sql_value(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (int, str)) or value is None:
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _upsert_output_row(conn: sqlite3.Connection, table: str, row: dict[str, Any]) -> None:
    existing_columns = _get_table_columns(conn, table)
    normalized_row = {
        key: _normalize_sql_value(value)
        for key, value in row.items()
        if key in existing_columns
    }

    if "case_id" not in normalized_row:
        raise ValueError("Output row is missing required key 'case_id'")

    columns = sorted(normalized_row.keys())
    quoted_cols = ", ".join(_quote_identifier(col) for col in columns)
    placeholders = ", ".join("?" for _ in columns)
    values = [normalized_row[col] for col in columns]

    assignments = ", ".join(
        f"{_quote_identifier(col)}=excluded.{_quote_identifier(col)}"
        for col in columns
        if col != "case_id"
    )

    on_conflict = (
        f"ON CONFLICT(case_id) DO UPDATE SET {assignments}"
        if assignments
        else "ON CONFLICT(case_id) DO NOTHING"
    )

    conn.execute(
        f"""
        INSERT INTO {_quote_identifier(table)} ({quoted_cols})
        VALUES ({placeholders})
        {on_conflict}
        """,
        values,
    )
    conn.commit()


def _config_to_input_row(config: dict[str, Any], *, case_name: str, notes: str = "") -> dict[str, Any]:
    pressures = config.get("pressures", {})
    temperatures = config.get("temperatures", {})
    dead_state = config.get("dead_state", {})
    recup = config.get("recuperator", {})
    hot_hx = config.get("heat_exchanger_hot", {})
    cold_hx = config.get("heat_exchanger_cold", {})
    machine_a = config.get("turbomachine_A", {})
    machine_b = config.get("turbomachine_B", {})
    solver = config.get("solver", {})

    timestamp = datetime.now(timezone.utc).isoformat()
    notes_obj = config.get("notes", {})

    return {
        "case_name": case_name,
        "enabled": 1,
        "fluid": config.get("fluid", "CO2"),
        "base_mode": str(config.get("mode", "charge")),
        "mass_flow_rate": float(config.get("mass_flow_rate", 1.0)),
        "p_low": float(pressures.get("P_low", 8.0e6)),
        "p_high": float(pressures.get("P_high", 20.0e6)),
        "t_source": float(temperatures.get("T_source", 700.0)),
        "t_sink": float(temperatures.get("T_sink", 300.0)),
        "t0": float(dead_state.get("T0", 300.0)),
        "p0": float(dead_state.get("P0", 101325.0)),
        "eta_a": float(machine_a.get("eta_isentropic", 1.0)),
        "eta_b": float(machine_b.get("eta_isentropic", 1.0)),
        "expander_mode": str(machine_a.get("expander_mode", "throttle")),
        "eps_recup": float(recup.get("effectiveness", 1.0)),
        "eps_hot": float(hot_hx.get("effectiveness", 1.0)),
        "eps_cold": float(cold_hx.get("effectiveness", 1.0)),
        "solver_max_iterations": int(solver.get("max_iterations", 100)),
        "solver_tolerance": float(solver.get("tolerance", 0.01)),
        "solver_enthalpy_tolerance": float(solver.get("enthalpy_tolerance", 10.0)),
        "solver_relaxation": float(solver.get("relaxation", 0.5)),
        "notes": notes,
        "notes_json": json.dumps(notes_obj, sort_keys=True),
        "config_json": json.dumps(config, sort_keys=True),
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _insert_case_if_missing(conn: sqlite3.Connection, table: str, case_row: dict[str, Any]) -> bool:
    columns = sorted(case_row.keys())
    values = [case_row[col] for col in columns]
    quoted_cols = ", ".join(_quote_identifier(col) for col in columns)
    placeholders = ", ".join("?" for _ in columns)

    cursor = conn.execute(
        f"INSERT OR IGNORE INTO {_quote_identifier(table)} ({quoted_cols}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    return int(cursor.rowcount) > 0


def _seed_baseline_case(
    conn: sqlite3.Connection,
    table: str,
    base_config: dict[str, Any],
    *,
    force: bool = False,
) -> None:
    if not force:
        existing = conn.execute(f"SELECT COUNT(*) FROM {_quote_identifier(table)}").fetchone()
        if existing is not None and int(existing[0]) > 0:
            return

    baseline_row = _config_to_input_row(base_config, case_name="baseline", notes="seeded")
    _insert_case_if_missing(conn, table, baseline_row)


def _seed_eta_grid_cases(
    conn: sqlite3.Connection,
    table: str,
    base_config: dict[str, Any],
    eta_a_values: list[float],
    eta_b_values: list[float],
) -> int:
    inserted = 0
    for eta_a in eta_a_values:
        for eta_b in eta_b_values:
            config = copy.deepcopy(base_config)
            config.setdefault("turbomachine_A", {})
            config.setdefault("turbomachine_B", {})
            config["turbomachine_A"]["eta_isentropic"] = eta_a
            config["turbomachine_B"]["eta_isentropic"] = eta_b

            case_name = f"etaA_{eta_a:.3f}_etaB_{eta_b:.3f}"
            case_row = _config_to_input_row(config, case_name=case_name, notes="grid seed")
            if _insert_case_if_missing(conn, table, case_row):
                inserted += 1

    return inserted


def _resolve_case_config(base_config: dict[str, Any], case_row: dict[str, Any]) -> dict[str, Any]:
    config_json_obj = _safe_load_json_object(case_row.get("config_json"))
    if config_json_obj is not None:
        config = config_json_obj
    else:
        config = copy.deepcopy(base_config)

    config.setdefault("pressures", {})
    config.setdefault("temperatures", {})
    config.setdefault("dead_state", {})
    config.setdefault("recuperator", {})
    config.setdefault("heat_exchanger_hot", {})
    config.setdefault("heat_exchanger_cold", {})
    config.setdefault("turbomachine_A", {})
    config.setdefault("turbomachine_B", {})
    config.setdefault("solver", {})

    notes_obj = _safe_load_json_object(case_row.get("notes_json"))
    if notes_obj is not None:
        config["notes"] = notes_obj

    if case_row.get("fluid") is not None:
        config["fluid"] = case_row["fluid"]
    if case_row.get("base_mode") is not None:
        config["mode"] = str(case_row["base_mode"])
    if case_row.get("mass_flow_rate") is not None:
        config["mass_flow_rate"] = float(case_row["mass_flow_rate"])

    if case_row.get("p_low") is not None:
        config["pressures"]["P_low"] = float(case_row["p_low"])
    if case_row.get("p_high") is not None:
        config["pressures"]["P_high"] = float(case_row["p_high"])

    if case_row.get("t_source") is not None:
        config["temperatures"]["T_source"] = float(case_row["t_source"])
    if case_row.get("t_sink") is not None:
        config["temperatures"]["T_sink"] = float(case_row["t_sink"])

    if case_row.get("t0") is not None:
        config["dead_state"]["T0"] = float(case_row["t0"])
    if case_row.get("p0") is not None:
        config["dead_state"]["P0"] = float(case_row["p0"])

    if case_row.get("eps_recup") is not None:
        config["recuperator"]["effectiveness"] = float(case_row["eps_recup"])
    if case_row.get("eps_hot") is not None:
        config["heat_exchanger_hot"]["effectiveness"] = float(case_row["eps_hot"])
    if case_row.get("eps_cold") is not None:
        config["heat_exchanger_cold"]["effectiveness"] = float(case_row["eps_cold"])

    if case_row.get("eta_a") is not None:
        config["turbomachine_A"]["eta_isentropic"] = float(case_row["eta_a"])
    if case_row.get("eta_b") is not None:
        config["turbomachine_B"]["eta_isentropic"] = float(case_row["eta_b"])
    if case_row.get("expander_mode") is not None:
        config["turbomachine_A"]["expander_mode"] = str(case_row["expander_mode"])

    if case_row.get("solver_max_iterations") is not None:
        config["solver"]["max_iterations"] = int(case_row["solver_max_iterations"])
    if case_row.get("solver_tolerance") is not None:
        config["solver"]["tolerance"] = float(case_row["solver_tolerance"])
    if case_row.get("solver_enthalpy_tolerance") is not None:
        config["solver"]["enthalpy_tolerance"] = float(case_row["solver_enthalpy_tolerance"])
    if case_row.get("solver_relaxation") is not None:
        config["solver"]["relaxation"] = float(case_row["solver_relaxation"])

    return config


def _flatten_inputs(config: dict[str, Any], case_row: dict[str, Any]) -> dict[str, Any]:
    pressures = config.get("pressures", {})
    temperatures = config.get("temperatures", {})
    dead_state = config.get("dead_state", {})
    recup = config.get("recuperator", {})
    hot_hx = config.get("heat_exchanger_hot", {})
    cold_hx = config.get("heat_exchanger_cold", {})
    machine_a = config.get("turbomachine_A", {})
    machine_b = config.get("turbomachine_B", {})
    solver = config.get("solver", {})
    notes_obj = config.get("notes", {})

    return {
        "input_case_name": case_row.get("case_name"),
        "input_fluid": config.get("fluid"),
        "input_base_mode": config.get("mode"),
        "input_mass_flow_rate_kg_per_s": config.get("mass_flow_rate"),
        "input_p_low_pa": pressures.get("P_low"),
        "input_p_high_pa": pressures.get("P_high"),
        "input_t_source_k": temperatures.get("T_source"),
        "input_t_sink_k": temperatures.get("T_sink"),
        "input_t0_k": dead_state.get("T0"),
        "input_p0_pa": dead_state.get("P0"),
        "input_eta_a": machine_a.get("eta_isentropic"),
        "input_eta_b": machine_b.get("eta_isentropic"),
        "input_expander_mode": machine_a.get("expander_mode"),
        "input_eps_recup": recup.get("effectiveness"),
        "input_eps_hot": hot_hx.get("effectiveness"),
        "input_eps_cold": cold_hx.get("effectiveness"),
        "input_solver_max_iterations": solver.get("max_iterations"),
        "input_solver_tolerance": solver.get("tolerance"),
        "input_solver_enthalpy_tolerance": solver.get("enthalpy_tolerance"),
        "input_solver_relaxation": solver.get("relaxation"),
        "input_notes_json": json.dumps(notes_obj, sort_keys=True),
        "input_config_json": json.dumps(config, sort_keys=True),
    }


def _flatten_cycle_result(mode_prefix: str, result: object, t0: float) -> dict[str, Any]:
    components = getattr(result, "components", {})
    machine_a = components.get("machine_A")
    machine_b = components.get("machine_B")
    recuperator = components.get("recuperator")
    hot_hx = components.get("hot_hx")
    cold_hx = components.get("cold_hx")

    row: dict[str, Any] = {
        f"{mode_prefix}_mode": getattr(result, "mode"),
        f"{mode_prefix}_fluid": getattr(result, "fluid"),
        f"{mode_prefix}_converged": int(getattr(result, "converged")),
        f"{mode_prefix}_iterations": getattr(result, "iterations"),
        f"{mode_prefix}_net_work_w": getattr(result, "net_work"),
        f"{mode_prefix}_q_hot_w": getattr(result, "Q_hot"),
        f"{mode_prefix}_q_cold_w": getattr(result, "Q_cold"),
        f"{mode_prefix}_cop_or_eta": getattr(result, "COP_or_eta"),
        f"{mode_prefix}_exergetic_efficiency": getattr(result, "exergetic_efficiency"),
        f"{mode_prefix}_cycle_isentropic_efficiency": getattr(result, "cycle_isentropic_efficiency"),
        f"{mode_prefix}_isentropic_reference_net_work_w": getattr(
            result, "isentropic_reference_net_work"
        ),
        f"{mode_prefix}_total_exergy_destruction_w": getattr(
            result, "total_exergy_destruction"
        ),
        f"{mode_prefix}_machine_a_mode": getattr(machine_a, "mode", None),
        f"{mode_prefix}_machine_a_w_dot_w": getattr(machine_a, "W_dot", math.nan),
        f"{mode_prefix}_machine_a_x_dest_w": (
            machine_a.exergy_destruction(t0) if machine_a is not None else math.nan
        ),
        f"{mode_prefix}_machine_b_mode": getattr(machine_b, "mode", None),
        f"{mode_prefix}_machine_b_w_dot_w": getattr(machine_b, "W_dot", math.nan),
        f"{mode_prefix}_machine_b_x_dest_w": (
            machine_b.exergy_destruction(t0) if machine_b is not None else math.nan
        ),
        f"{mode_prefix}_recuperator_q_dot_w": getattr(recuperator, "Q_dot", math.nan),
        f"{mode_prefix}_recuperator_x_dest_w": (
            recuperator.exergy_destruction(t0) if recuperator is not None else math.nan
        ),
        f"{mode_prefix}_hot_hx_q_dot_w": getattr(hot_hx, "Q_dot", math.nan),
        f"{mode_prefix}_hot_hx_x_dest_w": hot_hx.exergy_destruction(t0) if hot_hx is not None else math.nan,
        f"{mode_prefix}_cold_hx_q_dot_w": getattr(cold_hx, "Q_dot", math.nan),
        f"{mode_prefix}_cold_hx_x_dest_w": (
            cold_hx.exergy_destruction(t0) if cold_hx is not None else math.nan
        ),
    }
    return row


def _add_dual_mode_objectives(row: dict[str, Any]) -> None:
    charge_ex = row.get("charge_exergetic_efficiency")
    discharge_ex = row.get("discharge_exergetic_efficiency")
    charge_cop = row.get("charge_cop_or_eta")
    discharge_eta = row.get("discharge_cop_or_eta")

    if isinstance(charge_ex, (int, float)) and isinstance(discharge_ex, (int, float)):
        if math.isfinite(charge_ex) and math.isfinite(discharge_ex):
            row["objective_ex_eff_min_both"] = min(charge_ex, discharge_ex)
            row["objective_ex_eff_product"] = charge_ex * discharge_ex
            row["objective_ex_eff_delta_discharge_minus_charge"] = discharge_ex - charge_ex
            ex_sum = charge_ex + discharge_ex
            if ex_sum > 0.0:
                row["objective_ex_eff_harmonic_mean"] = 2.0 * charge_ex * discharge_ex / ex_sum

    if isinstance(charge_cop, (int, float)) and isinstance(discharge_eta, (int, float)):
        if math.isfinite(charge_cop) and math.isfinite(discharge_eta):
            row["objective_round_trip_proxy"] = discharge_eta * charge_cop


def _select_cases(
    conn: sqlite3.Connection,
    table: str,
    *,
    case_id: int | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    query = f"SELECT * FROM {_quote_identifier(table)} WHERE enabled = 1"
    params: list[Any] = []

    if case_id is not None:
        query += " AND case_id = ?"
        params.append(case_id)

    query += " ORDER BY case_id"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dual-mode (charge + discharge) sensitivity pipeline backed by SQLite. "
            "One input case -> one output row with all config inputs and essential output metrics."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "config.json",
        help="Path to baseline cycle configuration JSON",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).resolve().parent / "cycle_sensitivity.db",
        help="SQLite database path",
    )
    parser.add_argument(
        "--input-table",
        type=str,
        default="cycle_input_cases",
        help="SQLite input table name",
    )
    parser.add_argument(
        "--output-table",
        type=str,
        default="cycle_dual_mode_results_essential",
        help="SQLite output table name",
    )
    parser.add_argument(
        "--reset-output-table",
        action="store_true",
        help="Drop and recreate the output table before running",
    )
    parser.add_argument(
        "--seed-baseline",
        action="store_true",
        help="Insert baseline case from config if missing",
    )
    parser.add_argument(
        "--seed-eta-grid",
        action="store_true",
        help="Insert eta_a x eta_b grid cases based on range arguments",
    )
    parser.add_argument("--eta-a-min", type=float, default=0.70)
    parser.add_argument("--eta-a-max", type=float, default=1.00)
    parser.add_argument("--eta-a-step", type=float, default=0.05)
    parser.add_argument("--eta-b-min", type=float, default=0.70)
    parser.add_argument("--eta-b-max", type=float, default=1.00)
    parser.add_argument("--eta-b-step", type=float, default=0.05)
    parser.add_argument(
        "--case-id",
        type=int,
        default=None,
        help="Optional single case_id to run",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of enabled input rows to run",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    module = _load_solver_module()
    load_config = module.load_config
    build_cycle = module.build_cycle

    base_config = load_config(args.config)

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    try:
        _ensure_input_table(conn, args.input_table)
        _ensure_output_table(conn, args.output_table, reset=args.reset_output_table)

        if args.seed_baseline:
            _seed_baseline_case(conn, args.input_table, base_config)

        if args.seed_eta_grid:
            eta_a_values = _sweep_values(args.eta_a_min, args.eta_a_max, args.eta_a_step)
            eta_b_values = _sweep_values(args.eta_b_min, args.eta_b_max, args.eta_b_step)
            inserted = _seed_eta_grid_cases(
                conn,
                args.input_table,
                base_config,
                eta_a_values,
                eta_b_values,
            )
            print(f"Inserted {inserted} new grid cases into {args.input_table}")

        if not args.seed_baseline and not args.seed_eta_grid:
            _seed_baseline_case(conn, args.input_table, base_config)

        case_rows = _select_cases(
            conn,
            args.input_table,
            case_id=args.case_id,
            limit=args.limit,
        )

        if not case_rows:
            print("No enabled input cases found to run.")
            return

        total = len(case_rows)
        success = 0

        for row_index, case_row in enumerate(case_rows, start=1):
            case_id = int(case_row["case_id"])
            case_name = str(case_row.get("case_name") or f"case_{case_id}")

            resolved_config = _resolve_case_config(base_config, case_row)
            t0 = float(resolved_config.get("dead_state", {}).get("T0", 300.0))

            output_row: dict[str, Any] = {
                "case_id": case_id,
                "case_name": case_name,
                "run_timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "ok",
                "error": "",
            }
            output_row.update(_flatten_inputs(resolved_config, case_row))

            mode_errors: list[str] = []
            for mode_name in ["charge", "discharge"]:
                mode_config = copy.deepcopy(resolved_config)
                mode_config["mode"] = mode_name

                try:
                    mode_result = build_cycle(mode_config)
                    output_row[f"{mode_name}_status"] = "ok"
                    output_row[f"{mode_name}_error"] = ""
                    output_row.update(_flatten_cycle_result(mode_name, mode_result, t0))
                except (RuntimeError, ValueError) as exc:
                    mode_errors.append(f"{mode_name}: {exc}")
                    output_row[f"{mode_name}_status"] = "error"
                    output_row[f"{mode_name}_error"] = str(exc)

            if mode_errors:
                output_row["status"] = "error"
                output_row["error"] = " | ".join(mode_errors)
            else:
                _add_dual_mode_objectives(output_row)
                success += 1

            _upsert_output_row(conn, args.output_table, output_row)
            print(
                f"[{row_index}/{total}] processed case_id={case_id} "
                f"({case_name}) -> {output_row['status']}"
            )

        print(
            f"Completed dual-mode run for {total} cases. "
            f"Successful dual-mode rows: {success}. Output table: {args.output_table}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
