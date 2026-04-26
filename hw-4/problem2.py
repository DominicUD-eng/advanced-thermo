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
fluid = "Air"

P2 = rp * P1      # compressor outlet pressure

def get_props(T, P):
    h = PropsSI("H", "T", T, "P", P, fluid)
    s = PropsSI("S", "T", T, "P", P, fluid)
    return h, s

def solve_cycle(N_turb):
    """
    Solve the Brayton cycle with N_turb turbine stages
    (and N_turb - 1 reheaters) using CoolProp.
    Returns: eta_th, w_net (J/kg), q_in (J/kg), and state data.
    """
    # ── Compressor (single stage) ──
    h1, s1 = get_props(T1, P1)
    h2s = PropsSI("H", "S", s1, "P", P2, fluid)
    h2 = h1 + (h2s - h1) / eta_c
    T2 = PropsSI("T", "H", h2, "P", P2, fluid)

    w_comp = h2 - h1

    # ── Combustor: heat to T_max at P2 ──
    h3, s3 = get_props(T_max, P2)
    q_in = h3 - h2  # combustor heat

    # ── Multi-stage expansion with reheat ──
    rp_stage = rp ** (1.0 / N_turb)
    w_turb_total = 0.0
    P_in = P2  # first turbine inlet pressure
    h_in = h3
    s_in = s3
    T_in = T_max

    for i in range(N_turb):
        P_out = P_in / rp_stage

        # Isentropic expansion
        h_out_s = PropsSI("H", "S", s_in, "P", P_out, fluid)

        # Actual expansion
        h_out = h_in - eta_t * (h_in - h_out_s)
        T_out = PropsSI("T", "H", h_out, "P", P_out, fluid)

        w_turb_total += (h_in - h_out)

        # If not the last stage, reheat back to T_max
        if i < N_turb - 1:
            h_rh_in = h_out
            h_rh_out, s_rh_out = get_props(T_max, P_out)
            q_in += (h_rh_out - h_rh_in)  # reheater heat addition

            # Next turbine stage inlet
            h_in = h_rh_out
            s_in = s_rh_out
            T_in = T_max
        
        P_in = P_out

    w_net = w_turb_total - w_comp
    eta_th = w_net / q_in

    return eta_th, w_net, q_in, w_turb_total, w_comp

# ──────────────────────────────────────────────
# Sweep N_turb = 1 to 10
# ──────────────────────────────────────────────
N_range = range(1, 11)
results = []

print("=" * 70)
print(f"{'N_turb':>6} | {'η_th (%)':>10} | {'W_net (kJ/kg)':>14} | "
      f"{'Q_in (kJ/kg)':>13} | {'W_turb (kJ/kg)':>15} | {'W_comp (kJ/kg)':>15}")
print("-" * 70)

for N in N_range:
    eta, w_net, q_in, w_turb, w_comp = solve_cycle(N)
    results.append((N, eta, w_net, q_in, w_turb, w_comp))
    print(f"{N:>6} | {eta*100:>10.3f} | {w_net/1e3:>14.2f} | "
          f"{q_in/1e3:>13.2f} | {w_turb/1e3:>15.2f} | {w_comp/1e3:>15.2f}")

print("=" * 70)

# ──────────────────────────────────────────────
# Plot: Efficiency vs Number of Turbines
# ──────────────────────────────────────────────
N_vals = [r[0] for r in results]
eta_vals = [r[1] * 100 for r in results]

fig, ax1 = plt.subplots(figsize=(9, 6))

# Primary axis: Efficiency
color1 = "crimson"
ax1.plot(N_vals, eta_vals, "o-", color=color1, linewidth=2.5, markersize=8, label="Thermal Efficiency")
ax1.set_xlabel("Number of Turbine Stages", fontsize=13)
ax1.set_ylabel("Thermal Efficiency, η_th (%)", fontsize=13, color=color1)
ax1.tick_params(axis="y", labelcolor=color1)
ax1.set_xticks(N_vals)
ax1.grid(True, alpha=0.3)

# Secondary axis: Net work and Q_in
ax2 = ax1.twinx()
w_net_vals = [r[2] / 1e3 for r in results]
q_in_vals = [r[3] / 1e3 for r in results]
ax2.plot(N_vals, w_net_vals, "s--", color="royalblue", linewidth=1.5, markersize=6, label="W_net (kJ/kg)")
ax2.plot(N_vals, q_in_vals, "^--", color="orange", linewidth=1.5, markersize=6, label="Q_in (kJ/kg)")
ax2.set_ylabel("Energy (kJ/kg)", fontsize=13)

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=10, loc="center right")

ax1.set_title("Brayton Cycle with Reheat — Efficiency vs. Number of Turbine Stages\n(CoolProp Real Air Properties)", fontsize=13)
plt.tight_layout()
plt.savefig("study2_efficiency_vs_turbines.png", dpi=200)
plt.show()

print("\nPlot saved to study2_efficiency_vs_turbines.png")