#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import importlib
import importlib.util
import json
import math
import random
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any


SWEEP_NUMERIC_KEYS = [
    "mass_flow_rate",
    "p_low",
    "p_high",
    "t_source",
    "t_sink",
    "t0",
    "p0",
    "eta_a",
    "eta_b",
    "eps_recup",
    "eps_hot",
    "eps_cold",
]


_INVALID_PATH_CHARS = set('<>:"/\\|?*')


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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


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


def _slug_text(value: str) -> str:
    cleaned = [char.lower() if char.isalnum() else "_" for char in value]
    slug = "".join(cleaned).strip("_")
    return slug or "unnamed"


def _slug_number(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    text = f"{float(value):.10g}"
    return text.replace("-", "m").replace("+", "").replace(".", "p")


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _safe_path_component(value: str, fallback: str) -> str:
    cleaned = "".join("_" if ch in _INVALID_PATH_CHARS else ch for ch in value.strip())
    cleaned = cleaned.strip(" .")
    return cleaned or fallback


def _normalize_metadata_name(value: str) -> str:
    cleaned = _safe_path_component(value, "metadata")
    if cleaned.lower().endswith(".parquet"):
        cleaned = cleaned[: -len(".parquet")]
    return cleaned or "metadata"


def _write_single_row_parquet(path: Path, row: dict[str, Any]) -> None:
    try:
        pa = importlib.import_module("pyarrow")
        pq = importlib.import_module("pyarrow.parquet")
    except ImportError as exc:
        raise RuntimeError(
            "Parquet export requires the 'pyarrow' package. Install it with: pip install pyarrow"
        ) from exc

    table = pa.Table.from_pylist([row])
    pq.write_table(table, path)


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
        ("input_solver_profile_name", "TEXT"),
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


def _default_numeric_bounds(_base_config: dict[str, Any]) -> dict[str, tuple[float, float]]:
    _ = _base_config
    return {
        "mass_flow_rate": (0.1, 200.0),
        "p_low": (8.0e6, 3.5e7),
        "p_high": (9.0e6, 5.5e7),
        "t_source": (450.0, 1400.0),
        "t_sink": (250.0, 750.0),
        "t0": (250.0, 350.0),
        "p0": (8.0e4, 2.5e5),
        "eta_a": (0.5, 1.0),
        "eta_b": (0.5, 1.0),
        "eps_recup": (0.2, 1.0),
        "eps_hot": (0.2, 1.0),
        "eps_cold": (0.2, 1.0),
    }


def _base_solver_profile(base_config: dict[str, Any]) -> dict[str, Any]:
    solver = base_config.get("solver", {})
    return {
        "name": "base",
        "max_iterations": int(solver.get("max_iterations", 100)),
        "tolerance": float(solver.get("tolerance", 0.01)),
        "enthalpy_tolerance": float(solver.get("enthalpy_tolerance", 10.0)),
        "relaxation": float(solver.get("relaxation", 0.5)),
    }


def _load_lhsmdu_config(path: Path, base_config: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"LHSMDU config file not found: {path}. "
            "Create the file or pass --lhsmdu-config to an existing JSON."
        )

    with path.open("r", encoding="utf-8") as handle:
        raw_cfg = json.load(handle)

    if not isinstance(raw_cfg, dict):
        raise ValueError("LHSMDU config must be a JSON object")

    defaults = _default_numeric_bounds(base_config)
    raw_bounds = raw_cfg.get("numeric_bounds", {})

    numeric_bounds: dict[str, tuple[float, float]] = {}
    for key in SWEEP_NUMERIC_KEYS:
        raw_range = raw_bounds.get(key, defaults[key])
        if not isinstance(raw_range, list) or len(raw_range) != 2:
            raise ValueError(f"numeric_bounds.{key} must be [min, max]")
        lower = float(raw_range[0])
        upper = float(raw_range[1])
        if upper <= lower:
            raise ValueError(f"numeric_bounds.{key} must satisfy max > min")
        numeric_bounds[key] = (lower, upper)

    fixed_defaults = {
        "fluid": base_config.get("fluid", "CO2"),
        "expander_mode": base_config.get("turbomachine_A", {}).get("expander_mode", "throttle"),
        "base_mode": base_config.get("mode", "discharge"),
    }
    fixed_cfg = raw_cfg.get("fixed", {})
    if not isinstance(fixed_cfg, dict):
        raise ValueError("fixed must be an object")
    fixed = {
        "fluid": str(fixed_cfg.get("fluid", fixed_defaults["fluid"])),
        "expander_mode": str(fixed_cfg.get("expander_mode", fixed_defaults["expander_mode"])),
        "base_mode": str(fixed_cfg.get("base_mode", fixed_defaults["base_mode"])),
    }

    constraints_defaults = {
        "min_delta_p_pa": 2.0e5,
        "min_delta_t_k": 5.0,
        "avoid_vapor_dome": True,
        "critical_pressure_pa": 7.377e6,
        "critical_pressure_margin_pa": 1.0e5,
        "enforce_temperature_above_critical": False,
        "critical_temperature_k": 304.1282,
        "critical_temperature_margin_k": 2.0,
    }
    constraints_raw = raw_cfg.get("constraints", {})
    if not isinstance(constraints_raw, dict):
        raise ValueError("constraints must be an object")

    constraints = {
        "min_delta_p_pa": float(
            constraints_raw.get("min_delta_p_pa", constraints_defaults["min_delta_p_pa"])
        ),
        "min_delta_t_k": float(
            constraints_raw.get("min_delta_t_k", constraints_defaults["min_delta_t_k"])
        ),
        "avoid_vapor_dome": bool(
            constraints_raw.get("avoid_vapor_dome", constraints_defaults["avoid_vapor_dome"])
        ),
        "critical_pressure_pa": float(
            constraints_raw.get("critical_pressure_pa", constraints_defaults["critical_pressure_pa"])
        ),
        "critical_pressure_margin_pa": float(
            constraints_raw.get(
                "critical_pressure_margin_pa", constraints_defaults["critical_pressure_margin_pa"]
            )
        ),
        "enforce_temperature_above_critical": bool(
            constraints_raw.get(
                "enforce_temperature_above_critical",
                constraints_defaults["enforce_temperature_above_critical"],
            )
        ),
        "critical_temperature_k": float(
            constraints_raw.get(
                "critical_temperature_k", constraints_defaults["critical_temperature_k"]
            )
        ),
        "critical_temperature_margin_k": float(
            constraints_raw.get(
                "critical_temperature_margin_k", constraints_defaults["critical_temperature_margin_k"]
            )
        ),
    }

    n_samples = int(raw_cfg.get("n_samples", 100))
    if n_samples <= 0:
        raise ValueError("n_samples must be > 0")

    seed = int(raw_cfg.get("seed", 42))

    raw_profiles = raw_cfg.get("solver_profiles", [])
    if not isinstance(raw_profiles, list):
        raise ValueError("solver_profiles must be a list")

    if not raw_profiles:
        raw_profiles = [_base_solver_profile(base_config)]

    solver_profiles: list[dict[str, Any]] = []
    for index, profile in enumerate(raw_profiles, start=1):
        if not isinstance(profile, dict):
            raise ValueError(f"solver_profiles[{index-1}] must be an object")
        normalized = {
            "name": str(profile.get("name", f"profile_{index}")),
            "max_iterations": int(
                profile.get("max_iterations", _base_solver_profile(base_config)["max_iterations"])
            ),
            "tolerance": float(
                profile.get("tolerance", _base_solver_profile(base_config)["tolerance"])
            ),
            "enthalpy_tolerance": float(
                profile.get(
                    "enthalpy_tolerance",
                    _base_solver_profile(base_config)["enthalpy_tolerance"],
                )
            ),
            "relaxation": float(
                profile.get("relaxation", _base_solver_profile(base_config)["relaxation"])
            ),
        }
        solver_profiles.append(normalized)

    return {
        "n_samples": n_samples,
        "seed": seed,
        "fixed": fixed,
        "numeric_bounds": numeric_bounds,
        "constraints": constraints,
        "solver_profiles": solver_profiles,
    }


def _generate_lhs_unit_samples(n_samples: int, n_dims: int, seed: int) -> list[list[float]]:
    try:
        import lhsmdu  # type: ignore

        try:
            matrix = lhsmdu.sample(n_dims, n_samples, randomSeed=seed)
        except TypeError:
            lhsmdu.setRandomSeed(seed)
            matrix = lhsmdu.sample(n_dims, n_samples)

        rows: list[list[float]] = []
        for sample_index in range(n_samples):
            rows.append([float(matrix[dim_index][sample_index]) for dim_index in range(n_dims)])
        return rows
    except ImportError:
        rng = random.Random(seed)
        per_dim: list[list[float]] = []
        for _ in range(n_dims):
            bins = list(range(n_samples))
            rng.shuffle(bins)
            dim_vals = [(bins[i] + rng.random()) / n_samples for i in range(n_samples)]
            per_dim.append(dim_vals)

        return [[per_dim[dim][i] for dim in range(n_dims)] for i in range(n_samples)]


def _ensure_cycle_config_structure(config: dict[str, Any]) -> None:
    config.setdefault("pressures", {})
    config.setdefault("temperatures", {})
    config.setdefault("dead_state", {})
    config.setdefault("recuperator", {})
    config.setdefault("heat_exchanger_hot", {})
    config.setdefault("heat_exchanger_cold", {})
    config.setdefault("turbomachine_A", {})
    config.setdefault("turbomachine_B", {})
    config.setdefault("solver", {})
    config.setdefault("notes", {})


def _set_config_numeric_value(config: dict[str, Any], key: str, value: float) -> None:
    _ensure_cycle_config_structure(config)

    if key == "mass_flow_rate":
        config["mass_flow_rate"] = value
    elif key == "p_low":
        config["pressures"]["P_low"] = value
    elif key == "p_high":
        config["pressures"]["P_high"] = value
    elif key == "t_source":
        config["temperatures"]["T_source"] = value
    elif key == "t_sink":
        config["temperatures"]["T_sink"] = value
    elif key == "t0":
        config["dead_state"]["T0"] = value
    elif key == "p0":
        config["dead_state"]["P0"] = value
    elif key == "eta_a":
        config["turbomachine_A"]["eta_isentropic"] = value
    elif key == "eta_b":
        config["turbomachine_B"]["eta_isentropic"] = value
    elif key == "eps_recup":
        config["recuperator"]["effectiveness"] = value
    elif key == "eps_hot":
        config["heat_exchanger_hot"]["effectiveness"] = value
    elif key == "eps_cold":
        config["heat_exchanger_cold"]["effectiveness"] = value
    else:
        raise KeyError(f"Unknown sweep key: {key}")


def _apply_fixed_values(config: dict[str, Any], fixed: dict[str, Any]) -> None:
    _ensure_cycle_config_structure(config)
    config["fluid"] = str(fixed.get("fluid", config.get("fluid", "CO2")))
    config["mode"] = str(fixed.get("base_mode", config.get("mode", "discharge")))
    config["turbomachine_A"]["expander_mode"] = str(
        fixed.get(
            "expander_mode",
            config.get("turbomachine_A", {}).get("expander_mode", "throttle"),
        )
    )


def _apply_constraints(
    config: dict[str, Any],
    bounds: dict[str, tuple[float, float]],
    constraints: dict[str, Any],
) -> None:
    _ensure_cycle_config_structure(config)

    min_delta_p = float(constraints.get("min_delta_p_pa", 2.0e5))
    min_delta_t = float(constraints.get("min_delta_t_k", 5.0))

    p_low_min, p_low_max = bounds["p_low"]
    p_high_min, p_high_max = bounds["p_high"]

    p_low = float(config["pressures"].get("P_low", p_low_min))
    p_high = float(config["pressures"].get("P_high", p_high_max))

    p_low = _clamp(p_low, p_low_min, p_low_max)
    p_high = _clamp(p_high, p_high_min, p_high_max)

    if bool(constraints.get("avoid_vapor_dome", True)) and str(config.get("fluid", "")).upper() == "CO2":
        p_floor = float(constraints.get("critical_pressure_pa", 7.377e6)) + float(
            constraints.get("critical_pressure_margin_pa", 1.0e5)
        )
        p_low_min = max(p_low_min, p_floor)
        p_high_min = max(p_high_min, p_floor)
        p_low = max(p_low, p_floor)
        p_high = max(p_high, p_floor)

    if p_high_max - p_low_min < min_delta_p:
        raise ValueError("Pressure bounds are infeasible for min_delta_p constraint")

    max_low_allowed = min(p_low_max, p_high_max - min_delta_p)
    p_low = _clamp(p_low, p_low_min, max_low_allowed)
    min_high_allowed = max(p_high_min, p_low + min_delta_p)
    p_high = _clamp(p_high, min_high_allowed, p_high_max)

    if p_high < p_low + min_delta_p:
        p_high = p_low + min_delta_p

    if p_high > p_high_max:
        p_high = p_high_max
        p_low = p_high - min_delta_p

    if p_low < p_low_min or p_high > p_high_max or p_high < p_low + min_delta_p:
        raise ValueError("Unable to satisfy pressure constraints for sampled point")

    config["pressures"]["P_low"] = float(p_low)
    config["pressures"]["P_high"] = float(p_high)

    t_sink_min, t_sink_max = bounds["t_sink"]
    t_source_min, t_source_max = bounds["t_source"]

    t_sink = _clamp(float(config["temperatures"].get("T_sink", t_sink_min)), t_sink_min, t_sink_max)
    t_source = _clamp(
        float(config["temperatures"].get("T_source", t_source_max)), t_source_min, t_source_max
    )

    if bool(constraints.get("enforce_temperature_above_critical", False)) and str(
        config.get("fluid", "")
    ).upper() == "CO2":
        t_floor = float(constraints.get("critical_temperature_k", 304.1282)) + float(
            constraints.get("critical_temperature_margin_k", 2.0)
        )
        t_sink = max(t_sink, t_floor)
        t_source = max(t_source, t_floor + min_delta_t)

    feasible_sink_max = min(t_sink_max, t_source_max - min_delta_t)
    if feasible_sink_max < t_sink_min:
        raise ValueError("Temperature bounds are infeasible for min_delta_t constraint")

    t_sink = _clamp(t_sink, t_sink_min, feasible_sink_max)
    source_min_allowed = max(t_source_min, t_sink + min_delta_t)

    if source_min_allowed > t_source_max:
        t_sink = _clamp(t_source_max - min_delta_t, t_sink_min, feasible_sink_max)
        source_min_allowed = max(t_source_min, t_sink + min_delta_t)

    if source_min_allowed > t_source_max:
        raise ValueError("Unable to satisfy source/sink temperature separation")

    t_source = _clamp(t_source, source_min_allowed, t_source_max)
    if t_source <= t_sink + min_delta_t:
        t_source = t_sink + min_delta_t

    if t_source > t_source_max:
        raise ValueError("Unable to satisfy source/sink temperature separation")

    config["temperatures"]["T_sink"] = float(t_sink)
    config["temperatures"]["T_source"] = float(t_source)

    for key in ["eta_a", "eta_b", "eps_recup", "eps_hot", "eps_cold"]:
        low, high = bounds[key]
        if key == "eta_a":
            value = float(config["turbomachine_A"].get("eta_isentropic", low))
            config["turbomachine_A"]["eta_isentropic"] = _clamp(value, low, high)
        elif key == "eta_b":
            value = float(config["turbomachine_B"].get("eta_isentropic", low))
            config["turbomachine_B"]["eta_isentropic"] = _clamp(value, low, high)
        elif key == "eps_recup":
            value = float(config["recuperator"].get("effectiveness", low))
            config["recuperator"]["effectiveness"] = _clamp(value, low, high)
        elif key == "eps_hot":
            value = float(config["heat_exchanger_hot"].get("effectiveness", low))
            config["heat_exchanger_hot"]["effectiveness"] = _clamp(value, low, high)
        elif key == "eps_cold":
            value = float(config["heat_exchanger_cold"].get("effectiveness", low))
            config["heat_exchanger_cold"]["effectiveness"] = _clamp(value, low, high)


def _prepare_lhsmdu_case_configs(
    base_config: dict[str, Any],
    sweep_cfg: dict[str, Any],
    *,
    sample_override: int | None = None,
    seed_override: int | None = None,
) -> list[tuple[int, str, dict[str, Any]]]:
    n_samples = int(sample_override) if sample_override is not None else int(sweep_cfg["n_samples"])
    seed = int(seed_override) if seed_override is not None else int(sweep_cfg["seed"])

    bounds: dict[str, tuple[float, float]] = sweep_cfg["numeric_bounds"]
    fixed: dict[str, Any] = sweep_cfg["fixed"]
    constraints: dict[str, Any] = sweep_cfg["constraints"]

    unit_samples = _generate_lhs_unit_samples(n_samples, len(SWEEP_NUMERIC_KEYS), seed)

    case_configs: list[tuple[int, str, dict[str, Any]]] = []

    for sample_index, unit_row in enumerate(unit_samples, start=1):
        config = copy.deepcopy(base_config)
        _apply_fixed_values(config, fixed)

        for dim_index, param_name in enumerate(SWEEP_NUMERIC_KEYS):
            low, high = bounds[param_name]
            mapped_value = low + float(unit_row[dim_index]) * (high - low)
            _set_config_numeric_value(config, param_name, mapped_value)

        _apply_constraints(config, bounds, constraints)

        notes = config.setdefault("notes", {})
        if isinstance(notes, dict):
            notes["sweep_method"] = "LHSMDU"
            notes["sweep_seed"] = seed
            notes["sweep_sample_index"] = sample_index
            notes["sweep_bounds_configured"] = True

        case_name = f"lhs_{sample_index:05d}"
        case_configs.append((sample_index, case_name, config))

    return case_configs


def _solver_profile_table_name(prefix: str, profile: dict[str, Any], _index: int) -> str:
    _ = _index
    profile_suffix = (
        f"mi{int(profile['max_iterations'])}_"
        f"tol{_slug_number(float(profile['tolerance']))}_"
        f"htol{_slug_number(float(profile['enthalpy_tolerance']))}_"
        f"rel{_slug_number(float(profile['relaxation']))}"
    )
    return f"{_slug_text(prefix)}_solv_{profile_suffix}"


def _apply_solver_profile(config: dict[str, Any], profile: dict[str, Any], profile_index: int) -> str:
    _ensure_cycle_config_structure(config)

    profile_name = str(profile.get("name", f"profile_{profile_index}"))
    config["solver"]["max_iterations"] = int(profile["max_iterations"])
    config["solver"]["tolerance"] = float(profile["tolerance"])
    config["solver"]["enthalpy_tolerance"] = float(profile["enthalpy_tolerance"])
    config["solver"]["relaxation"] = float(profile["relaxation"])
    config["solver_profile_name"] = profile_name

    notes = config.setdefault("notes", {})
    if isinstance(notes, dict):
        notes["solver_profile_name"] = profile_name
        notes["solver_profile"] = {
            "max_iterations": int(profile["max_iterations"]),
            "tolerance": float(profile["tolerance"]),
            "enthalpy_tolerance": float(profile["enthalpy_tolerance"]),
            "relaxation": float(profile["relaxation"]),
        }

    return profile_name


def _flatten_inputs(config: dict[str, Any], case_name: str) -> dict[str, Any]:
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
        "input_case_name": case_name,
        "input_fluid": config.get("fluid"),
        "input_base_mode": config.get("mode"),
        "input_solver_profile_name": config.get("solver_profile_name"),
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


def _run_case_configs_to_table(
    conn: sqlite3.Connection,
    table: str,
    case_configs: list[tuple[int, str, dict[str, Any]]],
    build_cycle: Any,
    *,
    reset_output_table: bool,
) -> tuple[int, int]:
    _ensure_output_table(conn, table, reset=reset_output_table)

    total = len(case_configs)
    success = 0

    for row_index, (case_id, case_name, resolved_config) in enumerate(case_configs, start=1):
        t0 = float(resolved_config.get("dead_state", {}).get("T0", 300.0))

        output_row: dict[str, Any] = {
            "case_id": case_id,
            "case_name": case_name,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "error": "",
        }
        output_row.update(_flatten_inputs(resolved_config, case_name))

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

        _upsert_output_row(conn, table, output_row)
        print(f"[{row_index}/{total}] processed case_id={case_id} ({case_name}) -> {output_row['status']}")

    return total, success


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


def _export_success_rows_to_parquet(
    conn: sqlite3.Connection,
    table: str,
    *,
    output_root: Path,
    metadata_name: str,
) -> tuple[int, int]:
    if not _table_exists(conn, table):
        raise ValueError(f"Table not found: {table}")

    columns = _get_table_columns(conn, table)
    if "status" not in columns:
        raise ValueError(f"Table {table} has no 'status' column to filter successful rows")

    total_rows = int(
        conn.execute(f"SELECT COUNT(*) FROM {_quote_identifier(table)}").fetchone()[0]
    )

    order_column = "case_id" if "case_id" in columns else "rowid"
    success_rows = conn.execute(
        f"SELECT * FROM {_quote_identifier(table)} WHERE status = ? ORDER BY {order_column}",
        ("ok",),
    ).fetchall()

    table_folder = _safe_path_component(table, "table")
    metadata_base = _normalize_metadata_name(metadata_name)
    output_root.mkdir(parents=True, exist_ok=True)

    written = 0
    for row_index, row in enumerate(success_rows, start=1):
        row_dict = dict(row)
        case_value = row_dict.get("case_id")

        if isinstance(case_value, int):
            row_folder = f"row_{case_value}"
        elif isinstance(case_value, float) and case_value.is_integer():
            row_folder = f"row_{int(case_value)}"
        elif case_value is not None:
            row_folder = f"row_{_safe_path_component(str(case_value), str(row_index))}"
        else:
            row_folder = f"row_{row_index}"

        row_dir = output_root / table_folder / row_folder
        row_dir.mkdir(parents=True, exist_ok=True)

        parquet_path = row_dir / f"{metadata_base}.parquet"
        _write_single_row_parquet(parquet_path, row_dict)
        written += 1

    return total_rows, written


def _run_plot_exported_cycle_diagrams(
    *,
    export_root: Path,
    table_folder: str,
    metadata_name: str,
    overwrite: bool,
    no_vapor_dome: bool,
    skip_drift_check: bool,
    drift_tolerance: float,
    limit: int | None,
) -> None:
    plot_script = Path(__file__).resolve().parent / "plot_exported_cycle_diagrams.py"
    if not plot_script.exists():
        raise FileNotFoundError(f"Plot script not found: {plot_script}")

    command: list[str] = [
        sys.executable,
        str(plot_script),
        "--export-root",
        str(export_root),
        "--table",
        table_folder,
        "--metadata-name",
        metadata_name,
    ]

    if overwrite:
        command.append("--overwrite")
    if no_vapor_dome:
        command.append("--no-vapor-dome")
    if skip_drift_check:
        command.append("--skip-drift-check")
    if limit is not None:
        command.extend(["--limit", str(limit)])
    command.extend(["--drift-tolerance", f"{max(0.0, drift_tolerance):.12g}"])

    print("Starting automatic plot generation for exported parquet rows...")
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "Automatic plotting failed after parquet export. "
            "Run plot_exported_cycle_diagrams.py manually to inspect details."
        )


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
        help="SQLite output table name (used in standard mode)",
    )
    parser.add_argument(
        "--table-prefix",
        type=str,
        default="results",
        help="Output table prefix for LHSMDU mode",
    )
    parser.add_argument(
        "--reset-output-table",
        action="store_true",
        help="Drop and recreate output table(s) before writing",
    )
    parser.add_argument(
        "--seed-baseline",
        action="store_true",
        help="Insert baseline case from config if missing (standard mode)",
    )
    parser.add_argument(
        "--seed-eta-grid",
        action="store_true",
        help="Insert eta_a x eta_b grid cases based on range arguments (standard mode)",
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
        help="Optional single case_id to run (standard mode)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of enabled input rows to run (standard mode)",
    )

    parser.add_argument(
        "--run-lhsmdu",
        action="store_true",
        help="Run LHSMDU parameter sweep from a JSON config and write per-solver-profile tables",
    )
    parser.add_argument(
        "--lhsmdu-config",
        type=Path,
        default=Path(__file__).resolve().parent / "lhsmdu_sweep_config.json",
        help="Path to LHSMDU sweep JSON config",
    )
    parser.add_argument(
        "--lhsmdu-samples",
        type=int,
        default=None,
        help="Optional sample-count override for LHSMDU mode",
    )
    parser.add_argument(
        "--lhsmdu-seed",
        type=int,
        default=None,
        help="Optional seed override for LHSMDU mode",
    )
    parser.add_argument(
        "--export-success-parquet",
        action="store_true",
        help=(
            "Export successful rows (status='ok') from one existing results table into "
            "one parquet file per row"
        ),
    )
    parser.add_argument(
        "--export-table",
        type=str,
        default=None,
        help="Source table to export in parquet mode",
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=Path(__file__).resolve().parent / "metadata",
        help="Root folder for parquet metadata exports",
    )
    parser.add_argument(
        "--metadata-name",
        type=str,
        default="metadata",
        help="Base filename for each exported parquet metadata file",
    )
    parser.add_argument(
        "--plot-after-export",
        action="store_true",
        help="After parquet export, automatically generate charge/discharge cycle plots",
    )
    parser.add_argument(
        "--plot-overwrite",
        action="store_true",
        help="When used with --plot-after-export, overwrite existing plot png files",
    )
    parser.add_argument(
        "--plot-no-vapor-dome",
        action="store_true",
        help="When used with --plot-after-export, disable vapor-dome overlay",
    )
    parser.add_argument(
        "--plot-skip-drift-check",
        action="store_true",
        help="When used with --plot-after-export, skip stored-vs-recomputed drift warnings",
    )
    parser.add_argument(
        "--plot-drift-tolerance",
        type=float,
        default=1.0e-6,
        help="Relative drift tolerance passed to plot runner when --plot-after-export is enabled",
    )
    parser.add_argument(
        "--plot-limit",
        type=int,
        default=None,
        help="Optional row limit passed to plot runner when --plot-after-export is enabled",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    try:
        if args.export_success_parquet:
            if not args.export_table:
                raise ValueError("--export-table is required when using --export-success-parquet")

            total_rows, written = _export_success_rows_to_parquet(
                conn,
                args.export_table,
                output_root=args.export_root,
                metadata_name=args.metadata_name,
            )
            print(
                f"Exported {written} successful row metadata parquet files "
                f"from table {args.export_table} (total rows: {total_rows}) into {args.export_root}"
            )

            if args.plot_after_export:
                if written == 0:
                    print("No successful rows were exported, skipping automatic plot generation.")
                else:
                    table_folder = _safe_path_component(args.export_table, "table")
                    _run_plot_exported_cycle_diagrams(
                        export_root=args.export_root,
                        table_folder=table_folder,
                        metadata_name=args.metadata_name,
                        overwrite=args.plot_overwrite,
                        no_vapor_dome=args.plot_no_vapor_dome,
                        skip_drift_check=args.plot_skip_drift_check,
                        drift_tolerance=args.plot_drift_tolerance,
                        limit=args.plot_limit,
                    )
            return

        module = _load_solver_module()
        load_config = module.load_config
        build_cycle = module.build_cycle

        base_config = load_config(args.config)

        _ensure_input_table(conn, args.input_table)

        if args.run_lhsmdu:
            sweep_cfg = _load_lhsmdu_config(args.lhsmdu_config, base_config)
            raw_case_configs = _prepare_lhsmdu_case_configs(
                base_config,
                sweep_cfg,
                sample_override=args.lhsmdu_samples,
                seed_override=args.lhsmdu_seed,
            )

            profiles = sweep_cfg["solver_profiles"]
            for profile_index, profile in enumerate(profiles, start=1):
                table_name = _solver_profile_table_name(args.table_prefix, profile, profile_index)

                profiled_cases: list[tuple[int, str, dict[str, Any]]] = []
                for case_id, case_name, case_cfg in raw_case_configs:
                    cfg = copy.deepcopy(case_cfg)
                    _apply_solver_profile(cfg, profile, profile_index)
                    profiled_cases.append((case_id, case_name, cfg))

                total, success = _run_case_configs_to_table(
                    conn,
                    table_name,
                    profiled_cases,
                    build_cycle,
                    reset_output_table=args.reset_output_table,
                )
                print(
                    f"Completed table {table_name}: {success}/{total} successful dual-mode rows"
                )
            return

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

        case_configs: list[tuple[int, str, dict[str, Any]]] = []
        for case_row in case_rows:
            case_id = int(case_row["case_id"])
            case_name = str(case_row.get("case_name") or f"case_{case_id}")
            resolved_config = _resolve_case_config(base_config, case_row)
            case_configs.append((case_id, case_name, resolved_config))

        total, success = _run_case_configs_to_table(
            conn,
            args.output_table,
            case_configs,
            build_cycle,
            reset_output_table=False,
        )
        print(
            f"Completed dual-mode run for {total} cases. "
            f"Successful dual-mode rows: {success}. Output table: {args.output_table}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
