import numpy as np
import matplotlib.pyplot as plt
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
N_turb = 2        # number of turbine stages (1 reheat)

# Pressures
P2 = rp * P1                          # compressor outlet
P3 = P2                               # combustor is isobaric
rp_stage = rp ** (1.0 / N_turb)       # pressure ratio per turbine stage
P4 = P3 / rp_stage                    # after first turbine
P5 = P4                               # reheater is isobaric
P6 = P5 / rp_stage                    # after second turbine (= P1)

# ──────────────────────────────────────────────
# SCENARIO A: Constant Specific Heat (Ideal Gas)
# ──────────────────────────────────────────────
k = 1.4
cp = 1005.0  # J/(kg·K)
R_air = 287.0  # J/(kg·K)

def s_ideal(T, P, T_ref=300.0, P_ref=101325.0, s_ref=0.0):
    """Entropy for ideal gas with constant cp."""
    return s_ref + cp * np.log(T / T_ref) - R_air * np.log(P / P_ref)

# State 1
T1_id = T1
P1_id = P1

# State 2 (compressor)
T2s_id = T1_id * rp ** ((k - 1) / k)
T2_id = T1_id + (T2s_id - T1_id) / eta_c
P2_id = P2

# State 3 (combustor outlet)
T3_id = T_max
P3_id = P3

# State 4 (first turbine outlet)
T4s_id = T3_id * (1.0 / rp_stage) ** ((k - 1) / k)
T4_id = T3_id - eta_t * (T3_id - T4s_id)
P4_id = P4

# State 5 (reheater outlet)
T5_id = T_max
P5_id = P5

# State 6 (second turbine outlet)
T6s_id = T5_id * (1.0 / rp_stage) ** ((k - 1) / k)
T6_id = T5_id - eta_t * (T5_id - T6s_id)
P6_id = P6

# Entropy at each state
s1_id = s_ideal(T1_id, P1_id)
s2_id = s_ideal(T2_id, P2_id)
s3_id = s_ideal(T3_id, P3_id)
s4_id = s_ideal(T4_id, P4_id)
s5_id = s_ideal(T5_id, P5_id)
s6_id = s_ideal(T6_id, P6_id)

# Performance
w_comp_id = cp * (T2_id - T1_id)          # J/kg
w_turb1_id = cp * (T3_id - T4_id)
w_turb2_id = cp * (T5_id - T6_id)
w_net_id = (w_turb1_id + w_turb2_id) - w_comp_id

q_comb_id = cp * (T3_id - T2_id)          # combustor
q_rh_id = cp * (T5_id - T4_id)            # reheater
q_in_id = q_comb_id + q_rh_id

eta_id = w_net_id / q_in_id

states_id = {
    1: (T1_id, P1_id, s1_id),
    2: (T2_id, P2_id, s2_id),
    3: (T3_id, P3_id, s3_id),
    4: (T4_id, P4_id, s4_id),
    5: (T5_id, P5_id, s5_id),
    6: (T6_id, P6_id, s6_id),
}

print("=" * 60)
print("SCENARIO A: Constant Specific Heat (Ideal Gas)")
print("=" * 60)
for st, (T, P, s) in states_id.items():
    print(f"  State {st}: T = {T:.2f} K,  P = {P:.0f} Pa,  s = {s:.2f} J/(kg·K)")
print(f"\n  W_comp   = {w_comp_id/1e3:.2f} kJ/kg")
print(f"  W_turb1  = {w_turb1_id/1e3:.2f} kJ/kg")
print(f"  W_turb2  = {w_turb2_id/1e3:.2f} kJ/kg")
print(f"  W_net    = {w_net_id/1e3:.2f} kJ/kg")
print(f"  Q_in     = {q_in_id/1e3:.2f} kJ/kg")
print(f"  η_th     = {eta_id * 100:.2f} %")
print(f"  W_net_dot= {m_dot * w_net_id / 1e6:.2f} MW")

# ──────────────────────────────────────────────
# SCENARIO B: Real Air Properties (CoolProp)
# ──────────────────────────────────────────────
fluid = "Air"

def get_props(T, P):
    h = PropsSI("H", "T", T, "P", P, fluid)
    s = PropsSI("S", "T", T, "P", P, fluid)
    return h, s

# State 1
h1, s1 = get_props(T1, P1)

# State 2s (isentropic compression)
h2s = PropsSI("H", "S", s1, "P", P2, fluid)
T2s_real = PropsSI("T", "S", s1, "P", P2, fluid)
# State 2 (actual)
h2 = h1 + (h2s - h1) / eta_c
T2_real = PropsSI("T", "H", h2, "P", P2, fluid)
_, s2 = get_props(T2_real, P2)

# State 3
h3, s3 = get_props(T_max, P3)

# State 4s (isentropic expansion, first turbine)
h4s = PropsSI("H", "S", s3, "P", P4, fluid)
# State 4 (actual)
h4 = h3 - eta_t * (h3 - h4s)
T4_real = PropsSI("T", "H", h4, "P", P4, fluid)
_, s4 = get_props(T4_real, P4)

# State 5 (reheat back to T_max)
h5, s5 = get_props(T_max, P5)

# State 6s (isentropic expansion, second turbine)
h6s = PropsSI("H", "S", s5, "P", P6, fluid)
# State 6 (actual)
h6 = h5 - eta_t * (h5 - h6s)
T6_real = PropsSI("T", "H", h6, "P", P6, fluid)
_, s6 = get_props(T6_real, P6)

# Performance
w_comp_real = h2 - h1
w_turb1_real = h3 - h4
w_turb2_real = h5 - h6
w_net_real = (w_turb1_real + w_turb2_real) - w_comp_real
q_in_real = (h3 - h2) + (h5 - h4)
eta_real = w_net_real / q_in_real

states_real = {
    1: (T1,      P1, h1, s1),
    2: (T2_real, P2, h2, s2),
    3: (T_max,   P3, h3, s3),
    4: (T4_real, P4, h4, s4),
    5: (T_max,   P5, h5, s5),
    6: (T6_real, P6, h6, s6),
}

print("\n" + "=" * 60)
print("SCENARIO B: Real Air Properties (CoolProp)")
print("=" * 60)
for st, (T, P, h, s) in states_real.items():
    print(f"  State {st}: T = {T:.2f} K,  P = {P:.0f} Pa,  "
          f"h = {h/1e3:.2f} kJ/kg,  s = {s:.2f} J/(kg·K)")
print(f"\n  W_comp   = {w_comp_real/1e3:.2f} kJ/kg")
print(f"  W_turb1  = {w_turb1_real/1e3:.2f} kJ/kg")
print(f"  W_turb2  = {w_turb2_real/1e3:.2f} kJ/kg")
print(f"  W_net    = {w_net_real/1e3:.2f} kJ/kg")
print(f"  Q_in     = {q_in_real/1e3:.2f} kJ/kg")
print(f"  η_th     = {eta_real * 100:.2f} %")
print(f"  W_net_dot= {m_dot * w_net_real / 1e6:.2f} MW")

# ──────────────────────────────────────────────
# T-s DIAGRAM
# ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 7))

# --- Plot isobars (CoolProp) ---
T_range = np.linspace(250, 1350, 300)
pressures = sorted(set([P1, P2, P4]))  # P1=P6, P2=P3, P4=P5
colors_isobar = {P1: "gray", P4: "gray", P2: "gray"}
for Pi in pressures:
    s_iso = [PropsSI("S", "T", Ti, "P", Pi, fluid) for Ti in T_range]
    label = f"P = {Pi/1e3:.0f} kPa"
    ax.plot(s_iso, T_range, "--", color="lightgray", linewidth=0.8, label=label)

# --- Saturation lines for AIR (liquid & vapor) ---
# Compute pure-Air saturation (Q=0 and Q=1) over T from low temps up to critical.
try:
    Tcrit_air = PropsSI("Tcrit", "Air")
    T_sat_air = np.linspace(60.0, Tcrit_air * 0.999, 400)
    s_sat_liq_air = []
    s_sat_vap_air = []
    T_plot_air = []
    for Ti in T_sat_air:
        try:
            s_liq = PropsSI("S", "T", Ti, "Q", 0, "Air")
            s_vap = PropsSI("S", "T", Ti, "Q", 1, "Air")
            s_sat_liq_air.append(s_liq)
            s_sat_vap_air.append(s_vap)
            T_plot_air.append(Ti)
        except Exception:
            # skip temperatures where saturation props unavailable
            continue
    if len(T_plot_air) > 2:
        ax.plot(s_sat_liq_air, T_plot_air, color="tab:green", linewidth=1.2, label="Air saturated liquid")
        ax.plot(s_sat_vap_air, T_plot_air, color="tab:olive", linewidth=1.2, label="Air saturated vapor")
        ax.fill_betweenx(T_plot_air, s_sat_liq_air, s_sat_vap_air, color="lightgreen", alpha=0.15, label="Air vapor dome (pure Air)")
except Exception:
    # If Air saturation not available, do nothing (no extra imports added)
    pass
# --- Ideal gas cycle path ---
T_cyc_id = [T1_id, T2_id, T3_id, T4_id, T5_id, T6_id, T1_id]
s_cyc_id = [s1_id, s2_id, s3_id, s4_id, s5_id, s6_id, s1_id]
ax.plot(s_cyc_id, T_cyc_id, "o-", color="royalblue", linewidth=2, markersize=6,
        label=f"Ideal Gas (η = {eta_id*100:.2f}%)")

# --- CoolProp cycle path ---
T_cyc_r = [T1, T2_real, T_max, T4_real, T_max, T6_real, T1]
s_cyc_r = [s1, s2, s3, s4, s5, s6, s1]
ax.plot(s_cyc_r, T_cyc_r, "s-", color="crimson", linewidth=2, markersize=6,
        label=f"CoolProp Real Air (η = {eta_real*100:.2f}%)")

# Annotate states (CoolProp)
for st, (T, P, h, s) in states_real.items():
    ax.annotate(f" {st}", (s, T), fontsize=11, fontweight="bold", color="crimson")

for st, (T, P, s) in states_id.items():
    ax.annotate(f" {st}", (s, T), fontsize=11, fontweight="bold", color="royalblue",
                xytext=(5, -12), textcoords="offset points")

ax.set_xlabel("Specific Entropy, s [J/(kg·K)]", fontsize=12)
ax.set_ylabel("Temperature, T [K]", fontsize=12)
ax.set_title("T-s Diagram — Brayton Cycle with Reheat (Study 1)", fontsize=14)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("study1_Ts_diagram.png", dpi=200)
plt.show()

print("\nPlot saved to study1_Ts_diagram.png")