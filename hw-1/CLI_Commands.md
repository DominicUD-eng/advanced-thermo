# CLI Commands Reference - Advanced Thermodynamics Homework 1

This document contains all Command Line Interface (CLI) commands used for thermodynamic property calculations and verification throughout the homework problems.

## Problem 9: Isentropic Steam Turbine with Extraction

### Steam Properties Lookup
```bash
# State 1 (Inlet): 3 MPa, saturated vapor
python steam_cli.py T P 3000000 Q 1           # → T₁ = 507.0 K
python steam_cli.py H P 3000000 Q 1           # → h₁ = 2803.2 kJ/kg  
python steam_cli.py S P 3000000 Q 1           # → s₁ = 6185.6 J/kg·K

# State 2 (Extraction): 500 kPa, s₂ = s₁ (isentropic)
python steam_cli.py H P 500000 S 6185.583126654898    # → h₂ = 2478.2 kJ/kg

# State 3 (Exhaust): 50 kPa, T₃ = 100°C
python steam_cli.py H P 50000 T 373.15        # → h₃ = 2682.4 kJ/kg
```

## Problem 10: Real Steam Turbine Entropy Analysis

### Part A: Isentropic Operation Properties
```bash
# Inlet properties: 3 MPa, 400°C
python steam_cli.py H P 3000000 T 673.15      # → h₁ = 3231.7 kJ/kg
python steam_cli.py S P 3000000 T 673.15      # → s₁ = 6923.4 J/kg·K

# Isentropic exhaust: 100 kPa, s₂ₛ = s₁
python steam_cli.py H P 100000 S 6923.448666758736     # → h₂ₛ = 2512.6 kJ/kg
python steam_cli.py T P 100000 S 6923.448666758736     # → T₂ₛ = 372.8 K  
python steam_cli.py Q P 100000 S 6923.448666758736     # → x₂ₛ = 0.928
```

### Part B: Real Turbine Operation
```bash
# Real exhaust state: 100 kPa, h₂ = 2620.5 kJ/kg (from efficiency calculation)
python steam_cli.py T P 100000 H 2620500      # → T₂ = 372.8 K
python steam_cli.py Q P 100000 H 2620500      # → x₂ = 0.976
python steam_cli.py S P 100000 H 2620500      # → s₂ = 7212.8 J/kg·K
```

## Problem 11: Steam Quality Change in Piston-Cylinder

### Water/Steam Properties at 200 kPa
```bash
# Saturated liquid properties (x = 0)
python steam_cli.py S P 200000 Q 0            # → sₓ = 1530.2 J/kg·K = 1.530 kJ/kg·K

# Saturated vapor properties (x = 1)  
python steam_cli.py S P 200000 Q 1            # → sₘ = 7126.9 J/kg·K = 7.127 kJ/kg·K

# Verification: Initial state with x₁ = 0.6
python steam_cli.py S P 200000 Q 0.6          # → s₁ = 4888.2 J/kg·K ✓
```

## Problem 12: Piston-Cylinder Total Entropy Change  

### Initial State Properties
```bash
# Saturated liquid at 150 kPa
python steam_cli.py H P 150000 Q 0            # → h₁ = hₓ = 467.1 kJ/kg
python steam_cli.py S P 150000 Q 0            # → s₁ = sₓ = 1433.7 J/kg·K = 1.434 kJ/kg·K
python steam_cli.py D P 150000 Q 0            # → ρ₁ = 949.9 kg/m³
```

### Final State Properties
```bash
# Saturated vapor properties for reference
python steam_cli.py H P 150000 Q 1            # → hₘ = 2693.1 kJ/kg

# Final state after heating: 150 kPa, h₂ = 840.1 kJ/kg
python steam_cli.py Q P 150000 H 840100       # → x₂ = 0.168 (16.8% vapor)
```

## Problem 13: Solar Energy Storage Entropy Analysis

### Air Property Calculations using CoolProp
```bash
# State 3: 250°C, 4000 kPa 
python coolprop_cli.py S P 4000000 T 523.15 Air       # → s₃ = 3389.9 J/kg·K

# State 4: 1100°C, 4000 kPa (constant pressure heating)
python coolprop_cli.py S P 4000000 T 1373.15 Air      # → s₄ = 4468.7 J/kg·K
```

### Isentropic Expansion Analysis
```bash
# Find T₅ where s₅ = s₄ at P₅ = 100 kPa using iterative solver
python property_solver.py S 4468.7 P 100000 T 300 1500 Air    # → T₅ = 529.7 K

# Enthalpy calculations for turbine work
python coolprop_cli.py H P 4000000 T 1373.15 Air      # → h₄ = 1612783 J/kg  
python coolprop_cli.py H P 100000 T 529.688 Air       # → h₅ = 660057 J/kg
```

## Problem 14: Concentrated Solar Power Carnot Analysis

### Optimization Analysis
```bash
# Complete Carnot cycle analysis with optimization
python carnot_simple.py                       # → Complete analysis with optimization

# Generate efficiency plots  
python carnot_plotter.py                     # → Creates efficiency vs temperature plots
```

## Tool Summary

### Available CLI Tools:
- **steam_cli.py**: Water/steam property lookup using CoolProp
- **coolprop_cli.py**: Multi-fluid property calculations (Air, refrigerants, etc.)  
- **property_solver.py**: Iterative solver for complex thermodynamic state calculations
- **carnot_simple.py**: Concentrated solar power efficiency optimization analysis
- **carnot_plotter.py**: Matplotlib-based plotting for Carnot cycle analysis

### Command Format:
```bash
python <tool_name> <property> <input1> <value1> [input2] [value2] [fluid]
```

**Common Properties:**
- T: Temperature (K)
- P: Pressure (Pa) 
- H: Enthalpy (J/kg)
- S: Entropy (J/kg·K)
- Q: Quality (0-1 for two-phase)
- D: Density (kg/m³)

**Example Usage:**
```bash
python steam_cli.py H P 101325 T 373.15      # Steam enthalpy at 1 atm, 100°C
python coolprop_cli.py T P 101325 H 2676000 Water  # Temperature from P,H
```