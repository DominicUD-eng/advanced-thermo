#!/usr/bin/env python3
"""Reversible recuperated Brayton cycle skeleton using CoolProp.

Sign conventions used throughout:
- Work: positive means work INTO the fluid stream (compressor convention)
- Heat: positive means heat INTO the fluid stream
- Exergy destruction is always reported as a non-negative value

For cycle-level reporting:
- CycleResult.net_work is positive when net power is produced by the cycle
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from CoolProp.CoolProp import PropsSI

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from components import HeatExchanger, Recuperator, ReversibleTurbomachine
from plotting.brayton_cycle_plotter import BraytonCyclePlotter


@dataclass
class StatePoint:
    label: str
    T: float
    P: float
    h: float
    s: float
    psi: float


@dataclass
class CycleResult:
    mode: str
    fluid: str
    states: dict[int, StatePoint]
    components: dict[str, object]
    net_work: float
    Q_hot: float
    Q_cold: float
    COP_or_eta: float
    exergetic_efficiency: float
    cycle_isentropic_efficiency: float
    isentropic_reference_net_work: float
    total_exergy_destruction: float
    iterations: int
    converged: bool


def load_config(config_path: Path, mode_override: str | None = None) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    if mode_override is not None:
        config["mode"] = mode_override.lower()
    return config


def _pressure_map(mode: str, p_low: float, p_high: float) -> dict[int, float]:
    if mode == "discharge":
        return {
            1: p_low,
            2: p_high,
            3: p_high,
            4: p_high,
            5: p_low,
            6: p_low,
        }

    return {
        1: p_high,
        2: p_low,
        3: p_low,
        4: p_low,
        5: p_high,
        6: p_high,
    }


def _mode_settings(mode: str, config: dict[str, Any]) -> dict[str, Any]:
    if mode == "discharge":
        return {
            "machine_a_mode": "compressor",
            "machine_b_mode": "expander",
            "hot_hx_heat_into_stream": True,
            "cold_hx_heat_into_stream": False,
        }

    expander_mode = config.get("turbomachine_A", {}).get("expander_mode", "throttle").lower()
    if expander_mode not in {"throttle", "expander"}:
        raise ValueError(
            "turbomachine_A.expander_mode must be either 'throttle' or 'expander'"
        )

    return {
        "machine_a_mode": expander_mode,
        "machine_b_mode": "compressor",
        "hot_hx_heat_into_stream": False,
        "cold_hx_heat_into_stream": True,
    }


def _state_from_known(
    label: str,
    T: float,
    P: float,
    h: float,
    s: float,
    h0: float,
    s0: float,
    T0: float,
) -> StatePoint:
    psi = (h - h0) - T0 * (s - s0)
    return StatePoint(label=label, T=T, P=P, h=h, s=s, psi=psi)


def _compute_exergetic_efficiency(
    mode: str,
    net_work_out: float,
    q_hot: float,
    T0: float,
    t_source: float,
) -> float:
    if t_source <= 0.0:
        return math.nan

    carnot_factor = 1.0 - T0 / t_source
    if carnot_factor <= 0.0:
        return math.nan

    if mode == "discharge":
        exergy_fuel = q_hot * carnot_factor
        return net_work_out / exergy_fuel if exergy_fuel > 0.0 else math.nan

    heat_delivered_hot_store = -q_hot
    work_input = -net_work_out
    exergy_product = heat_delivered_hot_store * carnot_factor
    if work_input <= 0.0:
        return math.nan
    return exergy_product / work_input


def _build_isentropic_reference_config(config: dict[str, Any]) -> dict[str, Any]:
    ref_config = copy.deepcopy(config)

    if "turbomachine_A" not in ref_config:
        ref_config["turbomachine_A"] = {}
    if "turbomachine_B" not in ref_config:
        ref_config["turbomachine_B"] = {}

    ref_config["turbomachine_A"]["eta_isentropic"] = 1.0
    ref_config["turbomachine_B"]["eta_isentropic"] = 1.0
    return ref_config


def _compute_cycle_isentropic_efficiency(
    mode: str,
    actual_net_work: float,
    isentropic_reference_net_work: float,
) -> float:
    if mode == "discharge":
        return (
            actual_net_work / isentropic_reference_net_work
            if isentropic_reference_net_work > 0.0
            else math.nan
        )

    actual_work_input = -actual_net_work
    reference_work_input = -isentropic_reference_net_work
    if actual_work_input <= 0.0:
        return math.nan
    return reference_work_input / actual_work_input if reference_work_input > 0.0 else math.nan


def build_cycle(
    config: dict[str, Any], *, compute_isentropic_reference: bool = True
) -> CycleResult:
    """Build and solve the coupled cycle model with fixed physical state numbering.

    State numbers are pinned to physical locations and do NOT change by mode:

    #        Hot HX
    #     3 -------→ 4
    #     ↑  (recup)  ↓
    #     2 ←------- 5
    #     ↑           ↓
    #     1 ←------- 6
    #        Cold HX

    Discharge (power cycle) sequence along 1→2→3→4→5→6→1:
    - A compresses (P_low → P_high)
    - Hot HX adds heat to the fluid (Q_hot > 0)
    - B expands and outputs shaft work
    - Cold HX rejects heat from the fluid (Q_cold < 0)

    Charge (heat pump) sequence with the same physical state indexing:
    - A is set by turbomachine_A.expander_mode (throttle/expander)
    - B compresses (P_low → P_high)
    - Hot HX rejects heat from fluid to hot store (Q_hot < 0)
    - Cold HX absorbs heat from cold store into fluid (Q_cold > 0)
    """

    fluid = config.get("fluid", "CO2")
    mode = config.get("mode", "charge").lower()
    if mode not in {"charge", "discharge"}:
        raise ValueError("mode must be either 'charge' or 'discharge'")

    m_dot = float(config.get("mass_flow_rate", 1.0))

    pressures = config.get("pressures", {})
    p_low = float(pressures.get("P_low", 8.0e6))
    p_high = float(pressures.get("P_high", 20.0e6))

    temperatures = config.get("temperatures", {})
    t_source = float(temperatures.get("T_source", 700.0))
    t_sink = float(temperatures.get("T_sink", 300.0))

    dead_state = config.get("dead_state", {})
    T0 = float(dead_state.get("T0", 300.0))
    P0 = float(dead_state.get("P0", 101325.0))

    eps_recup = float(config.get("recuperator", {}).get("effectiveness", 1.0))
    eps_hot = float(config.get("heat_exchanger_hot", {}).get("effectiveness", 1.0))
    eps_cold = float(config.get("heat_exchanger_cold", {}).get("effectiveness", 1.0))

    eta_a = float(config.get("turbomachine_A", {}).get("eta_isentropic", 1.0))
    eta_b = float(config.get("turbomachine_B", {}).get("eta_isentropic", 1.0))

    solver_cfg = config.get("solver", {})
    max_iterations = int(solver_cfg.get("max_iterations", 100))
    tolerance = float(solver_cfg.get("tolerance", 0.01))
    h_tolerance = float(solver_cfg.get("enthalpy_tolerance", 10.0))
    relaxation = float(solver_cfg.get("relaxation", 0.5))

    if not 0.0 < relaxation <= 1.0:
        raise ValueError("solver.relaxation must be in (0, 1]")
    if p_low <= 0.0 or p_high <= 0.0 or p_high <= p_low:
        raise ValueError("Pressures must satisfy P_high > P_low > 0")

    p_state = _pressure_map(mode, p_low, p_high)
    mode_settings = _mode_settings(mode, config)

    h0 = PropsSI("H", "T", T0, "P", P0, fluid)
    s0 = PropsSI("S", "T", T0, "P", P0, fluid)

    if mode == "discharge":
        t2_guess = max(t_sink + 40.0, 320.0)
        t5_guess = max(t_source - 40.0, t_sink + 60.0)
    else:
        t2_guess = max(t_sink - 30.0, 260.0)
        t5_guess = max(t_source + 30.0, t_sink + 100.0)

    h2_guess = PropsSI("H", "T", t2_guess, "P", p_state[2], fluid)
    h5_guess = PropsSI("H", "T", t5_guess, "P", p_state[5], fluid)

    converged = False
    iteration = 0
    machine_a = None
    machine_b = None
    hot_hx = None
    cold_hx = None
    recuperator = None

    for iteration in range(1, max_iterations + 1):
        t2_in = PropsSI("T", "H", h2_guess, "P", p_state[2], fluid)
        t5_in = PropsSI("T", "H", h5_guess, "P", p_state[5], fluid)

        recuperator = Recuperator(
            fluid=fluid,
            T_hot_in=t5_in,
            P_hot=p_state[5],
            T_cold_in=t2_in,
            P_cold=p_state[2],
            m_dot=m_dot,
            effectiveness=eps_recup,
            T0=T0,
            P0=P0,
        )

        hot_hx = HeatExchanger(
            fluid=fluid,
            T_in=recuperator.T_cold_out,
            P=p_state[3],
            m_dot=m_dot,
            T_boundary=t_source,
            effectiveness=eps_hot,
            heat_into_stream=mode_settings["hot_hx_heat_into_stream"],
            T0=T0,
            P0=P0,
        )

        machine_b = ReversibleTurbomachine(
            fluid=fluid,
            T_in=hot_hx.T_out,
            P_in=p_state[4],
            P_out=p_state[5],
            m_dot=m_dot,
            mode=mode_settings["machine_b_mode"],
            eta_isentropic=eta_b,
            T0=T0,
            P0=P0,
        )

        cold_hx = HeatExchanger(
            fluid=fluid,
            T_in=recuperator.T_hot_out,
            P=p_state[6],
            m_dot=m_dot,
            T_boundary=t_sink,
            effectiveness=eps_cold,
            heat_into_stream=mode_settings["cold_hx_heat_into_stream"],
            T0=T0,
            P0=P0,
        )

        machine_a = ReversibleTurbomachine(
            fluid=fluid,
            T_in=cold_hx.T_out,
            P_in=p_state[1],
            P_out=p_state[2],
            m_dot=m_dot,
            mode=mode_settings["machine_a_mode"],
            eta_isentropic=eta_a,
            T0=T0,
            P0=P0,
        )

        t2_new = machine_a.T_out
        t5_new = machine_b.T_out
        h2_new = machine_a.h_out
        h5_new = machine_b.h_out

        temp_residual = max(abs(t2_new - t2_in), abs(t5_new - t5_in))
        h_residual = max(abs(h2_new - h2_guess), abs(h5_new - h5_guess))

        if temp_residual < tolerance or h_residual < h_tolerance:
            converged = True
            break

        h2_guess = (1.0 - relaxation) * h2_guess + relaxation * h2_new
        h5_guess = (1.0 - relaxation) * h5_guess + relaxation * h5_new

    if not converged:
        raise RuntimeError(
            "Cycle solver did not converge. "
            f"Reached max_iterations={max_iterations}, last state residuals remain above tolerance={tolerance}."
        )

    states: dict[int, StatePoint] = {
        1: _state_from_known(
            "Cold HX outlet / A inlet",
            cold_hx.T_out,
            p_state[1],
            cold_hx.h_out,
            cold_hx.s_out,
            h0,
            s0,
            T0,
        ),
        2: _state_from_known(
            "A outlet / Recuperator cold inlet",
            machine_a.T_out,
            p_state[2],
            machine_a.h_out,
            machine_a.s_out,
            h0,
            s0,
            T0,
        ),
        3: _state_from_known(
            "Recuperator cold outlet / Hot HX inlet",
            recuperator.T_cold_out,
            p_state[3],
            recuperator.h_cold_out,
            recuperator.s_cold_out,
            h0,
            s0,
            T0,
        ),
        4: _state_from_known(
            "Hot HX outlet / B inlet",
            hot_hx.T_out,
            p_state[4],
            hot_hx.h_out,
            hot_hx.s_out,
            h0,
            s0,
            T0,
        ),
        5: _state_from_known(
            "B outlet / Recuperator hot inlet",
            machine_b.T_out,
            p_state[5],
            machine_b.h_out,
            machine_b.s_out,
            h0,
            s0,
            T0,
        ),
        6: _state_from_known(
            "Recuperator hot outlet / Cold HX inlet",
            recuperator.T_hot_out,
            p_state[6],
            recuperator.h_hot_out,
            recuperator.s_hot_out,
            h0,
            s0,
            T0,
        ),
    }

    components: dict[str, object] = {
        "machine_A": machine_a,
        "machine_B": machine_b,
        "recuperator": recuperator,
        "hot_hx": hot_hx,
        "cold_hx": cold_hx,
    }

    work_into_system = machine_a.W_dot + machine_b.W_dot
    net_work_out = -work_into_system

    q_hot = hot_hx.Q_dot
    q_cold = cold_hx.Q_dot

    if mode == "discharge":
        cop_or_eta = net_work_out / q_hot if q_hot > 0.0 else math.nan
    else:
        heat_delivered_hot_store = -q_hot
        work_input = -net_work_out
        cop_or_eta = heat_delivered_hot_store / work_input if work_input > 0.0 else math.nan

    exergetic_efficiency = _compute_exergetic_efficiency(
        mode=mode,
        net_work_out=net_work_out,
        q_hot=q_hot,
        T0=T0,
        t_source=t_source,
    )

    if compute_isentropic_reference:
        reference_config = _build_isentropic_reference_config(config)
        reference_result = build_cycle(
            reference_config,
            compute_isentropic_reference=False,
        )
        isentropic_reference_net_work = reference_result.net_work
        cycle_isentropic_efficiency = _compute_cycle_isentropic_efficiency(
            mode=mode,
            actual_net_work=net_work_out,
            isentropic_reference_net_work=isentropic_reference_net_work,
        )
    else:
        isentropic_reference_net_work = math.nan
        cycle_isentropic_efficiency = math.nan

    total_exergy_destruction = (
        machine_a.exergy_destruction(T0)
        + machine_b.exergy_destruction(T0)
        + recuperator.exergy_destruction(T0)
        + hot_hx.exergy_destruction(T0)
        + cold_hx.exergy_destruction(T0)
    )

    return CycleResult(
        mode=mode,
        fluid=fluid,
        states=states,
        components=components,
        net_work=net_work_out,
        Q_hot=q_hot,
        Q_cold=q_cold,
        COP_or_eta=cop_or_eta,
        exergetic_efficiency=exergetic_efficiency,
        cycle_isentropic_efficiency=cycle_isentropic_efficiency,
        isentropic_reference_net_work=isentropic_reference_net_work,
        total_exergy_destruction=total_exergy_destruction,
        iterations=iteration,
        converged=converged,
    )


def print_cycle_result(result: CycleResult) -> None:
    metric_label = "COP_heating" if result.mode == "charge" else "eta_thermal"

    print("\n=== Reversible Recuperated Brayton Cycle ===")
    print(f"Mode: {result.mode}")
    print(f"Fluid: {result.fluid}")
    print(f"Converged: {result.converged} in {result.iterations} iterations")

    print("\nState Points")
    print("State | T [K]   | P [MPa] | h [kJ/kg] | s [kJ/kg-K] | psi [kJ/kg]")
    print("------|---------|---------|-----------|-------------|-----------")
    for index in range(1, 7):
        state = result.states[index]
        print(
            f"{index:>5d} | {state.T:>7.3f} | {state.P/1e6:>7.3f} | "
            f"{state.h/1e3:>9.3f} | {state.s/1e3:>11.5f} | {state.psi/1e3:>9.3f}"
        )

    machine_a = result.components["machine_A"]
    machine_b = result.components["machine_B"]
    recuperator = result.components["recuperator"]
    hot_hx = result.components["hot_hx"]
    cold_hx = result.components["cold_hx"]

    print("\nComponent Summary")
    print(
        f"machine_A: mode={machine_a.mode}, W_dot={machine_a.W_dot:.3f} W, "
        f"X_dest={machine_a.exergy_destruction():.3f} W"
    )
    print(
        f"machine_B: mode={machine_b.mode}, W_dot={machine_b.W_dot:.3f} W, "
        f"X_dest={machine_b.exergy_destruction():.3f} W"
    )
    print(
        f"recuperator: Q_dot={recuperator.Q_dot:.3f} W, "
        f"X_dest={recuperator.exergy_destruction():.3f} W"
    )
    print(
        f"hot_hx: Q_dot={hot_hx.Q_dot:.3f} W, "
        f"X_dest={hot_hx.exergy_destruction():.3f} W"
    )
    print(
        f"cold_hx: Q_dot={cold_hx.Q_dot:.3f} W, "
        f"X_dest={cold_hx.exergy_destruction():.3f} W"
    )

    print("\nCycle Totals")
    print(f"net_work (positive = power out): {result.net_work:.3f} W")
    print(f"Q_hot (positive = into fluid):   {result.Q_hot:.3f} W")
    print(f"Q_cold (positive = into fluid):  {result.Q_cold:.3f} W")
    print(f"{metric_label}: {result.COP_or_eta:.6f}")
    print(f"exergetic_efficiency: {result.exergetic_efficiency:.6f}")
    print(f"cycle_isentropic_efficiency: {result.cycle_isentropic_efficiency:.6f}")
    print(f"isentropic reference net_work: {result.isentropic_reference_net_work:.3f} W")
    print(f"total exergy destruction: {result.total_exergy_destruction:.3f} W")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Solve a reversible recuperated Brayton cycle with CoolProp"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parent / "config.json",
        help="Path to cycle configuration JSON file",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["charge", "discharge"],
        default=None,
        help="Optional mode override for config mode",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Save T-s and P-h diagrams for the current mode",
    )
    parser.add_argument(
        "--plot-both",
        action="store_true",
        help="Save T-s and P-h diagrams for both charge and discharge modes",
    )
    parser.add_argument(
        "--plot-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "plots",
        help="Directory where plot image files will be saved",
    )
    parser.add_argument(
        "--no-vapor-dome",
        action="store_true",
        help="Disable vapor-dome overlay on the cycle diagrams",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config, args.mode)
    result = build_cycle(config)
    print_cycle_result(result)

    if args.plot or args.plot_both:
        plot_paths: list[Path] = []
        plotter = BraytonCyclePlotter(
            output_dir=args.plot_dir,
            include_vapor_dome=not args.no_vapor_dome,
        )

        if args.plot_both:
            for mode_name in ["charge", "discharge"]:
                if mode_name == result.mode:
                    mode_result = result
                else:
                    mode_config = copy.deepcopy(config)
                    mode_config["mode"] = mode_name
                    mode_result = build_cycle(mode_config)
                plot_paths.append(plotter.save_cycle_diagrams(mode_result))
        else:
            plot_paths.append(plotter.save_cycle_diagrams(result))

        print("\nSaved plot files")
        for plot_path in plot_paths:
            print(f"- {plot_path}")


if __name__ == "__main__":
    main()