"""
Assignment 6 — Problem 1: Cardinal Steam Rankine Cycle
MEE 511 Advanced Thermodynamics — Dominic Lavigne

Study 1: Fixed turbine inlet T3 = 500 C; W_net,elec = 1800 MW.
Study 2: Sweep T3 = 300-700 C with mass flows fixed at Study 1 design point.
Study 3: T3 = 700 C, river dump vs passive cooling tower (psychrometric balance).
Real water properties via CoolProp (IAPWS).
"""

import numpy as np
import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI

FLUID = "Water"

# ============================================================
# Inputs (shared across all studies)
# ============================================================
P_lo  = 0.08e5            # Pa  (condenser)
P_hi  = 100e5             # Pa  (boiler)
T3    = 500 + 273.15      # K   (Study 1 turbine inlet)

eta_p = 0.80              # pump isentropic
eta_t = 0.90              # turbine isentropic
eta_g = 0.76              # generator electrical

W_net_elec = 1800e6       # W   (net plant electric)
T_cw_in    = 10 + 273.15  # K
dT_cw_max  = 10.0         # K (10 -> 20 C cap to limit thermal pollution)
cp_w       = 4186.0       # J/(kg.K)

HV_coal = 25e6            # J/kg

# ============================================================
# STUDY 1 — Cycle solve at T3 = 500 C
# ============================================================

# State 1: saturated liquid at P_lo
h1 = PropsSI("H", "P", P_lo, "Q", 0, FLUID)
s1 = PropsSI("S", "P", P_lo, "Q", 0, FLUID)
T1 = PropsSI("T", "P", P_lo, "Q", 0, FLUID)
v1 = 1.0 / PropsSI("D", "P", P_lo, "Q", 0, FLUID)

# State 2: pump exit at P_hi
h2s   = PropsSI("H", "P", P_hi, "S", s1, FLUID)
w_p_s = h2s - h1
w_p   = w_p_s / eta_p
h2    = h1 + w_p
s2    = PropsSI("S", "P", P_hi, "H", h2, FLUID)
T2    = PropsSI("T", "P", P_hi, "H", h2, FLUID)

# State 3: 100 bar, 500 C
h3 = PropsSI("H", "P", P_hi, "T", T3, FLUID)
s3 = PropsSI("S", "P", P_hi, "T", T3, FLUID)

# State 4: turbine exit at P_lo
h4s   = PropsSI("H", "P", P_lo, "S", s3, FLUID)
w_t_s = h3 - h4s
w_t   = eta_t * w_t_s
h4    = h3 - w_t
s4    = PropsSI("S", "P", P_lo, "H", h4, FLUID)
T4    = PropsSI("T", "P", P_lo, "H", h4, FLUID)
h_f   = PropsSI("H", "P", P_lo, "Q", 0, FLUID)
h_g   = PropsSI("H", "P", P_lo, "Q", 1, FLUID)
x4    = (h4 - h_f) / (h_g - h_f) if h4 < h_g else None

# Performance
q_in   = h3 - h2
q_out  = h4 - h1
w_net  = eta_g * w_t - w_p             # net electric per kg of steam

m_dot      = W_net_elec / w_net
Q_in_dot   = m_dot * q_in
Q_out_dot  = m_dot * q_out
W_t_dot    = m_dot * w_t
W_p_dot    = m_dot * w_p

eta_cycle  = (w_t - w_p) / q_in
eta_plant  = w_net / q_in

m_dot_cw   = Q_out_dot / (cp_w * dT_cw_max)

E_in_24h   = Q_in_dot * 24 * 3600
m_coal_24h = E_in_24h / HV_coal

# Report
print("========== STUDY 1 ==========")
def _row(i, T, P, h, s, x=None):
    xstr = f"  x={x:.4f}" if x is not None else ""
    print(f"State {i}: T={T-273.15:7.2f} C  P={P/1e5:7.3f} bar  "
          f"h={h/1e3:8.2f} kJ/kg  s={s/1e3:7.4f} kJ/(kg.K){xstr}")

_row(1, T1, P_lo, h1, s1)
_row(2, T2, P_hi, h2, s2)
_row(3, T3, P_hi, h3, s3)
_row(4, T4, P_lo, h4, s4, x4)

print()
print(f"w_pump            = {w_p/1e3:8.3f} kJ/kg")
print(f"w_turbine (act)   = {w_t/1e3:8.3f} kJ/kg")
print(f"q_in (boiler)     = {q_in/1e3:8.3f} kJ/kg")
print(f"q_out (condenser) = {q_out/1e3:8.3f} kJ/kg")
print(f"eta_cycle (shaft) = {eta_cycle*100:7.2f} %")
print(f"eta_plant (elec)  = {eta_plant*100:7.2f} %")
print()
print(f"m_dot steam       = {m_dot:9.2f} kg/s")
print(f"m_dot cooling H2O = {m_dot_cw:9.2f} kg/s   ({m_dot_cw/1e3:.2f} t/s)")
print(f"Q_in (boiler)     = {Q_in_dot/1e6:9.2f} MW_th")
print(f"Q_out (condenser) = {Q_out_dot/1e6:9.2f} MW_th")
print(f"Coal in 24 h      = {m_coal_24h:.3e} kg  ({m_coal_24h/1e6:.2f} kton)")

# T-s diagram with vapor dome and isobars
T_crit = PropsSI("Tcrit", FLUID)
T_dome = np.linspace(275.0, T_crit - 0.05, 400)
s_f_dome = np.array([PropsSI("S", "T", T, "Q", 0, FLUID) for T in T_dome])
s_g_dome = np.array([PropsSI("S", "T", T, "Q", 1, FLUID) for T in T_dome])

def isobar_Ts(P, T_min=280.0, T_max=1100.0, n=300):
    """Build T-s curve at constant P, splicing across the saturation dome."""
    Tsat = PropsSI("T", "P", P, "Q", 0, FLUID) if P < PropsSI("Pcrit", FLUID) else None
    Ts, ss = [], []
    if Tsat is not None:
        for T in np.linspace(T_min, Tsat - 0.05, n//3):
            ss.append(PropsSI("S", "P", P, "T", T, FLUID)); Ts.append(T)
        ss.append(PropsSI("S", "P", P, "Q", 0, FLUID)); Ts.append(Tsat)
        ss.append(PropsSI("S", "P", P, "Q", 1, FLUID)); Ts.append(Tsat)
        for T in np.linspace(Tsat + 0.05, T_max, n//2):
            ss.append(PropsSI("S", "P", P, "T", T, FLUID)); Ts.append(T)
    else:
        for T in np.linspace(T_min, T_max, n):
            ss.append(PropsSI("S", "P", P, "T", T, FLUID)); Ts.append(T)
    return np.array(Ts), np.array(ss)

T_hi_iso, s_hi_iso = isobar_Ts(P_hi)
T_lo_iso, s_lo_iso = isobar_Ts(P_lo)

fig, ax = plt.subplots(figsize=(8.0, 6.0))
ax.plot(s_f_dome/1e3, T_dome - 273.15, "k-", lw=1.2)
ax.plot(s_g_dome/1e3, T_dome - 273.15, "k-", lw=1.2, label="Saturation dome")
ax.plot(s_hi_iso/1e3, T_hi_iso - 273.15, "--", color="C3", lw=1.0, label="100 bar isobar")
ax.plot(s_lo_iso/1e3, T_lo_iso - 273.15, "--", color="C0", lw=1.0, label="0.08 bar isobar")

# Build cycle path that follows the 100 bar isobar through the boiler (2 -> 3),
# instead of cutting a straight diagonal across the dome.
mask_23 = (s_hi_iso >= s2) & (s_hi_iso <= s3)
s_boiler = np.concatenate(([s2], s_hi_iso[mask_23], [s3]))
T_boiler = np.concatenate(([T2], T_hi_iso[mask_23], [T3]))
order = np.argsort(s_boiler)
s_boiler, T_boiler = s_boiler[order], T_boiler[order]

S_cycle = np.concatenate((
    [s1, s2],            # 1 -> 2 (pump)
    s_boiler,            # 2 -> 3 (boiler, along 100 bar isobar)
    [s4, s1],            # 3 -> 4 (turbine) -> 1 (condenser)
)) / 1e3
T_cycle = np.concatenate((
    [T1, T2],
    T_boiler,
    [T4, T1],
)) - 273.15
ax.plot(S_cycle, T_cycle, "-", color="C2", lw=2.0, label="Cycle")

# Numbered state markers
S_pts = np.array([s1, s2, s3, s4]) / 1e3
T_pts = np.array([T1, T2, T3, T4]) - 273.15
ax.plot(S_pts, T_pts, "o", color="C2", ms=6)
for i, lbl in enumerate(["1", "2", "3", "4"]):
    ax.annotate(lbl, (S_pts[i], T_pts[i]), textcoords="offset points",
                xytext=(8, 8), fontsize=11, fontweight="bold")

ax.set_xlabel("Specific entropy s  [kJ/(kg·K)]")
ax.set_ylabel("Temperature T  [°C]")
ax.set_title("Cardinal Rankine Cycle — T-s diagram (Study 1, T₃ = 500 °C)")
ax.grid(True, alpha=0.3)
ax.legend(loc="lower right")
plt.tight_layout()
plt.savefig("rankine_Ts_study1.png", dpi=160)
plt.show()

# ============================================================
# STUDY 2 — T3 sweep with fixed mass flows from Study 1
# ============================================================
print()
print("========== STUDY 2 ==========")

m_dot_steam_S1 = m_dot          # 2037 kg/s
m_dot_cw_S1    = m_dot_cw       # ~98 340 kg/s

T3_C_grid = np.linspace(300.0, 700.0, 161)
T_cw_out_grid = np.zeros_like(T3_C_grid)
W_net_grid    = np.zeros_like(T3_C_grid)
x4_grid       = np.zeros_like(T3_C_grid)
q_out_grid    = np.zeros_like(T3_C_grid)

for i, T3_C in enumerate(T3_C_grid):
    T3_K = T3_C + 273.15
    h3i = PropsSI("H", "P", P_hi, "T", T3_K, FLUID)
    s3i = PropsSI("S", "P", P_hi, "T", T3_K, FLUID)
    h4si = PropsSI("H", "P", P_lo, "S", s3i, FLUID)
    w_ti = eta_t * (h3i - h4si)
    h4i  = h3i - w_ti
    x4_grid[i] = (h4i - h_f) / (h_g - h_f) if h4i < h_g else np.nan
    q_out_i = h4i - h1
    q_out_grid[i] = q_out_i
    Q_out_i = m_dot_steam_S1 * q_out_i
    T_cw_out_grid[i] = (T_cw_in + Q_out_i / (m_dot_cw_S1 * cp_w)) - 273.15
    W_net_grid[i] = m_dot_steam_S1 * (eta_g * w_ti - w_p)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(T3_C_grid, T_cw_out_grid, color="C3", lw=2)
ax.axhline(20.0, color="k", ls="--", lw=1, label="20 °C river-return cap")
ax.axvline(500.0, color="C2", ls=":",  lw=1, label="Study 1 design point")
ax.axvline(PropsSI("T","P",P_hi,"Q",0,FLUID)-273.15,
           color="C0", ls=":", lw=1, label="T_sat at 100 bar")
ax.set_xlabel("Turbine inlet temperature  T₃  [°C]")
ax.set_ylabel("Cooling-water outlet temperature  [°C]")
ax.set_title("Study 2 — T_cw,out vs T₃  (fixed ṁ_steam, ṁ_cw from Study 1)")
ax.grid(True, alpha=0.3); ax.legend(loc="best")
plt.tight_layout(); plt.savefig("study2_Tcw_out.png", dpi=160); plt.show()

print("Saved: study2_Tcw_out.png")
print(f"At T3 = 500 C : T_cw,out = {np.interp(500.0, T3_C_grid, T_cw_out_grid):.2f} C  (should ≈ 20.0)")
print(f"At T3 = 700 C : T_cw,out = {np.interp(700.0, T3_C_grid, T_cw_out_grid):.2f} C")

# ============================================================
# STUDY 3 — T3 = 700 C, river dump vs passive cooling tower
#
# Psychrometric balance from the figure:
#   Closed condenser loop: 20 -> 50 C  (dT_cond = 30 K, within 60 C cap)
#   Tower air inlet:       15 C, phi = 35 %
#   Tower air outlet:      35 C, phi = 92 %
#   River makeup at 10 C
#
# Mass + energy balances on the tower CV give m_da and m_evap directly.
# ============================================================
print()
print("========== STUDY 3 ==========")

T3_S3 = 700 + 273.15

# Re-solve cycle at the new operating point
h3_S3 = PropsSI("H", "P", P_hi, "T", T3_S3, FLUID)
s3_S3 = PropsSI("S", "P", P_hi, "T", T3_S3, FLUID)
h4s_S3 = PropsSI("H", "P", P_lo, "S", s3_S3, FLUID)
w_t_S3 = eta_t * (h3_S3 - h4s_S3)
h4_S3  = h3_S3 - w_t_S3
q_out_S3 = h4_S3 - h1
w_net_S3 = eta_g * w_t_S3 - w_p
m_dot_S3 = W_net_elec / w_net_S3
Q_out_S3 = m_dot_S3 * q_out_S3

# --- Option A: once-through river dump (dT = 10 K) ---
dT_river_A   = 10.0
m_dot_riverA = Q_out_S3 / (cp_w * dT_river_A)

# --- Option B: passive natural-draft cooling tower ---
# Closed condenser loop sets the heat-exchanger circulation
dT_cond_B = 30.0                             # 20 -> 50 C from figure
m_dot_circ_B = Q_out_S3 / (cp_w * dT_cond_B)

# Psychrometric states (P = 1 atm)
P_atm        = 101325.0
T_air_in_K   = 15.0 + 273.15
phi_in       = 0.35
T_air_out_K  = 35.0 + 273.15
phi_out      = 0.92
T_river_K    = 10.0 + 273.15

# Moist-air constants (per kg dry air, ref 0 C; standard ASHRAE values)
cp_da   = 1.005e3        # J/(kg_da.K)
cp_v    = 1.82e3         # J/(kg_v.K)
hfg_0   = 2501.3e3       # J/kg, latent heat of vaporization at 0 C

def Psat_water(T_K):
    """Saturation pressure of water [Pa] from CoolProp."""
    return PropsSI("P", "T", T_K, "Q", 0, "Water")

def humidity_ratio(T_K, phi, P_total=P_atm):
    """omega = 0.622 * (phi*Psat) / (P - phi*Psat)   [kg_w / kg_da]"""
    Pv = phi * Psat_water(T_K)
    return 0.622 * Pv / (P_total - Pv)

def h_moist(T_K, omega):
    """Moist-air enthalpy per kg dry air, ref 0 C  [J/kg_da]"""
    T_C = T_K - 273.15
    return cp_da * T_C + omega * (hfg_0 + cp_v * T_C)

omega_in  = humidity_ratio(T_air_in_K,  phi_in)
omega_out = humidity_ratio(T_air_out_K, phi_out)
d_omega   = omega_out - omega_in

h_a_in   = h_moist(T_air_in_K,  omega_in)
h_a_out  = h_moist(T_air_out_K, omega_out)

# Liquid-water enthalpy of the river makeup (saturated liquid at 10 C)
h_w_river = PropsSI("H", "T", T_river_K, "Q", 0, "Water")

# Energy balance on tower CV (adiabatic, no shaft work):
#   m_da*(h_a_out - h_a_in) - m_evap*h_w(T_river) = Q_out_S3
# with m_evap = m_da * d_omega
denom         = (h_a_out - h_a_in) - d_omega * h_w_river
m_dot_da_B    = Q_out_S3 / denom
m_dot_evap_B  = m_dot_da_B * d_omega
m_dot_total_B = m_dot_circ_B + m_dot_evap_B

# Tower-side closure check
LHS = m_dot_da_B * (h_a_out - h_a_in) - m_dot_evap_B * h_w_river

print(f"  m_dot_steam       = {m_dot_S3:7.0f} kg/s")
print(f"  Q_out             = {Q_out_S3/1e6:7.2f} MW_th")
print(f"  Tower closure: m_da*(dh_a) - m_evap*h_w(10 C) = {LHS/1e6:.2f} MW vs Q_out = {Q_out_S3/1e6:.2f} MW")
print()
print("  Option A (once-through river dump, dT = 10 K)")
print(f"    m_dot_river       = {m_dot_riverA:8.0f} kg/s   (returned warm; ~0 truly consumed)")
print()
print("  Option B (passive cooling tower; figure: 20->50 C closed loop, air 15/35% -> 35/92%)")
print(f"    P_sat(15 C) / P_sat(35 C) = {Psat_water(T_air_in_K)/1e3:.3f} / {Psat_water(T_air_out_K)/1e3:.3f} kPa")
print(f"    omega_in  (15 C, 35 %)  = {omega_in:.5f} kg_w/kg_da")
print(f"    omega_out (35 C, 92 %)  = {omega_out:.5f} kg_w/kg_da")
print(f"    d_omega                 = {d_omega:.5f} kg_w/kg_da")
print(f"    h_a_in / h_a_out        = {h_a_in/1e3:.2f} / {h_a_out/1e3:.2f} kJ/kg_da")
print(f"    m_dot_dryair      = {m_dot_da_B:8.0f} kg_da/s")
print(f"    m_dot_circulation = {m_dot_circ_B:8.0f} kg/s   (closed loop, 20->50 C)")
print(f"    m_dot_evap (=makeup) = {m_dot_evap_B:7.0f} kg/s   (truly consumed)")
print(f"    m_dot_total       = {m_dot_total_B:8.0f} kg/s   (HX + tower)")
print()
print("  Tower vs once-through (gross flow):")
print(f"    once-through / tower-total = {m_dot_riverA/m_dot_total_B:5.1f}x  (less water moved by tower)")
print(f"    truly consumed by tower    = {m_dot_evap_B:7.0f} kg/s   (vs ~0 by once-through)")