#!/usr/bin/env python3
"""Throttling and flash-separator demonstration for Q2 Part A.

Usage: python fluid-separator.py (no arguments)

Creates a Throttle object for propane and prints inlet/outlet enthalpies,
quality, and split mass flows.
"""

from CoolProp.CoolProp import PropsSI


class Throttle:
    """Simple isenthalpic throttling valve model."""

    def __init__(self, fluid, T_in, P_in, P_out, m_dot):
        self.fluid = fluid
        self.T_in = T_in
        self.P_in = P_in
        self.P_out = P_out
        self.m_dot = m_dot

        # inlet enthalpy and entropy
        self.h_in = PropsSI('H', 'T', T_in, 'P', P_in, fluid)
        self.s_in = PropsSI('S', 'T', T_in, 'P', P_in, fluid)
        # isenthalpic process
        self.h_out = self.h_in
        self.s_out = PropsSI('S', 'H', self.h_out, 'P', P_out, fluid)
        # quality at outlet pressure
        self.x_out = PropsSI('Q', 'H', self.h_out, 'P', P_out, fluid)

    def exergy_destruction(self, T0):
        """Gouy-Stodola exergy loss for throttle (adiabatic, no work)."""
        s_gen = self.m_dot * (self.s_out - self.s_in)
        return T0 * s_gen

    def __repr__(self):
        return (f"Throttle({self.fluid}, T_in={self.T_in}K, P_in={self.P_in}Pa, "
                f"P_out={self.P_out}Pa, m_dot={self.m_dot}kg/s)\n"
                f"   h_in={self.h_in:.2f} J/kg, x_out={self.x_out:.4f}")


class FlashSeparator:
    """Separates a two-phase mixture into saturated vapor and saturated liquid."""

    def __init__(self, fluid, P, x_in, m_dot, s_in=None):
        self.fluid = fluid
        self.P = P
        self.x_in = x_in
        self.m_dot = m_dot

        # inlet entropy optionally provided (from throttle)
        self.s_in = s_in

        # split fractions
        self.m_dot_vap = x_in * m_dot
        self.m_dot_liq = (1 - x_in) * m_dot

        # saturated vapor outlet (Q=1)
        self.h_vap = PropsSI('H', 'P', P, 'Q', 1, fluid)
        self.s_vap = PropsSI('S', 'P', P, 'Q', 1, fluid)
        self.T_vap = PropsSI('T', 'P', P, 'Q', 1, fluid)

        # saturated liquid outlet (Q=0)
        self.h_liq = PropsSI('H', 'P', P, 'Q', 0, fluid)
        self.s_liq = PropsSI('S', 'P', P, 'Q', 0, fluid)
        self.T_liq = PropsSI('T', 'P', P, 'Q', 0, fluid)

    def exergy_destruction(self, T0):
        # entropy of inlet mixture
        if self.s_in is None:
            # compute from mixture enthalpy and pressure
            h_mix = PropsSI('H', 'P', self.P, 'Q', self.x_in, self.fluid)
            self.s_in = PropsSI('S', 'H', h_mix, 'P', self.P, self.fluid)
        s_gen = (self.m_dot_vap * self.s_vap + self.m_dot_liq * self.s_liq) - (self.m_dot * self.s_in)
        return T0 * s_gen

    def __repr__(self):
        return (f"FlashSeparator @ {self.P/1e6:.2f} MPa\n"
                f"  Vapor: m_dot={self.m_dot_vap:.4f} kg/s, "
                f"h={self.h_vap:.2f} J/kg, T={self.T_vap:.2f} K\n"
                f"  Liquid: m_dot={self.m_dot_liq:.4f} kg/s, "
                f"h={self.h_liq:.2f} J/kg, T={self.T_liq:.2f} K")


class HeatExchanger:
    """Isobaric heat exchanger — heats or cools a single stream to a target temperature."""

    def exergy_destruction(self, T0, T_boundary=None):
        """Calculate exergy destruction using entropy balance with heat term.

        T_boundary defaults to T0 if not supplied.
        """
        if T_boundary is None:
            T_boundary = T0
        s_gen = self.m_dot * (self.s_out - self.s_in) - self.q_dot / T_boundary
        return T0 * s_gen

    def __init__(self, fluid, h_in, s_in, P, T_out, m_dot):
        self.fluid = fluid
        self.P = P
        self.m_dot = m_dot

        # inlet state (passed in from upstream component)
        self.h_in = h_in
        self.s_in = s_in

        # outlet state at target temperature
        self.T_out = T_out
        self.h_out = PropsSI('H', 'T', T_out, 'P', P, fluid)
        self.s_out = PropsSI('S', 'T', T_out, 'P', P, fluid)

        # heat transfer rate: positive = heat added, negative = heat rejected
        self.q_dot = m_dot * (self.h_out - self.h_in)

    def __repr__(self):
        label = "heating" if self.q_dot > 0 else "cooling"
        return (f"HeatExchanger ({label}) @ {self.P/1e6:.2f} MPa\n"
                f"  h_in={self.h_in:.2f}, h_out={self.h_out:.2f} J/kg\n"
                f"  Q_dot={self.q_dot:.2f} W ({self.q_dot/1e3:.2f} kW)")


class Mixer:
    """Adiabatic constant-pressure mixer of two streams."""

    def exergy_destruction(self, T0):
        s_gen = (self.m_dot_out * self.s_out
                 - self.m_dot_1 * self.s_1
                 - self.m_dot_2 * self.s_2)
        return T0 * s_gen

    def __init__(self, fluid, h_1, s_1, m_dot_1, h_2, s_2, m_dot_2, P):
        self.fluid = fluid
        self.P = P

        self.h_1, self.s_1, self.m_dot_1 = h_1, s_1, m_dot_1
        self.h_2, self.s_2, self.m_dot_2 = h_2, s_2, m_dot_2

        # total outlet flow
        self.m_dot_out = m_dot_1 + m_dot_2

        # energy balance: adiabatic, no work
        self.h_out = (m_dot_1 * h_1 + m_dot_2 * h_2) / self.m_dot_out

        # outlet state
        self.T_out = PropsSI('T', 'H', self.h_out, 'P', P, fluid)
        self.s_out = PropsSI('S', 'H', self.h_out, 'P', P, fluid)

    def __repr__(self):
        return (f"Mixer @ {self.P/1e6:.2f} MPa\n"
                f"  m_dot_out={self.m_dot_out:.4f} kg/s\n"
                f"  h_out={self.h_out:.2f} J/kg, T_out={self.T_out:.2f} K")


if __name__ == '__main__':
    fluid = "Propane"
    m_dot = 1.5       # kg/s
    T1    = 330.0     # K
    P1    = 2.5e6     # Pa
    P2    = 0.65e6    # Pa

    # Part A
    valve     = Throttle(fluid, T1, P1, P2, m_dot)
    separator = FlashSeparator(fluid, P2, valve.x_out, m_dot, s_in=valve.s_out)

    print("=== PART A ===")
    print(f"Quality after throttling: {valve.x_out:.4f}")
    print(separator)

    # Part B
    vapor_cooler  = HeatExchanger(fluid, separator.h_vap, separator.s_vap,
                                  P2, T_out=305.0, m_dot=separator.m_dot_vap)
    liquid_heater = HeatExchanger(fluid, separator.h_liq, separator.s_liq,
                                  P2, T_out=345.0, m_dot=separator.m_dot_liq)

    print("\n=== PART B ===")
    print(f"Vapor cooler  Q_dot = {vapor_cooler.q_dot/1e3:.2f} kW  (rejection)")
    print(f"Liquid heater Q_dot = {liquid_heater.q_dot/1e3:.2f} kW  (delivery)")

    # Mixer (for Part C later)
    mixer = Mixer(fluid,
                  vapor_cooler.h_out, vapor_cooler.s_out, separator.m_dot_vap,
                  liquid_heater.h_out, liquid_heater.s_out, separator.m_dot_liq,
                  P2)

    print(f"\nMixer outlet: T={mixer.T_out:.2f} K, m_dot={mixer.m_dot_out:.4f} kg/s")

    # Part C: exergy destruction
    print("\n=== PART C ===")
    T0 = 300.0
    components = {
        "Throttle":        valve.exergy_destruction(T0),
        "Flash Separator": separator.exergy_destruction(T0),
        "Vapor Cooler":    vapor_cooler.exergy_destruction(T0, T_boundary=T0),
        "Liquid Heater":   liquid_heater.exergy_destruction(T0, T_boundary=450.0),
        "Mixer":           mixer.exergy_destruction(T0),
    }
    total_xd = 0.0
    for name, xd in components.items():
        print(f"  {name:20s}: X_dest = {xd/1e3:.4f} kW")
        total_xd += xd
    print(f"  {'TOTAL':20s}: X_dest = {total_xd/1e3:.4f} kW")
    dominant = max(components, key=components.get)
    print(f"\nDominant component: {dominant}")
