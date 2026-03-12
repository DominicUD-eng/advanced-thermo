from __future__ import annotations

from CoolProp.CoolProp import PropsSI


class ReversibleTurbomachine:
    """Single-stream turbomachine with reversible and throttling modes.

    Sign convention for work:
    - Positive work means work INTO the fluid stream (compressor convention)
    - Negative work means work OUT of the fluid stream (expander convention)
    """

    VALID_MODES = {"compressor", "expander", "throttle"}

    def __init__(
        self,
        fluid: str,
        T_in: float,
        P_in: float,
        P_out: float,
        m_dot: float,
        mode: str,
        eta_isentropic: float = 1.0,
        T0: float = 300.0,
        P0: float = 101325.0,
    ) -> None:
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}'. Valid modes: {sorted(self.VALID_MODES)}")
        if eta_isentropic <= 0.0:
            raise ValueError("eta_isentropic must be > 0")
        if mode in {"compressor", "expander"} and eta_isentropic > 1.0:
            raise ValueError("eta_isentropic must be <= 1.0 for compressor/expander modes")

        self.fluid = fluid
        self.T_in = T_in
        self.P_in = P_in
        self.P_out = P_out
        self.m_dot = m_dot
        self.mode = mode
        self.eta_isentropic = eta_isentropic
        self.T0 = T0
        self.P0 = P0

        self.h_in = PropsSI("H", "T", self.T_in, "P", self.P_in, self.fluid)
        self.s_in = PropsSI("S", "T", self.T_in, "P", self.P_in, self.fluid)

        self.h_out_s = PropsSI("H", "P", self.P_out, "S", self.s_in, self.fluid)

        if self.mode == "compressor":
            self.h_out = self.h_in + (self.h_out_s - self.h_in) / self.eta_isentropic
        elif self.mode == "expander":
            self.h_out = self.h_in - self.eta_isentropic * (self.h_in - self.h_out_s)
        else:
            self.h_out = self.h_in

        self.T_out = PropsSI("T", "H", self.h_out, "P", self.P_out, self.fluid)
        self.s_out = PropsSI("S", "H", self.h_out, "P", self.P_out, self.fluid)

        if self.mode == "throttle":
            self.w_specific = 0.0
        else:
            self.w_specific = self.h_out - self.h_in
        self.W_dot = self.m_dot * self.w_specific

        self.h0 = PropsSI("H", "T", self.T0, "P", self.P0, self.fluid)
        self.s0 = PropsSI("S", "T", self.T0, "P", self.P0, self.fluid)

    def specific_flow_exergy(self, h: float, s: float, T0: float | None = None) -> float:
        t_ref = self.T0 if T0 is None else T0
        return (h - self.h0) - t_ref * (s - self.s0)

    def exergy_destruction(self, T0: float | None = None) -> float:
        t_ref = self.T0 if T0 is None else T0
        x_dest = t_ref * self.m_dot * (self.s_out - self.s_in)
        return max(0.0, x_dest)

    def summary(self) -> str:
        return (
            f"ReversibleTurbomachine(mode={self.mode}, fluid={self.fluid})\n"
            f"  Inlet : T={self.T_in:.3f} K, P={self.P_in/1e6:.3f} MPa, "
            f"h={self.h_in:.2f} J/kg, s={self.s_in:.4f} J/kg/K\n"
            f"  Outlet_s: h_s={self.h_out_s:.2f} J/kg\n"
            f"  Outlet : T={self.T_out:.3f} K, P={self.P_out/1e6:.3f} MPa, "
            f"h={self.h_out:.2f} J/kg, s={self.s_out:.4f} J/kg/K\n"
            f"  w={self.w_specific:.2f} J/kg, Wdot={self.W_dot:.2f} W"
        )

    def __repr__(self) -> str:
        return self.summary()