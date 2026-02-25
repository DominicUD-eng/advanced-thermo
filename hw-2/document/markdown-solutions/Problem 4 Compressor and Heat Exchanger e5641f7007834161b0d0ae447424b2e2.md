# Problem 4: Compressor and Heat Exchanger

Air flows through a compressor and heat exchanger. A separate liquid water stream also flows through the heat exchanger. The system operates at pseudo-steady state. Assume individual components are well insulated relative to the environment.

### Given Conditions

**Air Stream:**

- Inlet: P = 96 kPa, T = 27 °C, Q̇ = 26.91 m³/min
- Compressor outlet: P = 230 kPa, T = 127 °C
- Heat exchanger outlet: Assume Isobaric, T = 77 °C

**Water Stream:**

- Inlet: P_atm, T = 25 °C
- Outlet: Assume Isobaric, T = 40 °C

### PART A

Determine the required compressor power and the mass flow rate of cooling water

**Assumptions:**

- Pseudo-steady state operation
- Negligible kinetic and potential energy changes (ΔKE ≈ 0, ΔPE ≈ 0)
- Components are well-insulated (Q̇ ≈ 0 to environment)
- Air behaves as an ideal gas
- Water is incompressible liquid
- No shaft work in heat exchanger

$$
ṁ_{air} × h₁ + Ẇ_{comp} = ṁ_{air} × h₂
$$

$$
Ẇ_{comp} = ṁ_{air} × (h₂ - h₁)
$$

and

$$
ṁ_{air} × h₂ + ṁ_{water} × h_{water,in} = ṁ_{air} × h₃ + ṁ_{water} × h_{water,out}
$$

$$
ṁ_{air} × h₂ + ṁ_{water} × h_{water,in} = ṁ_{air} × h₃ + ṁ_{water} × h_{water,out}
$$

**For Air:**

- h₁ at T₁ = 27 °C = 300 K → **$h_1 = 426309.837 \space J/kg$**
- h₂ at T₂ = 127 °C = 400 K → $h_2 = 527107.689 \space J/kg$
- h₃ at T₃ = 77 °C = 350 K → $h_3 = 476472.292 \space J/kg$
- density at inlet = 1.1151220021248
- $\dot{m}=\dot{Q}\rho = 0.5 \space kg/s$

**For Water:**

- $h_{w,i} = 104920.1198\space J/kg$
- $h_{w,o} = 167616.2859\space J/kg$

For the heat exchanger, since water is incompressible and temperature changes are modest, you can directly use:

$$
ṁ_{water} = \frac{ṁ_{air} × (h₂ - h₃)}{c_{p,water} × (T_{water,out} - T_{water,in})}
$$

where c_p,water = 4.18 kJ/(kg·K)

$$
ṁ_{water} = \frac{0.5 × (527107.689 - 476472.292)}{4180 × (313.15 - 298.15)}
$$

$$
ṁ_{water} = 0.4403\space kg/s
$$

**Compressor Power Calculation:**

$$
Ẇ_{comp} = ṁ_{air} × (h₂ - h₁)
$$

$$
Ẇ_{comp} = 0.5 × (527107.689 - 426309.837)
$$

$$
Ẇ_{comp} = 0.5 × 100797.852
$$

$$
Ẇ_{comp} = 50398.926 \space W = 50.4 \space kW
$$

**Summary of Part A Results:**

- **Compressor Power:** Ẇ_comp = 50.4 kW
- **Water Mass Flow Rate:** ṁ_water = 0.4403 kg/s

### PART B

Determine the entropy production rates for the compressor and heat exchanger

$$
\dot{S}_{gen,comp}=\dot{m}_{air}\times (s_2-s_1)
$$

$$
\dot{S}_{gen,comp}=(0.5)* (3941.3529-3902.2459)
$$

$$
\dot{S}_{gen,comp}=19.5535\space W/K
$$

$$
\dot{S}_{gen,HX}=\dot{m}_{air}\times (s_3-s_2) + \dot{m}_{w}\times(s_{w,o}-s_{w,i})
$$

$$
\dot{S}_{gen,HX}=(0.5)* (3806.1314-3941.3529) + (0.4403)*(572.3652-367.1996)
$$

$$
\dot{S}_{gen,comp}=22.72366\space W/K
$$

### PART C

- **Compressor:** Irreversibilities due to friction, non-ideal compression process, and finite temperature differences within the device
- **Heat Exchanger:** Finite temperature difference between hot air and cold water streams driving heat transfer (thermal irreversibility)