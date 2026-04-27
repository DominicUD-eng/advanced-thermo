"""
Assignment 6 — Problem 2 (Study 1 + closure cross-check for Study 2)
R-134a vapor-compression refrigeration cycle.
MEE 511 Advanced Thermodynamics — Dominic Lavigne
"""

import numpy as np
import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI

FLUID = "R134a"

# ---------- Inputs ----------
T_evap = 4   + 273.15      # K
T_cond = 39.4 + 273.15     # K
dT_sup = 1.0               # K superheat at compressor inlet
dT_sub = 0.5               # K subcooling at valve inlet

eta_c   = 0.9              # compressor isentropic
m_dot   = 1.0              # kg/s

T_0     = 32 + 273.15      # K  (ambient / dead state, condenser side)
T_C     = 28 + 273.15      # K  (avg conditioned-air, evaporator side)

# ---------- Saturation pressures ----------
P_evap = PropsSI("P", "T", T_evap, "Q", 0, FLUID)
P_cond = PropsSI("P", "T", T_cond, "Q", 0, FLUID)

# ---------- State 1: superheated vapor at compressor inlet ----------
T1 = T_evap + dT_sup
h1 = PropsSI("H", "P", P_evap, "T", T1, FLUID)
s1 = PropsSI("S", "P", P_evap, "T", T1, FLUID)

# ---------- State 2: compressor exit at P_cond ----------
h2s   = PropsSI("H", "P", P_cond, "S", s1, FLUID)
w_c_s = h2s - h1
w_c   = w_c_s / eta_c
h2    = h1 + w_c
T2    = PropsSI("T", "P", P_cond, "H", h2, FLUID)
s2    = PropsSI("S", "P", P_cond, "H", h2, FLUID)

# ---------- State 3: subcooled liquid at valve inlet ----------
T3 = T_cond - dT_sub
h3 = PropsSI("H", "P", P_cond, "T", T3, FLUID)
s3 = PropsSI("S", "P", P_cond, "T", T3, FLUID)

# ---------- State 4: isenthalpic throttle to P_evap ----------
h4 = h3
T4 = PropsSI("T", "P", P_evap, "H", h4, FLUID)   # = T_evap (two-phase)
s4 = PropsSI("S", "P", P_evap, "H", h4, FLUID)
h_f4 = PropsSI("H", "P", P_evap, "Q", 0, FLUID)
h_g4 = PropsSI("H", "P", P_evap, "Q", 1, FLUID)
x4   = (h4 - h_f4) / (h_g4 - h_f4)

# ---------- Performance ----------
q_evap  = h1 - h4
q_cond  = h2 - h3
w_c_kg  = h2 - h1
Q_evap  = m_dot * q_evap
Q_cond  = m_dot * q_cond
W_c     = m_dot * w_c_kg

COP            = q_evap / w_c_kg
COP_Carnot_cyc = T_evap / (T_cond - T_evap)
COP_Carnot_res = T_C    / (T_0 - T_C)
eta_II_cyc     = COP / COP_Carnot_cyc
eta_II_res     = COP / COP_Carnot_res

# ---------- Condenser zone-splitting (parts c and d) ----------
h_g_cond = PropsSI("H", "P", P_cond, "Q", 1, FLUID)
s_g_cond = PropsSI("S", "P", P_cond, "Q", 1, FLUID)
h_f_cond = PropsSI("H", "P", P_cond, "Q", 0, FLUID)
s_f_cond = PropsSI("S", "P", P_cond, "Q", 0, FLUID)

q_z1  = h2 - h_g_cond
ds_z1 = s2 - s_g_cond
Tb_z1 = q_z1 / ds_z1
Ed_z1 = m_dot * q_z1 * (1.0 - T_0 / Tb_z1)

q_z2  = h_g_cond - h_f_cond
ds_z2 = s_g_cond - s_f_cond
Tb_z2 = T_cond
Ed_z2 = m_dot * q_z2 * (1.0 - T_0 / Tb_z2)

q_z3  = h_f_cond - h3
ds_z3 = s_f_cond - s3
Tb_z3 = q_z3 / ds_z3 if abs(ds_z3) > 1e-9 else T_cond
Ed_z3 = m_dot * q_z3 * (1.0 - T_0 / Tb_z3)

Ed_cond_zones = Ed_z1 + Ed_z2 + Ed_z3

# ---------- Component-wise exergy destruction ----------
Sdot_c    = m_dot * (s2 - s1)
Ed_c      = T_0 * Sdot_c

Sdot_cond = m_dot * (s3 - s2) + m_dot * q_cond / T_0
Ed_cond_lumped = T_0 * Sdot_cond

Sdot_v    = m_dot * (s4 - s3)
Ed_v      = T_0 * Sdot_v

Sdot_evap = m_dot * (s1 - s4) - m_dot * q_evap / T_C
Ed_evap   = T_0 * Sdot_evap

E_cool   = m_dot * q_evap * (T_0 / T_C - 1.0)
Ed_tot_d = Ed_c + Ed_cond_zones + Ed_v

# ---------- Report ----------
def _row(i, T, P, h, s, note=""):
    print(f"State {i}: T={T-273.15:7.2f} C  P={P/1e3:8.2f} kPa  "
          f"h={h/1e3:7.2f} kJ/kg  s={s/1e3:7.4f} kJ/(kg.K)  {note}")

print("========== STUDY 1 ==========")
_row(1, T1, P_evap, h1, s1, "superheated +1 K")
_row(2, T2, P_cond, h2, s2, "superheated, compressor exit")
_row(3, T3, P_cond, h3, s3, "subcooled -0.5 K")
_row(4, T4, P_evap, h4, s4, f"two-phase, x={x4:.4f}")

print()
print(f"P_evap        = {P_evap/1e3:8.2f} kPa")
print(f"P_cond        = {P_cond/1e3:8.2f} kPa")
print(f"q_evap        = {q_evap/1e3:8.2f} kJ/kg   Q_evap = {Q_evap/1e3:8.2f} kW")
print(f"q_cond        = {q_cond/1e3:8.2f} kJ/kg   Q_cond = {Q_cond/1e3:8.2f} kW")
print(f"w_compressor  = {w_c_kg/1e3:8.2f} kJ/kg   W_c    = {W_c/1e3:8.2f} kW")
print(f"COP_R                  = {COP:6.3f}")
print(f"COP_Carnot (cycle)     = {COP_Carnot_cyc:6.3f}    eta_II_cycle    = {eta_II_cyc*100:5.2f} %")
print(f"COP_Carnot (reservoir) = {COP_Carnot_res:6.3f}    eta_II_reservoir = {eta_II_res*100:5.2f} %")

print()
print("--- (c) Effective hot-side boundary T's of heat rejection (condenser) ---")
print(f"  Zone 1 desuperheat:   Tb1 = {Tb_z1:6.2f} K = {Tb_z1-273.15:5.2f} C   q1 = {q_z1/1e3:6.2f} kJ/kg")
print(f"  Zone 2 phase change:  Tb2 = {Tb_z2:6.2f} K = {Tb_z2-273.15:5.2f} C   q2 = {q_z2/1e3:6.2f} kJ/kg")
print(f"  Zone 3 sub-cool:      Tb3 = {Tb_z3:6.2f} K = {Tb_z3-273.15:5.2f} C   q3 = {q_z3/1e3:6.2f} kJ/kg")

print()
print("--- (d) Exergy destruction: compressor, condenser zones, valve ---")
print(f"  Compressor:                      E_d = {Ed_c/1e3:6.3f} kW   ({Ed_c/Ed_tot_d*100:5.1f} %)")
print(f"  Condenser zone 1 (desuperheat):  E_d = {Ed_z1/1e3:6.3f} kW   ({Ed_z1/Ed_tot_d*100:5.1f} %)")
print(f"  Condenser zone 2 (phase change): E_d = {Ed_z2/1e3:6.3f} kW   ({Ed_z2/Ed_tot_d*100:5.1f} %)")
print(f"  Condenser zone 3 (sub-cool):     E_d = {Ed_z3/1e3:6.3f} kW   ({Ed_z3/Ed_tot_d*100:5.1f} %)")
print(f"  Condenser TOTAL:                 E_d = {Ed_cond_zones/1e3:6.3f} kW   ({Ed_cond_zones/Ed_tot_d*100:5.1f} %)")
print(f"  Expansion valve:                 E_d = {Ed_v/1e3:6.3f} kW   ({Ed_v/Ed_tot_d*100:5.1f} %)")
print(f"  TOTAL (parts d, excl. evap):     E_d = {Ed_tot_d/1e3:6.3f} kW")

print()
print(f"  Sanity: Ed_cond (lumped) = {Ed_cond_lumped/1e3:6.3f} kW vs zones-summed = {Ed_cond_zones/1e3:6.3f} kW  (should match)")
print(f"  Evaporator (single-T closure):  E_d = {Ed_evap/1e3:6.3f} kW")
print(f"  Useful cooling exergy:  E_cool = {E_cool/1e3:6.3f} kW")
print(f"  Full closure: W_c = {W_c/1e3:6.3f} kW vs E_cool + sum(all 4 E_d) = "
      f"{(E_cool + Ed_c + Ed_cond_zones + Ed_v + Ed_evap)/1e3:6.3f} kW")

# ---------- Study 2 lumped psychrometric closure (cross-check) ----------
print()
print("========== STUDY 2 (lumped psychrometric) ==========")

# Air-side conditions
P_atm = 101325.0
T_a   = 32 + 273.15;  RH_a = 0.95
T_b   = 24 + 273.15;  RH_b = 0.60

# Saturation pressure (Antoine-style via CoolProp on water)
Psat_a = PropsSI("P", "T", T_a, "Q", 0, "Water")
Psat_b = PropsSI("P", "T", T_b, "Q", 0, "Water")
Pv_a   = RH_a * Psat_a;   Pv_b   = RH_b * Psat_b
Pda_a  = P_atm - Pv_a;    Pda_b  = P_atm - Pv_b
omega_a = 0.622 * Pv_a / Pda_a
omega_b = 0.622 * Pv_b / Pda_b

# Moist-air enthalpy (per kg dry air), reference 0 C
def h_moist(T_K, omega):
    Tc = T_K - 273.15
    return 1.005e3 * Tc + omega * (2501.3e3 + 1.82e3 * Tc)   # J/kg_da

h_a_air = h_moist(T_a, omega_a)
h_b_air = h_moist(T_b, omega_b)
h_w_Tb  = PropsSI("H", "T", T_b, "Q", 0, "Water")            # sat. liquid water at T_b

m_dot_da = Q_evap / ((h_a_air - h_b_air) - (omega_a - omega_b) * h_w_Tb)
m_dot_cond = m_dot_da * (omega_a - omega_b)

# Sensible / latent split (diagnostic)
cp_moist = 1.005e3 + ((omega_a + omega_b)/2) * 1.82e3
Q_sens = m_dot_da * cp_moist * (T_a - T_b)
Q_lat  = Q_evap - Q_sens

# Entropy balance on lumped evaporator CV
R_da = 287.0;  R_v = 461.5
ds_da = 1.005e3 * np.log(T_b/T_a) - R_da * np.log(Pda_b/Pda_a)

s_g_a = PropsSI("S", "T", T_a, "Q", 1, "Water")
s_g_b = PropsSI("S", "T", T_b, "Q", 1, "Water")
s_v_a = s_g_a - R_v * np.log(RH_a)
s_v_b = s_g_b - R_v * np.log(RH_b)
s_w_Tb = PropsSI("S", "T", T_b, "Q", 0, "Water")

Sgen_evap_lumped = (m_dot_da * ds_da
                   + m_dot_da * (omega_b * s_v_b - omega_a * s_v_a)
                   + m_dot_cond * s_w_Tb
                   + m_dot * (s1 - s4))
Ed_evap_lumped = T_0 * Sgen_evap_lumped

print(f"  omega_a = {omega_a:.5f}    omega_b = {omega_b:.5f}    Δω = {omega_a-omega_b:.5f}")
print(f"  h_a_air = {h_a_air/1e3:.2f} kJ/kg_da    h_b_air = {h_b_air/1e3:.2f} kJ/kg_da")
print(f"  m_dot_dry_air        = {m_dot_da:6.3f} kg_da/s")
print(f"  m_dot_condensate     = {m_dot_cond:6.4f} kg_w/s   ({m_dot_cond*3600:.0f} kg/h ≈ {m_dot_cond*3600:.0f} L/h)")
print(f"  Q_sens = {Q_sens/1e3:6.2f} kW    Q_lat = {Q_lat/1e3:6.2f} kW    (sum = {Q_evap/1e3:.2f} kW)")
print(f"  Sgen_evap (lumped)   = {Sgen_evap_lumped:6.2f} W/K")
print(f"  E_d_evap (lumped)    = {Ed_evap_lumped/1e3:6.3f} kW")

# System totals
E_d_total = Ed_c + Ed_cond_zones + Ed_v + Ed_evap_lumped
dPsi_air = W_c - E_d_total
print()
print("  --- System summary ---")
print(f"  W_c (work in)        = {W_c/1e3:6.3f} kW")
print(f"  Σ E_d (4 components) = {E_d_total/1e3:6.3f} kW   ({E_d_total/W_c*100:.1f} %)")
print(f"  ΔΨ_air (useful)      = {dPsi_air/1e3:6.3f} kW   ({dPsi_air/W_c*100:.1f} %)")
print(f"  η_II,sys             = {dPsi_air/W_c*100:5.2f} %")

# ---------- T-s diagram ----------
T_crit = PropsSI("Tcrit", FLUID)
T_dome = np.linspace(170.0, T_crit - 0.1, 400)
s_f = np.array([PropsSI("S", "T", T, "Q", 0, FLUID) for T in T_dome])
s_g = np.array([PropsSI("S", "T", T, "Q", 1, FLUID) for T in T_dome])

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(s_f/1e3, T_dome - 273.15, "k-", lw=1.2)
ax.plot(s_g/1e3, T_dome - 273.15, "k-", lw=1.2, label="Saturation dome")

S = np.array([s1, s2, s3, s4, s1]) / 1e3
T = np.array([T1, T2, T3, T4, T1]) - 273.15
ax.plot(S, T, "o-", color="C0", lw=2.0, ms=6, label="R-134a cycle")
for i, lbl in enumerate(["1", "2", "3", "4"]):
    ax.annotate(lbl, (S[i], T[i]), textcoords="offset points",
                xytext=(8, 8), fontsize=11, fontweight="bold")

ax.axhline(T_0  - 273.15, color="C3", ls=":", lw=1, label=f"T_0 = {T_0-273.15:.1f} °C (ambient)")
ax.axhline(T_C  - 273.15, color="C2", ls=":", lw=1, label=f"T_C = {T_C-273.15:.1f} °C (avg air)")
ax.set_xlabel("Specific entropy s  [kJ/(kg·K)]")
ax.set_ylabel("Temperature T  [°C]")
ax.set_title("R-134a refrigeration cycle — T-s diagram (Problem 2, Study 1)")

# Auto-fit axes to dome + cycle. CoolProp's default reference state for R-134a
# is IIR (h=200 kJ/kg, s=1.0 kJ/(kg·K) at sat. liq., 0 °C), so entropies live in
# the ~0.6–1.9 kJ/(kg·K) range — don't hardcode old NBP-style limits.
s_all = np.concatenate([s_f, s_g, np.array([s1, s2, s3, s4])]) / 1e3
T_all = np.concatenate([T_dome - 273.15, np.array([T1, T2, T3, T4]) - 273.15])
s_pad = 0.05 * (s_all.max() - s_all.min())
T_pad = 0.08 * (T_all.max() - T_all.min())
ax.set_xlim(s_all.min() - s_pad, s_all.max() + s_pad)
ax.set_ylim(T_all.min() - T_pad, T_all.max() + T_pad)
ax.grid(True, alpha=0.3)
ax.legend(loc="lower right", fontsize=9)
plt.tight_layout()
plt.savefig("problem2_Ts_study1.png", dpi=160)
plt.show()