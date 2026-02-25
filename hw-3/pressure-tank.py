#!/usr/bin/env python3
"""
PressureVessel — rigid insulated tank filling model for Q3.

Usage:
    python PressureVessel.py
"""

from CoolProp.CoolProp import PropsSI
from scipy.integrate import quad


class PressureVessel:
    """Rigid, insulated pressure vessel being filled from a supply line."""

    def __init__(self, fluid, V, P_i, T_i, P_in, T_in, t_final, m_dot_func):
        """
        Parameters
        ----------
        fluid      : str       – CoolProp fluid name (e.g. "Nitrogen")
        V          : float     – tank volume in m³
        P_i        : float     – initial tank pressure in Pa
        T_i        : float     – initial tank temperature in K
        P_in       : float     – supply line pressure in Pa
        T_in       : float     – supply line temperature in K
        t_final    : float     – fill duration in seconds
        m_dot_func : callable  – mass flow rate function m_dot(t) in kg/s
        """
        self.fluid = fluid
        self.V = V
        self.P_i = P_i
        self.T_i = T_i
        self.P_in = P_in
        self.T_in = T_in
        self.t_final = t_final
        self.m_dot = m_dot_func

        # initial state
        self.rho_i = PropsSI('D', 'T', T_i, 'P', P_i, fluid)
        self.m_i = self.rho_i * V

    def mass_added(self):
        """Total mass entering the tank: integral of m_dot(t) from 0 to t_final."""
        delta_m, _ = quad(self.m_dot, 0, self.t_final)
        return delta_m

    # --- Part B helper methods ---
    def dead_state_properties(self):
        """Returns (u_0, s_0, rho_0) at the dead state."""
        T0 = 300.0    # K
        P0 = 101325.0 # Pa
        u0 = PropsSI('U', 'T', T0, 'P', P0, self.fluid)
        s0 = PropsSI('S', 'T', T0, 'P', P0, self.fluid)
        rho0 = PropsSI('D', 'T', T0, 'P', P0, self.fluid)
        return u0, s0, rho0

    def stored_exergy_initial(self):
        """Non-flow exergy of initial tank contents (J)."""
        T0 = 300.0
        P0 = 101325.0
        u0, s0, rho0 = self.dead_state_properties()

        u_i = self.initial_internal_energy()
        s_i = PropsSI('S', 'T', self.T_i, 'P', self.P_i, self.fluid)
        v_i = 1.0 / self.rho_i     # specific volume of initial state
        v_0 = 1.0 / rho0           # specific volume at dead state

        xi = self.m_i * ((u_i - u0) + P0 * (v_i - v_0) - T0 * (s_i - s0))
        return xi

    def stored_exergy_final(self):
        """Non-flow exergy of final tank contents (J)."""
        T0 = 300.0
        P0 = 101325.0
        u0, s0, rho0 = self.dead_state_properties()

        u_f = self.final_internal_energy()
        s_f = PropsSI('S', 'U', u_f, 'D', self.final_density(), self.fluid)
        v_f = 1.0 / self.final_density()
        v_0 = 1.0 / rho0

        m_f = self.final_mass()
        xi = m_f * ((u_f - u0) + P0 * (v_f - v_0) - T0 * (s_f - s0))
        return xi

    # --- Part C helper methods ---
    def inlet_entropy(self):
        """Specific entropy of the supply stream."""
        return PropsSI('S', 'T', self.T_in, 'P', self.P_in, self.fluid)

    def inlet_flow_exergy(self):
        """Specific flow exergy of the supply stream (J/kg).
        
        psi_in = (h_in - h_0) - T_0 * (s_in - s_0)
        """
        T0 = 300.0
        P0 = 101325.0
        u0, s0, rho0 = self.dead_state_properties()
        h0 = PropsSI('H', 'T', T0, 'P', P0, self.fluid)

        h_in = self.inlet_enthalpy()
        s_in = self.inlet_entropy()

        return (h_in - h0) - T0 * (s_in - s0)

    def exergy_destroyed(self):
        """Total exergy destroyed during the filling process (J).
        
        X_dest = psi_in * delta_m - (Xi_final - Xi_initial)
        """
        x_in_total = self.inlet_flow_exergy() * self.mass_added()
        delta_xi = self.stored_exergy_final() - self.stored_exergy_initial()
        return x_in_total - delta_xi

    def final_mass(self):
        """Final mass in the tank: m_i + delta_m."""
        return self.m_i + self.mass_added()

    def inlet_enthalpy(self):
        """Specific enthalpy of the supply stream (constant T_in, P_in)."""
        return PropsSI('H', 'T', self.T_in, 'P', self.P_in, self.fluid)

    def initial_internal_energy(self):
        """Specific internal energy of the initial tank contents."""
        return PropsSI('U', 'T', self.T_i, 'P', self.P_i, self.fluid)

    def final_internal_energy(self):
        """Specific internal energy of the final tank contents from energy balance.
        
        m_f * u_f = m_i * u_i + h_in * delta_m
        """
        m_i = self.m_i
        u_i = self.initial_internal_energy()
        h_in = self.inlet_enthalpy()
        delta_m = self.mass_added()
        m_f = self.final_mass()
        return (m_i * u_i + h_in * delta_m) / m_f

    def final_density(self):
        """Final density in the tank: m_f / V."""
        return self.final_mass() / self.V

    def final_temperature(self):
        """Final temperature from CoolProp inversion using u_f and rho_f."""
        return PropsSI('T', 'U', self.final_internal_energy(),
                       'D', self.final_density(), self.fluid)

    def final_pressure(self):
        """Final pressure from CoolProp inversion using u_f and rho_f."""
        return PropsSI('P', 'U', self.final_internal_energy(),
                       'D', self.final_density(), self.fluid)


if __name__ == '__main__':
    fluid = "Nitrogen"
    m_dot_func = lambda t: 0.02 * (1 - t / 600)

    tank = PressureVessel(
        fluid=fluid,
        V=0.8,
        P_i=150e3,
        T_i=310.0,
        P_in=1.8e6,
        T_in=420.0,
        t_final=600.0,
        m_dot_func=m_dot_func
    )

    print("=== PART A ===")
    print(f"Initial mass:           {tank.m_i:.4f} kg")
    print(f"Mass added:             {tank.mass_added():.4f} kg")
    print(f"Final mass:             {tank.final_mass():.4f} kg")
    print(f"Inlet enthalpy:         {tank.inlet_enthalpy():.2f} J/kg")
    print(f"Initial specific u:     {tank.initial_internal_energy():.2f} J/kg")
    print(f"Final specific u:       {tank.final_internal_energy():.2f} J/kg")
    print(f"Final temperature:      {tank.final_temperature():.2f} K")
    print(f"Final pressure:         {tank.final_pressure()/1e3:.2f} kPa")

    # Part B: stored exergy
    print("\n=== PART B ===")
    print(f"Stored exergy (initial): {tank.stored_exergy_initial()/1e3:.4f} kJ")
    print(f"Stored exergy (final):   {tank.stored_exergy_final()/1e3:.4f} kJ")

    # Part C: total exergy destroyed
    print("\n=== PART C ===")
    print(f"Inlet flow exergy:      {tank.inlet_flow_exergy()/1e3:.4f} kJ/kg")
    print(f"Total exergy in:        {tank.inlet_flow_exergy() * tank.mass_added()/1e3:.4f} kJ")
    print(f"Exergy destroyed:       {tank.exergy_destroyed()/1e3:.4f} kJ")
