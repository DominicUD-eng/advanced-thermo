from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from CoolProp.CoolProp import PropsSI


class BraytonCyclePlotter:
    """Plotter for the reversible recuperated Brayton cycle application.

    The class is intentionally cycle-specific so plotting behavior can be tuned
    for this project without cluttering the solver script.
    """

    PROCESS_COLORS = [
        "tab:blue",
        "tab:cyan",
        "tab:red",
        "tab:purple",
        "tab:green",
        "tab:orange",
    ]

    TS_LABEL_OFFSETS = {
        "charge": {
            1: (8, 6),
            2: (-18, -14),
            3: (8, 8),
            4: (8, -16),
            5: (8, 8),
            6: (-18, 6),
        },
        "discharge": {
            1: (8, -14),
            2: (8, 8),
            3: (8, 8),
            4: (8, 8),
            5: (8, -14),
            6: (8, 8),
        },
    }

    PH_LABEL_OFFSETS = {
        "charge": {
            1: (8, 6),
            2: (-22, -10),
            3: (8, 8),
            4: (8, -16),
            5: (8, 8),
            6: (-22, 8),
        },
        "discharge": {
            1: (8, -14),
            2: (8, 8),
            3: (8, 8),
            4: (8, 8),
            5: (8, -14),
            6: (8, 8),
        },
    }

    def __init__(
        self,
        output_dir: Path,
        include_vapor_dome: bool = True,
        dpi: int = 220,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.include_vapor_dome = include_vapor_dome
        self.dpi = dpi
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_cycle_diagrams(self, result: Any) -> Path:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        process_paths = self._build_cycle_paths(result)
        vapor_dome = self._build_vapor_dome(result.fluid) if self.include_vapor_dome else None

        fig, (ax_ts, ax_ph) = plt.subplots(1, 2, figsize=(14.5, 7.0))
        fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.20, wspace=0.28)

        self._plot_vapor_dome(ax_ts, ax_ph, vapor_dome)
        self._plot_process_paths(ax_ts, ax_ph, process_paths)
        self._plot_state_points(ax_ts, ax_ph, result)
        self._style_axes(ax_ts, ax_ph, result, vapor_dome)

        handles, labels = ax_ts.get_legend_handles_labels()
        fig.legend(
            handles,
            labels,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.06),
            ncol=4,
            frameon=False,
        )
        fig.suptitle(
            f"Reversible Recuperated Brayton Cycle Diagrams ({result.mode.title()}, {result.fluid})",
            fontsize=14,
            y=0.96,
        )

        output_path = self.output_dir / f"{result.mode}_{result.fluid.lower()}_cycle_diagrams.png"
        fig.savefig(output_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def _build_cycle_paths(self, result: Any) -> list[tuple[str, dict[str, np.ndarray]]]:
        machine_a = result.components["machine_A"]
        machine_b = result.components["machine_B"]
        states = result.states
        fluid = result.fluid

        return [
            (
                f"A ({machine_a.mode})",
                self._sample_machine_path(
                    fluid=fluid,
                    start_state=states[1],
                    end_state=states[2],
                    mode=machine_a.mode,
                ),
            ),
            (
                "Recup cold",
                self._sample_isobaric_path(fluid, states[2], states[3]),
            ),
            (
                "Hot HX",
                self._sample_isobaric_path(fluid, states[3], states[4]),
            ),
            (
                f"B ({machine_b.mode})",
                self._sample_machine_path(
                    fluid=fluid,
                    start_state=states[4],
                    end_state=states[5],
                    mode=machine_b.mode,
                ),
            ),
            (
                "Recup hot",
                self._sample_isobaric_path(fluid, states[5], states[6]),
            ),
            (
                "Cold HX",
                self._sample_isobaric_path(fluid, states[6], states[1]),
            ),
        ]

    def _sample_isobaric_path(
        self,
        fluid: str,
        start_state: Any,
        end_state: Any,
        n_points: int = 80,
    ) -> dict[str, np.ndarray]:
        h_values = np.linspace(start_state.h, end_state.h, n_points, dtype=float)
        p_values = np.full(n_points, start_state.P, dtype=float)
        t_values = np.array(
            [PropsSI("T", "H", float(h), "P", start_state.P, fluid) for h in h_values],
            dtype=float,
        )
        s_values = np.array(
            [PropsSI("S", "H", float(h), "P", start_state.P, fluid) for h in h_values],
            dtype=float,
        )
        return self._enforce_endpoints(
            {"T": t_values, "P": p_values, "h": h_values, "s": s_values},
            start_state,
            end_state,
        )

    def _sample_machine_path(
        self,
        fluid: str,
        start_state: Any,
        end_state: Any,
        mode: str,
        n_points: int = 80,
    ) -> dict[str, np.ndarray]:
        p_values = np.linspace(start_state.P, end_state.P, n_points, dtype=float)

        if mode == "throttle":
            h_values = np.full(n_points, start_state.h, dtype=float)
            t_values = np.array(
                [PropsSI("T", "H", start_state.h, "P", float(p), fluid) for p in p_values],
                dtype=float,
            )
            s_values = np.array(
                [PropsSI("S", "H", start_state.h, "P", float(p), fluid) for p in p_values],
                dtype=float,
            )
            return self._enforce_endpoints(
                {"T": t_values, "P": p_values, "h": h_values, "s": s_values},
                start_state,
                end_state,
            )

        if abs(start_state.s - end_state.s) <= 1e-6:
            s_values = np.full(n_points, start_state.s, dtype=float)
            h_values = np.array(
                [PropsSI("H", "P", float(p), "S", start_state.s, fluid) for p in p_values],
                dtype=float,
            )
            t_values = np.array(
                [PropsSI("T", "P", float(p), "S", start_state.s, fluid) for p in p_values],
                dtype=float,
            )
            return self._enforce_endpoints(
                {"T": t_values, "P": p_values, "h": h_values, "s": s_values},
                start_state,
                end_state,
            )

        h_values = np.linspace(start_state.h, end_state.h, n_points, dtype=float)
        t_values = np.array(
            [
                PropsSI("T", "H", float(h), "P", float(p), fluid)
                for h, p in zip(h_values, p_values)
            ],
            dtype=float,
        )
        s_values = np.array(
            [
                PropsSI("S", "H", float(h), "P", float(p), fluid)
                for h, p in zip(h_values, p_values)
            ],
            dtype=float,
        )
        return self._enforce_endpoints(
            {"T": t_values, "P": p_values, "h": h_values, "s": s_values},
            start_state,
            end_state,
        )

    def _enforce_endpoints(
        self,
        path: dict[str, np.ndarray],
        start_state: Any,
        end_state: Any,
    ) -> dict[str, np.ndarray]:
        path["T"][0] = start_state.T
        path["P"][0] = start_state.P
        path["h"][0] = start_state.h
        path["s"][0] = start_state.s
        path["T"][-1] = end_state.T
        path["P"][-1] = end_state.P
        path["h"][-1] = end_state.h
        path["s"][-1] = end_state.s
        return path

    def _build_vapor_dome(self, fluid: str, n_points: int = 300) -> dict[str, np.ndarray] | None:
        try:
            t_triple = float(PropsSI("Ttriple", fluid))
            t_critical = float(PropsSI("Tcrit", fluid))
        except ValueError:
            return None

        if t_critical <= t_triple:
            return None

        t_values = np.linspace(t_triple + 1e-3, t_critical - 1e-3, n_points, dtype=float)
        valid_rows: list[tuple[float, float, float, float, float, float]] = []

        for temperature in t_values:
            try:
                p_sat = PropsSI("P", "T", float(temperature), "Q", 0, fluid)
                s_liq = PropsSI("S", "T", float(temperature), "Q", 0, fluid)
                s_vap = PropsSI("S", "T", float(temperature), "Q", 1, fluid)
                h_liq = PropsSI("H", "T", float(temperature), "Q", 0, fluid)
                h_vap = PropsSI("H", "T", float(temperature), "Q", 1, fluid)
                valid_rows.append((temperature, p_sat, s_liq, s_vap, h_liq, h_vap))
            except ValueError:
                continue

        if len(valid_rows) < 2:
            return None

        dome_array = np.array(valid_rows, dtype=float)
        return {
            "T": dome_array[:, 0],
            "P": dome_array[:, 1],
            "s_liq": dome_array[:, 2],
            "s_vap": dome_array[:, 3],
            "h_liq": dome_array[:, 4],
            "h_vap": dome_array[:, 5],
        }

    def _plot_vapor_dome(self, ax_ts: Any, ax_ph: Any, vapor_dome: dict[str, np.ndarray] | None) -> None:
        if vapor_dome is None:
            return

        ax_ts.fill_betweenx(
            vapor_dome["T"],
            vapor_dome["s_liq"] / 1e3,
            vapor_dome["s_vap"] / 1e3,
            color="0.92",
            alpha=0.6,
            zorder=0,
        )
        ax_ts.plot(
            vapor_dome["s_liq"] / 1e3,
            vapor_dome["T"],
            color="0.25",
            linestyle="--",
            linewidth=1.2,
            label="Vapor dome",
        )
        ax_ts.plot(
            vapor_dome["s_vap"] / 1e3,
            vapor_dome["T"],
            color="0.25",
            linestyle="--",
            linewidth=1.2,
        )

        ax_ph.fill_betweenx(
            vapor_dome["P"] / 1e6,
            vapor_dome["h_liq"] / 1e3,
            vapor_dome["h_vap"] / 1e3,
            color="0.92",
            alpha=0.6,
            zorder=0,
        )
        ax_ph.plot(
            vapor_dome["h_liq"] / 1e3,
            vapor_dome["P"] / 1e6,
            color="0.25",
            linestyle="--",
            linewidth=1.2,
            label="Vapor dome",
        )
        ax_ph.plot(
            vapor_dome["h_vap"] / 1e3,
            vapor_dome["P"] / 1e6,
            color="0.25",
            linestyle="--",
            linewidth=1.2,
        )

    def _plot_process_paths(
        self,
        ax_ts: Any,
        ax_ph: Any,
        process_paths: list[tuple[str, dict[str, np.ndarray]]],
    ) -> None:
        for color, (label, path) in zip(self.PROCESS_COLORS, process_paths):
            ax_ts.plot(path["s"] / 1e3, path["T"], color=color, linewidth=2.0, label=label)
            ax_ph.plot(path["h"] / 1e3, path["P"] / 1e6, color=color, linewidth=2.0, label=label)
            self._add_direction_arrow(ax_ts, path["s"] / 1e3, path["T"], color)
            self._add_direction_arrow(ax_ph, path["h"] / 1e3, path["P"] / 1e6, color)

    def _plot_state_points(self, ax_ts: Any, ax_ph: Any, result: Any) -> None:
        ts_state_x = np.array([result.states[index].s / 1e3 for index in range(1, 7)], dtype=float)
        ts_state_y = np.array([result.states[index].T for index in range(1, 7)], dtype=float)
        ph_state_x = np.array([result.states[index].h / 1e3 for index in range(1, 7)], dtype=float)
        ph_state_y = np.array([result.states[index].P / 1e6 for index in range(1, 7)], dtype=float)

        ax_ts.scatter(ts_state_x, ts_state_y, color="black", s=28, zorder=5)
        ax_ph.scatter(ph_state_x, ph_state_y, color="black", s=28, zorder=5)

        ts_offsets = self.TS_LABEL_OFFSETS.get(result.mode, {})
        ph_offsets = self.PH_LABEL_OFFSETS.get(result.mode, {})
        label_box = {"boxstyle": "round,pad=0.16", "fc": "white", "ec": "none", "alpha": 0.85}

        for index in range(1, 7):
            ts_offset = ts_offsets.get(index, (6, 6))
            ph_offset = ph_offsets.get(index, (6, 6))
            ax_ts.annotate(
                str(index),
                (result.states[index].s / 1e3, result.states[index].T),
                xytext=ts_offset,
                textcoords="offset points",
                bbox=label_box,
            )
            ax_ph.annotate(
                str(index),
                (result.states[index].h / 1e3, result.states[index].P / 1e6),
                xytext=ph_offset,
                textcoords="offset points",
                bbox=label_box,
            )

    def _style_axes(
        self,
        ax_ts: Any,
        ax_ph: Any,
        result: Any,
        vapor_dome: dict[str, np.ndarray] | None,
    ) -> None:
        ax_ts.set_title(f"{result.mode.title()} cycle on T-s", pad=10)
        ax_ts.set_xlabel("Entropy [kJ/(kg·K)]")
        ax_ts.set_ylabel("Temperature [K]")
        ax_ts.grid(True, alpha=0.3)

        ax_ph.set_title(f"{result.mode.title()} cycle on P-h", pad=10)
        ax_ph.set_xlabel("Enthalpy [kJ/kg]")
        ax_ph.set_ylabel("Pressure [MPa]")
        ax_ph.set_yscale("log")
        ax_ph.grid(True, which="both", alpha=0.3)

        if vapor_dome is not None:
            ph_state_y = np.array([result.states[index].P / 1e6 for index in range(1, 7)], dtype=float)
            p_values_mpa = np.concatenate([ph_state_y, vapor_dome["P"] / 1e6])
            ax_ph.set_ylim(max(0.05, np.min(p_values_mpa) * 0.8), np.max(p_values_mpa) * 1.2)

    def _add_direction_arrow(self, ax: Any, x_values: np.ndarray, y_values: np.ndarray, color: str) -> None:
        if len(x_values) < 3:
            return
        mid_index = len(x_values) // 2
        ax.annotate(
            "",
            xy=(x_values[mid_index], y_values[mid_index]),
            xytext=(x_values[mid_index - 2], y_values[mid_index - 2]),
            arrowprops={"arrowstyle": "->", "lw": 1.4, "color": color},
        )
