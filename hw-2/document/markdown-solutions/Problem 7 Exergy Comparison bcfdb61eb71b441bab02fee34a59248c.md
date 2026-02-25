# Problem 7: Exergy Comparison

**Exergy**

Which of the two materials below have the capability to produce the most work in a closed system if taken to an environmental dead state of 25 °C and 100 kPa?

### Initial States

**Steam:**

- Mass: 1 kg
- P = 800 kPa
- T = 180 °C

**R-134a:**

- Mass: 1 kg
- P = 800 kPa
- T = 180 °C

### Environmental Dead State

- T₀ = 25 °C
- P₀ = 100 kPa

### Solution

**For Steam (Water):**

Initial state (P = 800 kPa, T = 180 °C = 453.15 K):

$$
h_1 = 2792.44 \text{ kJ/kg}
$$

$$
s_1 = 6.7154 \text{ kJ/kg K}
$$

Dead state (P₀ = 100 kPa, T₀ = 25 °C = 298.15 K):

$$
h_0 = 104.92 \text{ kJ/kg}
$$

$$
s_0 = 0.3672 \text{ kJ/kg K}
$$

Specific exergy calculation:

$$
\psi_{steam} = (h_1 - h_0) - T_0(s_1 - s_0)
$$

$$
\psi_{steam} = (2792.44 - 104.92) - 298.15(6.7154 - 0.3672)
$$

$$
\psi_{steam} = 2687.52 - 298.15(6.3482)
$$

$$
\psi_{steam} = 2687.52 - 1892.97
$$

$$
\psi_{steam} = 794.55 \text{ kJ/kg}
$$

**For R-134a:**

Initial state (P = 800 kPa, T = 180 °C = 453.15 K):

$$
h_1 = 570.78 \text{ kJ/kg}
$$

$$
s_1 = 2.1283 \text{ kJ/kg K}
$$

Dead state (P₀ = 100 kPa, T₀ = 25 °C = 298.15 K):

$$
h_0 = 424.55 \text{ kJ/kg}
$$

$$
s_0 = 1.9017 \text{ kJ/kg K}
$$

Specific exergy calculation:

$$
\psi_{R134a} = (h_1 - h_0) - T_0(s_1 - s_0)
$$

$$
\psi_{R134a} = (570.78 - 424.55) - 298.15(2.1283 - 1.9017)
$$

$$
\psi_{R134a} = 146.23 - 298.15(0.2266)
$$

$$
\psi_{R134a} = 146.23 - 67.57
$$

$$
\psi_{R134a} = 78.66 \text{ kJ/kg}
$$

### Conclusion

**Steam has significantly higher exergy:**

- Steam:
    
    $$
    \psi = 794.55 \text{ kJ/kg}
    $$
    
- R-134a:
    
    $$
    \psi = 78.66 \text{ kJ/kg}
    $$
    

**Answer: Steam (water) has the capability to produce approximately 10 times more work than R-134a when brought to the environmental dead state.**

This is because steam at these conditions has a much larger enthalpy difference from the dead state, despite both substances starting at the same pressure and temperature. This is largely due to water’s specific heat capacity being so large.