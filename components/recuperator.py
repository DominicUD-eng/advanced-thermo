from __future__ import annotations

from CoolProp.CoolProp import PropsSI


class Recuperator:
    """Two-stream internal heat exchanger (recuperator) with equal mass flow on both sides.

    Heat transfer is computed with an enthalpy-based effectiveness model to avoid
    constant-Cp assumptions that are inaccurate for sCO2 near the critical region.
    """

    def __init__(
        self,
        fluid: str,
        T_hot_in: float,
        P_hot: float,
        T_cold_in: float,
        P_cold: float,
        m_dot: float,
        effectiveness: float = 1.0,
        T0: float = 300.0,
        P0: float = 101325.0,
    ) -> None:
        if not 0.0 <= effectiveness <= 1.0:
            raise ValueError("effectiveness must be within [0, 1]")

        self.fluid = fluid
        self.T_hot_in = T_hot_in
        self.P_hot = P_hot
        self.T_cold_in = T_cold_in
        self.P_cold = P_cold
        self.m_dot = m_dot
        self.effectiveness = effectiveness
        self.T0 = T0
        self.P0 = P0

        self.h_hot_in = PropsSI("H", "T", self.T_hot_in, "P", self.P_hot, self.fluid)
        self.s_hot_in = PropsSI("S", "T", self.T_hot_in, "P", self.P_hot, self.fluid)
        self.h_cold_in = PropsSI("H", "T", self.T_cold_in, "P", self.P_cold, self.fluid)
        self.s_cold_in = PropsSI("S", "T", self.T_cold_in, "P", self.P_cold, self.fluid)

        h_hot_at_cold_in = PropsSI("H", "T", self.T_cold_in, "P", self.P_hot, self.fluid)
        h_cold_at_hot_in = PropsSI("H", "T", self.T_hot_in, "P", self.P_cold, self.fluid)

        q_hot_cap_specific = max(0.0, self.h_hot_in - h_hot_at_cold_in)
        q_cold_cap_specific = max(0.0, h_cold_at_hot_in - self.h_cold_in)
        q_max_specific = min(q_hot_cap_specific, q_cold_cap_specific)

        self.Q_max = self.m_dot * q_max_specific
        self.Q_dot = self.effectiveness * self.Q_max

        self.h_hot_out = self.h_hot_in - self.Q_dot / self.m_dot
        self.h_cold_out = self.h_cold_in + self.Q_dot / self.m_dot

        self.T_hot_out = PropsSI("T", "H", self.h_hot_out, "P", self.P_hot, self.fluid)
        self.s_hot_out = PropsSI("S", "H", self.h_hot_out, "P", self.P_hot, self.fluid)
        self.T_cold_out = PropsSI("T", "H", self.h_cold_out, "P", self.P_cold, self.fluid)
        self.s_cold_out = PropsSI("S", "H", self.h_cold_out, "P", self.P_cold, self.fluid)

    def exergy_destruction(self, T0: float | None = None) -> float:
        t_ref = self.T0 if T0 is None else T0
        x_dest = t_ref * self.m_dot * (
            (self.s_hot_out - self.s_hot_in) + (self.s_cold_out - self.s_cold_in)
        )
        return max(0.0, x_dest)

    def __repr__(self) -> str:
        return (
            f"Recuperator(fluid={self.fluid}, eps={self.effectiveness:.3f})\n"
            f"  Hot : Tin={self.T_hot_in:.3f} K -> Tout={self.T_hot_out:.3f} K @ {self.P_hot/1e6:.3f} MPa\n"
            f"  Cold: Tin={self.T_cold_in:.3f} K -> Tout={self.T_cold_out:.3f} K @ {self.P_cold/1e6:.3f} MPa\n"
            f"  Qdot={self.Q_dot:.2f} W"
        )