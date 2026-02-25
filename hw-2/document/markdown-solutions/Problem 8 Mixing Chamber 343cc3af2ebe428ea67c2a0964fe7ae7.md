# Problem 8: Mixing Chamber

**Exergy**

Liquid water is heated using a mixing chamber that combines it with superheated steam at a constant pressure. Heat loss to the environment is tracked.

### Given Conditions

**Liquid Water Inlet:**

- T = 15 °C
- ṁ = 4 kg/s

**Steam Inlet:**

- T = 200 °C
- P = 200 kPa (mixing chamber pressure)

**Mixed Outlet:**

- T = 80 °C
- P = 200 kPa

**Heat Loss:**

- Q̇ = 600 kJ/min

### PART A

Determine the mass flow rate of the superheated steam.

**1) Control volume + assumptions**

- Steady state mixing chamber at constant pressure, $P = 200\ \text{kPa}$
- Neglect KE/PE changes
- One heat interaction (loss): $\dot Q = -600\ \text{kJ/min} = -10\ \text{kW}$

**2) Property states (use steam tables / IF97)**

Define specific enthalpies:

- Liquid inlet (compressed liquid, use saturated-liquid approx at 15°C):
    - $h_1 \approx h_f(15^{\circ}C)$
    - $s_1 \approx s_f(15^{\circ}C)$
- Steam inlet (superheated at $T_2 = 200^{\circ}C,\ P_2 = 200\ \text{kPa}$):
    - $h_2 = h\left(200^{\circ}C,\ 200\ \text{kPa}\right)$
    - $s_2 = s\left(200^{\circ}C,\ 200\ \text{kPa}\right)$
- Mixed outlet (at $T_3=80^{circ}C, P_3=200 text{kPa}$):
    - Check phase: at $200 text{kPa}$, $T_{sat}approx120.2^{circ}C$, so $T_3 < T_{sat}$ ⇒ **compressed (subcooled) liquid**
    - $h_3 \approx h_f(80^{\circ}C)$
    - $s_3 \approx s_f(80^{\circ}C)$

**3) Mass balance**

Let $\dot m_1=4\ \text{kg/s}$ (liquid), and $\dot m_2$ be the unknown steam flow.

$$
\dot m_3 = \dot m_1 + \dot m_2
$$

**4) Steady-flow energy balance**

For a mixing chamber with no shaft work:

$$
0 = \dot Q + \dot m_1 h_1 + \dot m_2 h_2 - \dot m_3 h_3
$$

Substitute $dot m_3=dot m_1+dot m_2$:

$$
0 = \dot Q + \dot m_1 h_1 + \dot m_2 h_2 - (\dot m_1+\dot m_2)h_3
$$

Solve for $\dot m_2$:

$$
\dot m_2 (h_2-h_3) = \dot m_1 (h_3-h_1) - \dot Q
$$

$$
{\dot m_2 = \dfrac{\dot m_1 (h_3-h_1) - \dot Q}{h_2-h_3}}
$$

Convert to kJ-based units:

- $h_1 = 63171.30\ \text{J/kg} = 63.171\ \text{kJ/kg}$
- $h_2 = 2870730.48\ \text{J/kg} = 2870.730\ \text{kJ/kg}$
- $h_3 = 335133.80\ \text{J/kg} = 335.134\ \text{kJ/kg}$

Compute:

$$
\dot m_1(h_3-h_1)=4\,(335.134-63.171)=4\,(271.963)=1087.85\ \text{kW}
$$

Since $\dot Q=-10\ \text{kW}$ (heat loss),

$$
\dot m_1(h_3-h_1)-\dot Q = 1087.85-(-10)=1097.85\ \text{kW}
$$

Denominator:

$$
h_2-h_3 = 2870.730-335.134 = 2535.596\ \text{kJ/kg}
$$

Therefore:

$$
\boxed{\dot m_2=\frac{1097.85}{2535.596}=0.433\ \text{kg/s}}
$$

---

### PART B

Determine the rate of lost work potential caused by this mixing process.

The **lost work potential rate** is the **exergy destruction rate**:

$$
\dot W_{lost} = \dot X_{dest} = T_0\,\dot S_{gen}
$$

where $T_0$ is the environment (dead-state) temperature in K.

**1) Choose dead state**

$$
T_0 = 25^{\circ}C = 298.15\ \text{K},\qquad p_0 = 100\ \text{kPa}\ (\text{or local atmospheric})
$$

**2) Entropy rate balance (steady CV)**

$$
0 = \sum \frac{\dot Q_j}{T_j} + \sum \dot m_{in} s_{in} - \sum \dot m_{out} s_{out} + \dot S_{gen}
$$

Here there is one heat loss to the surroundings. If the heat crosses the boundary at approximately the ambient boundary temperature, take $T_b \approx T_0$:

$$
\dot S_{gen} = \dot m_3 s_3 - \dot m_1 s_1 - \dot m_2 s_2 - \frac{\dot Q}{T_b}
$$

with $\dot m_3=\dot m_1+\dot m_2$ and $\dot Q=-10\ \text{kW}$.

**Numerical evaluation (using your CoolProp results at** $P=200\ \text{kPa}$**)**

Convert to kJ/kg-K:

- $s_1 = 224.433\ \text{J/kg-K} = 0.224433\ \text{kJ/kg-K}$
- $s_2 = 7508.072\ \text{J/kg-K} = 7.508072\ \text{kJ/kg-K}$
- $s_3 = 1075.478\ \text{J/kg-K} = 1.075478\ \text{kJ/kg-K}$

Mass flow rates:

- $\dot m_1 = 4.000\ \text{kg/s}$
- $\dot m_2 = 0.433\ \text{kg/s}$ (from Part A)
- $\dot m_3 = 4.433\ \text{kg/s}$

Take $T_b \approx T_0 = 298.15\ \text{K}$.

Compute the entropy rate terms:

$$
\dot m_3 s_3 = 4.433(1.075478)=4.767\ \text{kW/K}
$$

$$
\dot m_1 s_1 = 4(0.224433)=0.898\ \text{kW/K}
$$

$$
\dot m_2 s_2 = 0.433(7.508072)=3.251\ \text{kW/K}
$$

Heat-transfer entropy term:

$$
-\frac{\dot Q}{T_b}=-\frac{-10}{298.15}=0.0335\ \text{kW/K}
$$

So

$$
\dot S_{gen}=4.767-0.898-3.251+0.0335=0.6515\ \text{kW/K}
$$

Finally,

$$
\boxed{\dot W_{lost}=T_0\dot S_{gen}=298.15(0.6515)=194\ \text{kW}}
$$