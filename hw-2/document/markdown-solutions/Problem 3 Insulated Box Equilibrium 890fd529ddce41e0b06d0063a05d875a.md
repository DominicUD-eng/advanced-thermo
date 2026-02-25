# Problem 3: Insulated Box Equilibrium

### Problem Statement

An insulated box is initially divided into two halves by a frictionless, thermally conductive actuated wall. The piston is suddenly released and equilibrium between the two gases is fully attained.

**Initial Conditions:**

- **Left side (Air):** V = 1.5 m³, P = 4 bar, T = 400 K
- **Right side (Also Air):** V = 1.5 m³, P = 2 bar, T = 400 K
- Wall is suddenly removed

**Parts:**

- **Part A:** Determine the final temperature in K
- **Part B:** Determine the final pressure in bar
- **Part C:** Determine the quantity of energy production
- **Part D:** Comment on what caused this entropy production to occur

---

### Solution

#### Part A: Final Temperature

The system is in free expansion (no work) and insulated (no heat) therefore internal energy is conserved and the temperature is constant. $400 \space\text K$.

#### Part B: Final Pressure

$$
\frac{4*1.5}{8.314 * 400} = 0.0018042 \space\text {mol}
$$

$$
\frac{2*1.5}{8.314 * 400} = 0.0009028 \space\text {mol}
$$

$$
\frac{8.314\space\text{J/(mol K)}*0.00270628\space\text{mol}*400\space\text K }{3\space\text m^3} = 3 \space\text{bar}
$$

#### Part C: Energy Production

$$
\Delta U = Q - W = 0
$$

Therefore, the energy production is **zero**.

#### Part D: Entropy Production Analysis

For an ideal gas undergoing free expansion into a vacuum (or pressure equalization), we use:

$$
\Delta S = nC_v \ln\left(\frac{T_f}{T_i}\right) + nR\ln\left(\frac{V_f}{V_i}\right)
$$

Since temperature is constant (T_f = T_i = 400 K), the first term vanishes:

$$
\Delta S = nR\ln\left(\frac{V_f}{V_i}\right)
$$

**For the left side (high pressure air):**

$$
\Delta S_L = 0.0018042 \times 8.314 \times \ln\left(\frac{3}{1.5}\right) = 0.0104 \space\text{kJ/K}
$$

**For the right side (low pressure air):**

$$
\Delta S_R = 0.0009028 \times 8.314 \times \ln\left(\frac{3}{1.5}\right) = 0.0052 \space\text{kJ/K}
$$

**Total entropy production:**

$$
\Delta S_{total} = \Delta S_L + \Delta S_R = 0.0156 \space\text{kJ/K}
$$

**What caused this entropy production?**

The entropy production occurs due to the **irreversible mixing and pressure equalization** of two gases at different pressures. Even though both sides contain air at the same temperature, the pressure difference creates a thermodynamic disequilibrium. When the wall is removed, the gases spontaneously expand and mix to reach mechanical equilibrium.

This is an **irreversible process** because:

- Work potential was lost (the pressure difference could have been used to do work via a piston)
- The mixing occurred spontaneously without any controlled energy transfer
- The system cannot return to its initial state without external intervention

The Second Law of Thermodynamics requires ΔS_universe ≥ 0 for any real process. Since the system is isolated (Q = 0), all entropy production stays within the system, confirming the irreversibility of free expansion.