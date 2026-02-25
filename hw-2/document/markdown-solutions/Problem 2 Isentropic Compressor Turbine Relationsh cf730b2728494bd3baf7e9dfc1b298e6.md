# Problem 2: Isentropic Compressor/Turbine Relationships

### Problem Statement

Using the T-ds equations and ideal-gas relationships and assuming constant specific heats, derive the predictive relationships for the performance of isentropic compressors / turbines for ideal gases. Additionally comment on the weaknesses of this prediction and where you would differ.

**Required relationships:**

- $\frac{T_2}{T_1} = f(P_2, P_1, k)$
- $\frac{T_2}{T_1} = f(v_2, v_1, k)$
- $\frac{P_2}{P_1} = f(v_1, v_2, k)$

---

### Solution

1.

$$
0 = C_v dT + P dv
$$

$$
\frac{RT}{v} dv + C_v dT =0
$$

$$
\int_1^2\frac{C_v  dT}{T} +\int_1^2\frac{R  dv}{v} =0
$$

Assume constant specific heat, now integrate from state 1 to state 2:

$$
⁍
$$

Use $R = C_p - C_v$ and $k = C_p/C_v$:

$$
⁍
$$

Divide by $C_v$:

$$
⁍
$$

Therefore:

$$
⁍
$$

2.

$$
0 = C_p dT - v dP
$$

$$
-v dP + C_p dT
$$

$$
\frac{RT}{P} dP = C_p dT
$$

$$
\int\frac{R}{P} dP = \int\frac{C_p dT}{T}
$$

$$
R\ln(P_2/P_1) = C_p \ln(T_2/T_1)
$$

$$
\frac{R}{C_p}\ln(P_2/P_1) = \ln(T_2/T_1) = \frac{C_p-C_v}{C_p}\ln(P_2/P_1)
$$

$$
\frac{R}{C_p}\ln(P_2/P_1) = \ln(T_2/T_1) = \frac{C_p-C_v}{C_p}\ln(P_2/P_1) = (1-\frac{1}{k})\ln(P_2/P_1)
$$

$$
(P_2/P_1)^{(\frac{k-1}{k})}=T_2/T_1
$$

3.

$$
(P_2/P_1)^{(\frac{k-1}{k})}=T_2/T_1=(v_2/v_1)^{k-1}
$$

$$
(P_2/P_1)^{(\frac{k-1}{k})}=(v_2/v_1)^{k-1}
$$

$$
(P_2/P_1)^{(\frac{1}{k})}=(v_2/v_1)
$$

$$
(P_2/P_1)=(v_2/v_1)^k
$$

Commentary:

the assumptions needed are that specific heats are constant w.r.t temperature and that the turbine/compressor is operating reversibly with an ideal gas. these assumptions are not realistic in any practical application. turbines and compressors are almost never isentropic and the purpose is compression/expansion indicating high pressure regions, far from ideal gas fluid regimes.

A.I.:

**End Result - Three Key Relationships:**

You need to derive the following three equations that predict the performance of isentropic compressors and turbines for ideal gases:

1. **Temperature-Pressure Relationship:** $\frac{T_2}{T_1} = \left(\frac{P_2}{P_1}\right)^{\frac{k-1}{k}}$
2. **Temperature-Volume Relationship:** $\frac{T_2}{T_1} = \left(\frac{v_1}{v_2}\right)^{k-1}$
3. **Pressure-Volume Relationship:** $\frac{P_2}{P_1} = \left(\frac{v_1}{v_2}\right)^{k}$

These relationships allow you to predict how temperature, pressure, and specific volume change across an isentropic compressor or turbine when you know the inlet conditions and one outlet property.

### Background Information

**Ideal Gas Relationships:**

- Ideal gas law: $Pv = RT$
- Relationship between properties: $P v^k = \text{constant}$ (for isentropic process)
- Specific heat ratio: $k = \frac{c_p}{c_v}$
- Gas constant relation: $R = c_p - c_v$

**T-ds Equations (Gibbs Equations):**

For this derivation, you should start with the first T-ds equation:

- $T \, ds = du + P \, dv$

Or alternatively, the second T-ds equation:

- $T \, ds = dh - v \, dP$

**Additional useful relationships for ideal gases with constant specific heats:**

- $du = c_v \, dT$
- $dh = c_p \, dT$

For an **isentropic process**, recall that $ds = 0$, which simplifies the T-ds equations considerably and allows you to derive the required relationships.

---