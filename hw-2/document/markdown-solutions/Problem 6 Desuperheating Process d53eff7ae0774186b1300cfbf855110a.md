# Problem 6: Desuperheating Process

Liquid water is injected into a superheated vapor to produce a saturated vapor.

### Given Conditions

**Injected Water:**

- P = 0.3 MPa
- ṁ = 6.37 kg/min

**Steam Inlet:**

- P = 0.3 MPa
- T = 200 °C

**Vapor Outlet:**

- P = 0.3 MPa (Saturated Vapor)

### PART A

Determine the mass flow rate of the superheated vapor stream

$$
ṁ_{steam} = \frac{ṁ_{water} \times (h_{sat,vapor} - h_{water})}{h_{steam} - h_{sat,vapor}}
$$

$$
ṁ_{steam} = \frac{6.37\,\text{kg/min} \times \left(2724882.6303 - 561426.6778\right)\,\text{J/kg}}{\left(2865890.6540 - 2724882.6303\right)\,\text{J/kg}}
= 97.7\,\text{kg/min}
$$

### PART B

Determine the rate of entropy production within the system.

$$
\dot{S}_{gen} = (\dot{m}_{water} + \dot{m}_{steam})\, s_{sat,vapor} - \dot{m}_{water}\, s_{water} - \dot{m}_{steam}\, s_{steam}
$$

$$
\dot{S}_{gen} = (6.37 + 97.7)\,\text{kg/min} \times 6991.6171\,\text{J/(kg K)} \\
-\; 6.37\,\text{kg/min} \times 1671.7187\,\text{J/(kg K)} \\
-\; 97.7\,\text{kg/min} \times 7313.1252\,\text{J/(kg K)} \\
= 2.48\times 10^{3}\,\text{J/(min K)}
$$

$$
\dot{S}_{gen} = 0.0413\,\text{kW/K}
$$