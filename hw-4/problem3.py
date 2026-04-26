import numpy as np
from CoolProp.CoolProp import PropsSI

# ──────────────────────────────────────────────
# Given Parameters
# ──────────────────────────────────────────────
T1 = 300.0        # K, compressor inlet
P1 = 101325.0     # Pa, compressor inlet
rp = 15.0         # overall pressure ratio
T_max = 1200.0    # K, max turbine inlet temperature
eta_c = 0.8       # compressor isentropic efficiency
eta_t = 0.9       # turbine isentropic efficiency (each stage)
m_dot = 100.0     # kg/s
N_turb = 2        # 2 turbine stages, 1 reheater
fluid = "Air"

# Dead state
T0 = 300.0        # K
P0 = 101325.0     # Pa
v0 = 0.0          # m/s (velocity)
z0 = 0.0          # m (elevation)

# Dead state properties
h0 = PropsSI("H", "T", T0, "P", P0, fluid)
s0 = PropsSI("S", "T", T0, "P", P0, fluid)

# ──────────────────────────────────────────────
# Pressures
# ──────────────────────────────────────────────
P2 = rp * P1
P3 = P2
rp_stage = rp ** (1.0 / N_turb)
P4 = P3 / rp_stage
P5 = P4
P6 = P5 / rp_stage  # = P1

# ──────────────────────────────────────────────
# Solve all 6 states (CoolProp)
# ──────────────────────────────────────────────
def get_props(T, P):
    h = PropsSI("H", "T", T, "P", P, fluid)
    s = PropsSI("S", "T", T, "P", P, fluid)
    return h, s

def specific_exergy(h, s):
    """Specific flow exergy: ef = (h - h0) - T0*(s - s0)"""
    return (h - h0) - T0 * (s - s0)

# State 1
h1, s1 = get_props(T1, P1)
ef1 = specific_exergy(h1, s1)

# State 2 (compressor outlet)
h2s = PropsSI("H", "S", s1, "P", P2, fluid)
h2 = h1 + (h2s - h1) / eta_c
T2 = PropsSI("T", "H", h2, "P", P2, fluid)
_, s2 = get_props(T2, P2)
ef2 = specific_exergy(h2, s2)

# State 3 (combustor outlet)
h3, s3 = get_props(T_max, P3)
ef3 = specific_exergy(h3, s3)

# State 4 (first turbine outlet)
h4s = PropsSI("H", "S", s3, "P", P4, fluid)
h4 = h3 - eta_t * (h3 - h4s)
T4 = PropsSI("T", "H", h4, "P", P4, fluid)
_, s4 = get_props(T4, P4)
ef4 = specific_exergy(h4, s4)

# State 5 (reheater outlet)
h5, s5 = get_props(T_max, P5)
ef5 = specific_exergy(h5, s5)

# State 6 (second turbine outlet)
h6s = PropsSI("H", "S", s5, "P", P6, fluid)
h6 = h5 - eta_t * (h5 - h6s)
T6 = PropsSI("T", "H", h6, "P", P6, fluid)
_, s6 = get_props(T6, P6)
ef6 = specific_exergy(h6, s6)

# Print state table
print("=" * 85)
print("STATE PROPERTIES (CoolProp, 2-stage expansion with reheat)")
print("=" * 85)
print(f"{'State':>5} | {'T (K)':>10} | {'P (Pa)':>12} | {'h (kJ/kg)':>12} | "
      f"{'s (J/kg·K)':>12} | {'ef (kJ/kg)':>12}")
print("-" * 85)
states = {
    1: (T1,    P1, h1, s1, ef1),
    2: (T2,    P2, h2, s2, ef2),
    3: (T_max, P3, h3, s3, ef3),
    4: (T4,    P4, h4, s4, ef4),
    5: (T_max, P5, h5, s5, ef5),
    6: (T6,    P6, h6, s6, ef6),
}
for st, (T, P, h, s, ef) in states.items():
    print(f"{st:>5} | {T:>10.2f} | {P:>12.0f} | {h/1e3:>12.3f} | "
          f"{s:>12.3f} | {ef/1e3:>12.3f}")

# ──────────────────────────────────────────────
# EXERGY DESTRUCTION per component (per unit mass)
# ──────────────────────────────────────────────
# General: Ed = T0 * s_gen (per unit mass)
# For each component: s_gen = (s_out - s_in) - q/T_boundary
# For adiabatic work devices: Ed = T0 * (s_out - s_in)
# For heat exchangers (combustor/reheater): 
#   Ed = T0 * [(s_out - s_in) - q/T_eff]
#   where q = h_out - h_in (heat added to stream)
#   and T_eff is the effective source temperature

# ── (a) Component-by-component exergy destruction ──

# 1. COMPRESSOR (adiabatic, work input)
#    Ed_comp = T0 * m_dot * (s2 - s1)
#    Or equivalently: Ed_comp = m_dot * (w_comp - (ef2 - ef1))
ed_comp = T0 * (s2 - s1)  # J/kg
Ed_comp = m_dot * ed_comp   # W

# 2. COMBUSTOR (isobaric heat addition, 2→3)
#    Energy: q_comb = h3 - h2
#    Exergy supplied by fuel:  Ef_q_comb = q_comb * (1 - T0/T_eff_comb)
#    Ed_comb = Ef_q_comb - (ef3 - ef2) = T0 * (s3 - s2) - T0 * q_comb / T_eff
#    But we need T_eff first. We find it from the entropy-averaged temperature.
#    T_eff = q / (s_out - s_in) for the stream receiving heat
q_comb = h3 - h2  # J/kg (heat added)
T_eff_comb = q_comb / (s3 - s2)  # effective temperature of heat addition

# Exergy destruction = exergy in - exergy out
# For combustor modeled as external heat source at T_eff:
#   Ed = m_dot * [T0*(s3-s2) - T0*q_comb/T_eff]  ... but that's 0 by definition of T_eff!
# 
# Instead, the CORRECT approach: The fuel is burned, modeled as heat from
# combustion products at some effective temperature. The exergy destruction is:
#   Ed_comb = m_dot * [(ef2 + ef_q_comb) - ef3]
#   where ef_q_comb = q_comb * (1 - T0/T_source)
# 
# Since we don't know the actual flame/source temperature, we compute
# exergy destruction using the entropy generation approach:
#   s_gen_comb = (s3 - s2) - q_comb / T_source
#
# HOWEVER, the assignment asks for the "effective temperature for heat transfer
# for the combustor and reheater" — this is T_eff = q / Δs of the stream,
# i.e., the log-mean-like temperature at which the STREAM receives heat.
# 
# For the exergy destruction, if we model the heat source as the fuel
# (chemical exergy ≈ q_comb for natural gas approximation), then:
#   Ed_comb = m_dot * [q_comb - (ef3 - ef2)]   (fuel exergy in, minus stream exergy gain)
#   This equals: Ed_comb = m_dot * T0 * (s3 - s2)    ... only if source is at T→∞
#
# The standard approach for this course: model the heat as coming from a 
# reservoir at T_eff (the effective temperature), so:
#   Ed_comb = m_dot * q_comb * (1 - T0/T_eff_comb) - m_dot * (ef3 - ef2)

# Let's compute it both ways and use the exergy balance:
# Method: Exergy balance on combustor
#   Exergy in (heat from source at T_eff) = q * (1 - T0/T_eff)
#   Exergy out (stream gain) = ef3 - ef2
#   Ed = Exergy_in - Exergy_out
# But T_eff = q/(s3-s2), so q*(1-T0/T_eff) = q - T0*(s3-s2) = (h3-h2) - T0*(s3-s2) = ef3 - ef2
# This means Ed = 0 if we use T_eff as the source temperature!
#
# The resolution: T_eff is the effective temperature of the STREAM (cold side).
# The actual source (combustion gases) is at a HIGHER temperature.
# For the assignment, the exergy destruction in the combustor comes from
# the irreversibility of heat transfer across a finite ΔT.
#
# Standard textbook approach (Moran, Çengel):
#   For an internally reversible, isobaric heat exchanger with an external source:
#   Ed_combustor = T0 * s_gen = T0 * m_dot * (s3 - s2)  [if source is modeled at T→∞]
#
# BUT the assignment says to find the "effective temperature" for the combustor.
# The effective temperature is defined as: T_eff = q / Δs (for the stream).
# Then comparing to a Carnot cycle operating between T_eff and T0 gives the
# exergetic efficiency context.
#
# For EXERGY DESTRUCTION in each component, we use the straightforward
# entropy generation * T0 method. For the combustor and reheater, 
# we need to decide what the source temperature is.
#
# The cleanest interpretation: the fuel's chemical exergy ≈ the heat released,
# so the exergy input to the combustor = q_comb (approximately).
# Then: Ed_comb = q_comb - (ef3 - ef2)

ed_comb = q_comb - (ef3 - ef2)  # J/kg
Ed_comb_rate = m_dot * ed_comb   # W

# 3. TURBINE 1 (adiabatic, work output, 3→4)
ed_turb1 = T0 * (s4 - s3)  # J/kg
Ed_turb1 = m_dot * ed_turb1

# 4. REHEATER (isobaric heat addition, 4→5)
q_rh = h5 - h4  # J/kg
T_eff_rh = q_rh / (s5 - s4)  # effective stream temperature

ed_rh = q_rh - (ef5 - ef4)  # J/kg
Ed_rh = m_dot * ed_rh

# 5. TURBINE 2 (adiabatic, work output, 5→6)
ed_turb2 = T0 * (s6 - s5)  # J/kg
Ed_turb2 = m_dot * ed_turb2

# 6. HEAT REJECTION (exhaust, 6→1, to environment)
# The exhaust gas at state 6 is rejected to the dead state at T0, P0
# Exergy rejected = exergy of stream at state 6 (since state 1 = dead state, ef1 ≈ 0)
q_out = h6 - h1  # J/kg (heat rejected)
ed_exhaust = ef6 - ef1  # exergy wasted (rejected to environment)
Ed_exhaust = m_dot * ed_exhaust

# ──────────────────────────────────────────────
# Performance Summary
# ──────────────────────────────────────────────
w_comp = h2 - h1
w_turb1 = h3 - h4
w_turb2 = h5 - h6
w_net = (w_turb1 + w_turb2) - w_comp
q_in = q_comb + q_rh
eta_th = w_net / q_in

# Total exergy input (fuel exergy ≈ q_comb + q_rh for natural gas)
ef_fuel_total = q_in  # approximation

# Total exergy destruction
Ed_total_components = Ed_comp + Ed_comb_rate + Ed_turb1 + Ed_rh + Ed_turb2
Ed_total_with_exhaust = Ed_total_components + Ed_exhaust

# Exergetic (second-law) efficiency
# η_ex = W_net / Ef_fuel_in
eta_ex = (m_dot * w_net) / (m_dot * ef_fuel_total)

# Carnot efficiency at effective combustor temperature
eta_carnot_comb = 1 - T0 / T_eff_comb

print("\n" + "=" * 70)
print("EXERGY ANALYSIS — Study 3")
print("=" * 70)

print(f"\n  Dead state: T0 = {T0} K, P0 = {P0} Pa")
print(f"  h0 = {h0/1e3:.3f} kJ/kg,  s0 = {s0:.3f} J/(kg·K)")

print(f"\n── Cycle Performance ──")
print(f"  W_comp   = {w_comp/1e3:.2f} kJ/kg  ({m_dot*w_comp/1e6:.3f} MW)")
print(f"  W_turb1  = {w_turb1/1e3:.2f} kJ/kg  ({m_dot*w_turb1/1e6:.3f} MW)")
print(f"  W_turb2  = {w_turb2/1e3:.2f} kJ/kg  ({m_dot*w_turb2/1e6:.3f} MW)")
print(f"  W_net    = {w_net/1e3:.2f} kJ/kg  ({m_dot*w_net/1e6:.3f} MW)")
print(f"  Q_comb   = {q_comb/1e3:.2f} kJ/kg")
print(f"  Q_reheat = {q_rh/1e3:.2f} kJ/kg")
print(f"  Q_in     = {q_in/1e3:.2f} kJ/kg")
print(f"  η_th     = {eta_th*100:.3f} %")

print(f"\n── Effective Temperatures (b.1a) ──")
print(f"  Combustor effective temp:  T_eff,comb = {T_eff_comb:.2f} K")
print(f"    (Stream: T2 = {T2:.2f} K → T3 = {T_max:.2f} K)")
print(f"  Reheater effective temp:   T_eff,rh   = {T_eff_rh:.2f} K")
print(f"    (Stream: T4 = {T4:.2f} K → T5 = {T_max:.2f} K)")

print(f"\n── Exergy Destruction by Component (b.1b) ──")
print(f"  {'Component':<20} | {'Ed (kJ/kg)':>12} | {'Ed_dot (MW)':>12} | {'% of Total':>10}")
print(f"  {'-'*60}")

components = [
    ("Compressor",   ed_comp,    Ed_comp),
    ("Combustor",    ed_comb,    Ed_comb_rate),
    ("Turbine 1",    ed_turb1,   Ed_turb1),
    ("Reheater",     ed_rh,      Ed_rh),
    ("Turbine 2",    ed_turb2,   Ed_turb2),
    ("Exhaust (6→0)", ed_exhaust, Ed_exhaust),
]

ed_total_all = sum(c[1] for c in components)
for name, ed, Ed_dot in components:
    pct = (ed / ed_total_all) * 100
    print(f"  {name:<20} | {ed/1e3:>12.3f} | {Ed_dot/1e6:>12.4f} | {pct:>9.2f}%")

print(f"  {'-'*60}")
print(f"  {'TOTAL':<20} | {ed_total_all/1e3:>12.3f} | {m_dot*ed_total_all/1e6:>12.4f} | {'100.00%':>10}")

print(f"\n── Exergy Rejected to Environment (b.1c) ──")
print(f"  Exergy at state 6:  ef6 = {ef6/1e3:.3f} kJ/kg")
print(f"  Rate of exergy rejection: {Ed_exhaust/1e6:.4f} MW")

print(f"\n── Exergetic Efficiency & Carnot Comparison (b.1d) ──")
print(f"  Exergetic efficiency:       η_ex     = {eta_ex*100:.3f} %")
print(f"  Carnot at T_eff,comb & T0:  η_Carnot = {eta_carnot_comb*100:.3f} %")
print(f"    (T_H = T_eff,comb = {T_eff_comb:.2f} K,  T_L = T0 = {T0:.2f} K)")
print(f"  Ratio η_ex / η_Carnot:      {(eta_ex/eta_carnot_comb)*100:.2f} %")

# ──────────────────────────────────────────────
# Verify: Exergy balance on entire cycle
# ──────────────────────────────────────────────
print(f"\n── Exergy Balance Check ──")
print(f"  Exergy input (fuel ≈ Q_in): {q_in/1e3:.3f} kJ/kg")
print(f"  Net work produced:          {w_net/1e3:.3f} kJ/kg")
print(f"  Total exergy destroyed:     {(ed_total_all)/1e3:.3f} kJ/kg")
print(f"  Sum (W_net + Ed_total):     {(w_net + ed_total_all)/1e3:.3f} kJ/kg")
balance_error = abs(q_in - (w_net + ed_total_all)) / q_in * 100
print(f"  Balance error:              {balance_error:.4f} %")