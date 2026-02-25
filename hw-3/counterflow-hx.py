#!/usr/bin/env python3
"""Simple counterflow heat-exchanger checks using CoolProp.

Usage: python counterflow-hx.py [--m_h <kg/s> --m_c <kg/s>]

Hot- and cold-side mass flows default to the Part A values (2.0 and
1.2 kg/s); the program computes the outlet states for the two pinch
scenarios and evaluates feasibility, boundary temperatures, exergy
creation/destruction, and an exergetic efficiency.

Requires CoolProp (pip install CoolProp).
"""

import argparse
import sys

try:
    from CoolProp.CoolProp import PropsSI
except Exception as e:
    print("CoolProp is required. Install with: pip install CoolProp")
    raise


def Jperkg_to_kJperkg(x):
    return x / 1000.0


def safe_T_from_h(h, P, fluid):
    try:
        T = PropsSI('T', 'H', h, 'P', P, fluid)
        return T
    except Exception:
        return None


def compute_boundary_temperatures(T_h_in, T_h_out, P_h,
                                   T_c_in, T_c_out, P_c,
                                   m_dot_h, m_dot_c,
                                   fluid_h='CO2', fluid_c='Water'):
    """
    Compute thermodynamic-mean boundary temperatures and stream properties.

    Returns:
        T_b_H: hot-stream boundary temperature (K)
        T_b_C: cold-stream boundary temperature (K)
        Q_dot: heat transfer rate (W, positive)
        h_h_in, h_h_out, s_h_in, s_h_out: hot-side enthalpies/entropies
        h_c_in, h_c_out, s_c_in, s_c_out: cold-side enthalpies/entropies

    The returned enthalpy/entropy values let callers avoid repeating
    CoolProp lookups when computing exergy or efficiencies.
    """
    # look up properties
    h_h_in  = PropsSI('H', 'T', T_h_in,  'P', P_h, fluid_h)
    h_h_out = PropsSI('H', 'T', T_h_out, 'P', P_h, fluid_h)
    s_h_in  = PropsSI('S', 'T', T_h_in,  'P', P_h, fluid_h)
    s_h_out = PropsSI('S', 'T', T_h_out, 'P', P_h, fluid_h)

    h_c_in  = PropsSI('H', 'T', T_c_in,  'P', P_c, fluid_c)
    h_c_out = PropsSI('H', 'T', T_c_out, 'P', P_c, fluid_c)
    s_c_in  = PropsSI('S', 'T', T_c_in,  'P', P_c, fluid_c)
    s_c_out = PropsSI('S', 'T', T_c_out, 'P', P_c, fluid_c)

    T_b_H = (h_h_in - h_h_out) / (s_h_in - s_h_out)
    T_b_C = (h_c_out - h_c_in) / (s_c_out - s_c_in)
    Q_dot = m_dot_h * (h_h_in - h_h_out)

    print('\nBoundary temperatures:')
    print(f' T_b,H = {T_b_H:.3f} K')
    print(f' T_b,C = {T_b_C:.3f} K')
    print(f' Q_dot = {Q_dot/1000:.3f} kW')

    return (T_b_H, T_b_C, Q_dot,
            h_h_in, h_h_out, s_h_in, s_h_out,
            h_c_in, h_c_out, s_c_in, s_c_out)


def compute_exergy_destruction(T_b_H, T_b_C, Q_dot, T_0,
                                m_dot_h, m_dot_c,
                                s_h_in, s_h_out, s_c_in, s_c_out):
    """Calculate exergy destruction in the destruction layer.

    ``X_dest = T0 * Q_dot * (1/T_b_C - 1/T_b_H)``

    Also compute total entropy generation and a consistency check::

        S_gen = m_h (s_h_out - s_h_in) + m_c (s_c_out - s_c_in)
        X_check = T0 * S_gen

    Returns ``(X_dest, X_check)``.
    """
    X_dest = T_0 * Q_dot * (1.0 / T_b_C - 1.0 / T_b_H)
    S_gen = m_dot_h * (s_h_out - s_h_in) + m_dot_c * (s_c_out - s_c_in)
    X_check = T_0 * S_gen
    print(f"\nExergy destruction (layer) = {X_dest/1000:.3f} kW")
    print(f"Entropy-generation check -> X = {X_check/1000:.3f} kW")
    return X_dest, X_check


def compute_exergetic_efficiency(m_dot_h, m_dot_c, T_0,
                                   h_h_in, h_h_out, s_h_in, s_h_out,
                                   h_c_in, h_c_out, s_c_in, s_c_out):
    """Compute exergetic efficiency defined by stream exergies.

    Numerator: exergy gain of cold fluid
        m_c[(h_c_out-h_c_in)-T0(s_c_out-s_c_in)]
    Denominator: exergy loss of hot fluid
        m_h[(h_h_in-h_h_out)-T0(s_h_in-s_h_out)]
    """
    dX_c = m_dot_c * ((h_c_out - h_c_in) - T_0 * (s_c_out - s_c_in))
    dX_h = m_dot_h * ((h_h_in - h_h_out) - T_0 * (s_h_in - s_h_out))
    eta_ex = dX_c / dX_h if dX_h != 0 else float('nan')
    print(f"\nExergetic efficiency = {eta_ex:.4f}")
    return eta_ex


def main():
    parser = argparse.ArgumentParser()
    # allow specification of actual mass flows (Part A values by default)
    parser.add_argument('--m_h', type=float, default=2.0,
                        help='hot-side mass flow (kg/s)')
    parser.add_argument('--m_c', type=float, default=1.2,
                        help='cold-side mass flow (kg/s)')
    args = parser.parse_args()
    m_dot_h = args.m_h
    m_dot_c = args.m_c
    mu = m_dot_h / m_dot_c if m_dot_c != 0 else float('inf')

    # Given conditions
    P_h = 12e6  # Pa
    T_h_in = 720.0  # K

    P_c = 10e6  # Pa
    T_c_in = 310.0  # K

    dTmin = 12.0  # K

    fluid_h = 'CO2'
    fluid_c = 'Water'

    # Inlet enthalpies
    h_h_in = PropsSI('H', 'T', T_h_in, 'P', P_h, fluid_h)
    h_c_in = PropsSI('H', 'T', T_c_in, 'P', P_c, fluid_c)

    print('Given:')
    print(f'- Hot:  {fluid_h}, P_h={P_h:.3g} Pa, T_h,in={T_h_in:.3f} K')
    print(f'- Cold: {fluid_c}, P_c={P_c:.3g} Pa, T_c,in={T_c_in:.3f} K')
    print()
    print('Inlet enthalpies:')
    print(f'- h_h,in = {Jperkg_to_kJperkg(h_h_in):.3f} kJ/kg')
    print(f'- h_c,in = {Jperkg_to_kJperkg(h_c_in):.3f} kJ/kg')
    print()

    print(f'Hot mass flow = {m_dot_h:.3f} kg/s, cold mass flow = {m_dot_c:.3f} kg/s')
    print(f'Using mass-flow ratio mu = m_h/m_c = {mu:.6g}')
    print()

    # helper to evaluate a pinch case and return results + feasibility
    def evaluate_case(pinch_hot: bool):
        if pinch_hot:
            T_h_out = T_c_in + dTmin
            h_h_out = PropsSI('H', 'T', T_h_out, 'P', P_h, fluid_h)
            h_c_out = h_c_in + mu * (h_h_in - h_h_out)
            T_c_out = safe_T_from_h(h_c_out, P_c, fluid_c)
            # opposite-end differential for feasibility: cold outlet
            dT_other = T_h_in - (T_c_out if T_c_out is not None else T_c_in)
            return T_h_out, h_h_out, h_c_out, T_c_out, dT_other
        else:
            T_c_out = T_h_in - dTmin
            h_c_out = PropsSI('H', 'T', T_c_out, 'P', P_c, fluid_c)
            h_h_out = h_h_in - (h_c_out - h_c_in) / mu if mu != 0 else None
            T_h_out = safe_T_from_h(h_h_out, P_h, fluid_h) if h_h_out is not None else None
            # if we can't compute T_h_out, we cannot evaluate feasibility
            dT_other = None if T_h_out is None else T_h_out - T_c_in
            return T_h_out, h_h_out, h_c_out, T_c_out, dT_other

    # evaluate both cases
    T_h_out_case1, h_h_out_case1, h_c_out_case1, T_c_out_case1, dT_other1 = evaluate_case(True)
    T_h_out_case2, h_h_out_case2, h_c_out_case2, T_c_out_case2, dT_other2 = evaluate_case(False)

    print('Case 1 (pinch at hot outlet):')
    print(f'- T_h,out = {T_h_out_case1:.3f} K')
    print(f'- h_h,out = {Jperkg_to_kJperkg(h_h_out_case1):.3f} kJ/kg')
    print(f'- h_c,out = {Jperkg_to_kJperkg(h_c_out_case1):.3f} kJ/kg')
    if T_c_out_case1 is not None:
        print(f'- T_c,out = {T_c_out_case1:.3f} K')
        print(f'- dT at cold outlet = {dT_other1:.3f} K  '
              f'{"FEASIBLE" if dT_other1 >= dTmin else "INFEASIBLE"}')
    else:
        print('- T_c,out: could not invert enthalpy to temperature at given P_c')
    if h_h_in - h_h_out_case1 != 0:
        mu_calc_case1 = (h_c_out_case1 - h_c_in) / (h_h_in - h_h_out_case1)
        print(f'- implied mu = {mu_calc_case1:.6g}')
    print()

    print('Case 2 (pinch at cold outlet):')
    print(f'- T_c,out = {T_c_out_case2:.3f} K')
    print(f'- h_c,out = {Jperkg_to_kJperkg(h_c_out_case2):.3f} kJ/kg')
    if h_h_out_case2 is not None:
        print(f'- h_h,out = {Jperkg_to_kJperkg(h_h_out_case2):.3f} kJ/kg')
        if T_h_out_case2 is not None:
            print(f'- T_h,out = {T_h_out_case2:.3f} K')
            print(f'- dT at hot outlet = {dT_other2:.3f} K  '
                  f'{"FEASIBLE" if dT_other2 >= dTmin else "INFEASIBLE"}')
        else:
            print('- T_h,out: could not invert enthalpy to temperature at given P_h')
        if (h_h_in - h_h_out_case2) != 0:
            mu_calc_case2 = (h_c_out_case2 - h_c_in) / (h_h_in - h_h_out_case2)
            print(f'- implied mu = {mu_calc_case2:.6g}')
    else:
        print('- mu was zero, cannot compute h_h,out')

    # choose a feasible case for subsequent analysis
    # Initialize variables to None to avoid possible use before assignment
    TbH = TbC = Qdot = None
    h_h_out = s_h_in = s_h_out = h_c_out = s_c_in = s_c_out = None

    if T_c_out_case1 is not None and dT_other1 >= dTmin:
        # analyze case 1, receive full property set
        (TbH, TbC, Qdot,
         h_h_in_calc, h_h_out, s_h_in, s_h_out,
         h_c_in_calc, h_c_out, s_c_in, s_c_out) = \
            compute_boundary_temperatures(
                T_h_in, T_h_out_case1, P_h,
                T_c_in, T_c_out_case1, P_c,
                m_dot_h, m_dot_c
            )
        # h_h_in and h_c_in already computed earlier; ensure consistency
        h_h_in = h_h_in_calc
        h_c_in = h_c_in_calc
    elif T_h_out_case2 is not None and dT_other2 >= dTmin:
        (TbH, TbC, Qdot,
         h_h_in_calc, h_h_out, s_h_in, s_h_out,
         h_c_in_calc, h_c_out, s_c_in, s_c_out) = \
            compute_boundary_temperatures(
                T_h_in, T_h_out_case2, P_h,
                T_c_in, T_c_out_case2, P_c,
                m_dot_h, m_dot_c
            )
        h_h_in = h_h_in_calc
        h_c_in = h_c_in_calc

    if TbH is not None:
        Xdest, Xcheck = compute_exergy_destruction(
            TbH, TbC, Qdot, 300.0, m_dot_h, m_dot_c,
            s_h_in, s_h_out, s_c_in, s_c_out
        )
        compute_exergetic_efficiency(
            m_dot_h, m_dot_c, 300.0,
            h_h_in, h_h_out, s_h_in, s_h_out,
            h_c_in, h_c_out, s_c_in, s_c_out
        )


if __name__ == '__main__':
    main()
