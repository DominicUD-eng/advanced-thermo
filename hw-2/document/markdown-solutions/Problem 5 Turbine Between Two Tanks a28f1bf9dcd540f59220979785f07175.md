# Problem 5: Turbine Between Two Tanks

**Entropy and Other Things**

A turbine is located between two tanks. Initially the smaller tank is pressurized while the larger tank is fully evacuated. Assume the heat transfer with the surroundings is negligible. Steam is allowed to flow from the smaller tank, through the turbine, and into the larger tank until equilibrium is attained. If the turbine is ideal during its expansion process, determine:

### Initial Conditions

**Small Tank (100 m³):**

- At t = 0: Steam at 3.0 MPa and 280 °C

**Large Tank (1000 m³):**

- At t = 0: Pure Vacuum

### PART A

What are the equilibrium conditions in both tanks (T, P, m_s)?

### Detailed Calculations with Proper Notation

### Step 1: Initial Properties of Small Tank

Given initial conditions:

$$
T_1 = 280°C = 553.15 \text{ K}
$$

$$
P_1 = 3.0 \text{ MPa} = 3{,}000{,}000 \text{ Pa}
$$

$$
V_{\text{small}} = 100 \text{ m}^3
$$

From CoolProp output:

$$
\rho_1 = 12.9598 \text{ kg/m}^3
$$

$$
u_1 = 2{,}710{,}698.33 \text{ J/kg}
$$

Calculate specific volume:

$$
v_1 = \frac{1}{\rho_1} = \frac{1}{12.9598} = 0.07716 \text{ m}^3\text{/kg}
$$

### Step 2: Initial Mass in Small Tank

$$
m_1 = \frac{V_{\text{small}}}{v_1} = \frac{100}{0.07716} = 1{,}296.0 \text{ kg}
$$

### Step 3: Conservation Principles

**Conservation of Mass:**

$$
m_{\text{total}} = m_1 = 1{,}296.0 \text{ kg}
$$

**Conservation of Energy** (adiabatic system, rigid tanks):

$$
U_{\text{initial}} = U_{\text{final}}
$$

$$
m_1 u_1 = m_{\text{total}} u_f
$$

Therefore, the final specific internal energy:

$$
u_f = \frac{m_1 u_1}{m_{\text{total}}} = u_1 = 2{,}710{,}698.33 \text{ J/kg}
$$

### Step 4: Final Specific Volume

Total volume of both tanks:

$$
V_{\text{total}} = V_{\text{small}} + V_{\text{large}} = 100 + 1{,}000 = 1{,}100 \text{ m}^3
$$

Final specific volume at equilibrium:

$$
v_f = \frac{V_{\text{total}}}{m_{\text{total}}} = \frac{1{,}100}{1{,}296.0} = 0.8488 \text{ m}^3\text{/kg}
$$

$$
\rho_f = \frac{1}{v_f} = \frac{1}{0.8488} = 1.1781 \text{ kg/m}^3
$$

$$
\rho = 1.1781 \text{ kg/m}^3
$$

$$
u = 2{,}710{,}698.33 \text{ J/kg}
$$

$$
T_f = 510.9918 \text{ K} = 237.84^\circ\text{C}
$$

$$
P_f = 274{,}926.80 \text{ Pa} = 0.27493 \text{ MPa}
$$

$$
m_{\text{small,final}} = \frac{V_{\text{small}}}{v_f} = \frac{100}{0.8488} = 117.8 \text{ kg}
$$

$$
m_{\text{large,final}} = \frac{V_{\text{large}}}{v_f} = \frac{1{,}000}{0.8488} = 1{,}178.2 \text{ kg}
$$

Check: 

$$
m_{\text{small,final}} + m_{\text{large,final}} = 117.8 + 1{,}178.2 = 1{,}296.0 \text{ kg}
$$

### PART B

What is the maximum theoretical work that could be extracted from the turbine?

### Step 1: Identify the Process

For an ideal turbine operating adiabatically and reversibly, the process is isentropic (constant entropy).

The maximum theoretical work occurs when the turbine operates reversibly between the initial state and the final state at the same specific entropy.

### Step 2: Initial State Properties

From the initial conditions in the small tank:

$$
P_1 = 3.0 \text{ MPa} = 3{,}000{,}000 \text{ Pa}
$$

$$
T_1 = 280°C = 553.15 \text{ K}
$$

$$
u_1 = 2{,}710{,}698.33 \text{ J/kg}
$$

From CoolProp output:

$$
s_1 = 6{,}448.57 \text{ J/(kg K)}
$$

### Step 3: Final State Properties (Isentropic Expansion)

The steam expands isentropically to the final density:

$$
\rho_f = 1.1781 \text{ kg/m}^3
$$

$$
s_2 = s_1 = 6{,}448.57 \text{ J/(kg K)}
$$

From CoolProp output at 

$$
s = 6{,}448.57 \text{ J/(kg K)}
$$

 and 

$$
\rho = 1.1781 \text{ kg/m}^3
$$

:

$$
T_2 = 390.30 \text{ K} = 117.15°\text{C}
$$

$$
P_2 = 181{,}372.43 \text{ Pa} = 0.18137 \text{ MPa}
$$

$$
u_2 = 2{,}270{,}315.48 \text{ J/kg}
$$

### Step 4: Calculate Maximum Work per Unit Mass

The maximum theoretical work extracted per kilogram of steam flowing through the turbine:

$$
w_{\text{turbine}} = u_1 - u_2
$$

$$
w_{\text{turbine}} = 2{,}710{,}698.33 - 2{,}270{,}315.48
$$

$$
w_{\text{turbine}} = 440{,}382.85 \text{ J/kg}
$$

### Step 5: Total Mass Flow Through Turbine

All the steam initially in the small tank flows through the turbine:

$$
m_{\text{flow}} = m_1 = 1{,}296.0 \text{ kg}
$$

### Step 6: Maximum Total Work Output

The maximum theoretical work that could be extracted from the turbine:

$$
W_{\text{max}} = m_{\text{flow}} \times w_{\text{turbine}}
$$

$$
W_{\text{max}} = 1{,}296.0 \times 440{,}382.85
$$

$$
W_{\text{max}} = 570{,}736{,}254 \text{ J}
$$

$$
W_{\text{max}} = 570.74 \text{ MJ}
$$

### Final Answer

**The maximum quantity of theoretical work that could be extracted from the turbine is 570.74 MJ (or approximately 571 MJ).**