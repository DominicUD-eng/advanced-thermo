from __future__ import annotations

from CoolProp.CoolProp import PropsSI


class HeatExchanger:
    """Single-stream HX exchanging heat with a boundary reservoir at fixed temperature.

    Sign convention:
    - Q_dot > 0 means heat into the fluid stream
    - Q_dot < 0 means heat rejected by the fluid stream
    """

    def __init__(
        self,
        fluid: str,
        T_in: float,
        P: float,
        m_dot: float,
        T_boundary: float,
        effectiveness: float = 1.0,
        heat_into_stream: bool = True,
        T0: float = 300.0,
        P0: float = 101325.0,
    ) -> None:
        if not 0.0 <= effectiveness <= 1.0:
            raise ValueError("effectiveness must be within [0, 1]")

        self.fluid = fluid
        self.T_in = T_in
        self.P = P
        self.m_dot = m_dot
        self.T_boundary = T_boundary
        self.effectiveness = effectiveness
        self.heat_into_stream = heat_into_stream
        self.T0 = T0
        self.P0 = P0

        self.h_in = PropsSI("H", "T", self.T_in, "P", self.P, self.fluid)
        self.s_in = PropsSI("S", "T", self.T_in, "P", self.P, self.fluid)

        self.h_boundary = PropsSI("H", "T", self.T_boundary, "P", self.P, self.fluid)
        self.Q_max = self.m_dot * abs(self.h_boundary - self.h_in)

        direction = 1.0 if self.heat_into_stream else -1.0
        self.Q_dot = direction * self.effectiveness * self.Q_max

        self.h_out = self.h_in + self.Q_dot / self.m_dot
        self.T_out = PropsSI("T", "H", self.h_out, "P", self.P, self.fluid)
        self.s_out = PropsSI("S", "H", self.h_out, "P", self.P, self.fluid)

    def exergy_destruction(self, T0: float | None = None) -> float:
        t_ref = self.T0 if T0 is None else T0
        s_gen = self.m_dot * (self.s_out - self.s_in) - self.Q_dot / self.T_boundary
        x_dest = t_ref * s_gen
        return max(0.0, x_dest)

    def __repr__(self) -> str:
        return (
            f"HeatExchanger(fluid={self.fluid}, eps={self.effectiveness:.3f}, "
            f"Qdot={self.Q_dot:.2f} W, Tb={self.T_boundary:.2f} K)"
        )