# Problem 9: Heating Method Exergy Comparison

## Problem Statement

The temperature of the air in a building can be maintained at a desirable level during winter by using different methods of heating. Compare indirectly heating this air in a heat exchanger unit with condensing steam to heating the air directly via an electric resistance heater. Play with exergy analyses to prove which heating method results in the least exergy destruction method. You will need to perform some research regarding temperatures and operating characteristics of these systems.

## Given Information

- Building air heating requirement (winter)
- Two heating methods to compare:
    1. **Indirect heating**: Heat exchanger with condensing steam
    2. **Direct heating**: Electric resistance heater

## Required

- Perform exergy analysis for both heating methods
- Determine which method has **least exergy destruction**
- Research typical temperatures and operating characteristics

## Assumptions

- Steady state.
- Air behaves as an ideal gas.
- Indoor air is maintained at $T_{in}=25°C=298.15\ \mathrm{K}$.
- Environment (dead state): $T_0 = 0°C = 273.15\ \mathrm{K}$, $p_0 = 1\ \mathrm{atm}$ (typical winter design condition).
- Same useful heating delivered in both cases: $\dot Q_{load}$ is identical for both systems.
- Electric resistance heater has $\eta_{elec \to heat} = 1$ (all electrical work converted to heat).
- Steam heat source behaves as a condensing reservoir at constant $T_s$.
- Neglect KE and PE effects.
- No auxiliary work (fans, pumps) and no casing heat losses.
- **Point-of-use analysis only** — upstream losses (boiler efficiency, power plant losses) are not included.

## Key equations

Exergy rate transfer with heat across a boundary at $T_b$:

$$
\dot X_Q=\left(1-\frac{T_0}{T_b}\right)\dot Q
$$

Exergy destruction rate:

$$
\dot X_{dest}=T_0\dot S_{gen}
$$

## System 1: Steam condensing HX (heat input at $T_s$)

Exergy in with supplied heat:

$$
\dot X_{in,steam}=\left(1-\frac{T_0}{T_s}\right)\dot Q_{load}
$$

Exergy out to the room:

$$
\dot X_{out,room}=\left(1-\frac{T_0}{T_{in}}\right)\dot Q_{load}
$$

Exergy destruction in the heating process:

$$
\dot X_{dest,steam}=\dot X_{in,steam}-\dot X_{out,room}
$$

So,

$$
\boxed{\dot X_{dest,steam}=\dot Q_{load}T_0\left(\frac{1}{T_{in}}-\frac{1}{T_s}\right)}
$$

## System 2: Electric resistance heater (work input)

$$
\dot W_{elec,in}=\dot Q_{load}
$$

Exergy in:

$$
\dot X_{in,elec}=\dot W_{elec,in}=\dot Q_{load}
$$

Exergy destruction:

$$
\boxed{\dot X_{dest,elec}=\dot Q_{load}-\left(1-\frac{T_0}{T_{in}}\right)\dot Q_{load}=\dot Q_{load}\frac{T_0}{T_{in}}}
$$

## Difference

$$
\boxed{\Delta\dot X_{dest}=\dot X_{dest,elec}-\dot X_{dest,steam}}
$$

## Energy (equal $\dot Q_{load}$)

$$
\boxed{\dot E_{in,elec}=\dot E_{in,steam}=\dot Q_{load}}
$$

## Analysis

To perform a simple comparison, we'll use typical operating parameters from real-world heating systems:

### Typical Operating Parameters

- **Steam heating system:** Low-pressure steam condensing at approximately T_s = 120°C = 393.15 K (common for building HVAC systems) [Engineering ToolBox - Saturated Steam Properties (SI)](https://www.engineeringtoolbox.com/saturated-steam-properties-d_101.html)
- **Indoor air temperature:** T_in = 25°C = 298.15 K (already assumed)
- **Environment (dead state):** Winter ambient temperature T_0 = 0°C = 273.15 K (typical winter design condition) [ASHRAE Climatic Design Conditions](https://ashrae-meteo.info/)

### Normalized Comparison (per unit $\dot Q_{load}$)

**System 1: Steam Condensing HX**

$$
\frac{\dot X_{dest,steam}}{\dot Q_{load}} = T_0 \left(\frac{1}{T_{in}} - \frac{1}{T_s}\right)
$$

$$
= 273.15 \left(\frac{1}{298.15} - \frac{1}{393.15}\right)
$$

$$
= 273.15 \times (0.003354 - 0.002544)
$$

$$
= 273.15 \times 0.000810 = 0.221
$$

**System 2: Electric Resistance Heater**

$$
\frac{\dot X_{dest,elec}}{\dot Q_{load}} = \frac{T_0}{T_{in}}
$$

$$
= \frac{273.15}{298.15} = 0.916
$$

### Comparison

$$
\frac{\Delta\dot X_{dest}}{\dot Q_{load}} = 0.916 - 0.221 = 0.695
$$

$$
\frac{\dot X_{dest,elec}}{\dot X_{dest,steam}} = \frac{0.916}{0.221} \approx 4.1
$$

**Conclusion:** The electric resistance heater destroys **69.5%** of $\dot Q_{load}$ as exergy versus **22.1%** for steam, roughly **4.1 times more**, independent of system scale. This is because electricity is pure work (exergy = energy), so converting it to low-temperature heat is inherently wasteful, while steam at 120°C supplies heat much closer to the delivery temperature.

**Result: Steam condensing heat exchanger heating results in the least exergy destruction.**