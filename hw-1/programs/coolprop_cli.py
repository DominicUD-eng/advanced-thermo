import sys
from CoolProp.CoolProp import PropsSI, get_global_param_string

# Usage: python coolprop_cli.py <property> <input1_type> <input1_value> <input2_type> <input2_value> [fluid]
# Example: python coolprop_cli.py H P 101325 T 373.15 Water
# Example: python coolprop_cli.py H P 101325 T 300 Air
# Example: python coolprop_cli.py H P 500000 T 273.15 R134a

def list_common_fluids():
    """List some commonly used fluids in CoolProp"""
    common_fluids = [
        "Water", "Air", "R134a", "R410A", "R22", "R32", "CO2", "Ammonia",
        "Propane", "Butane", "Methane", "Ethane", "Nitrogen", "Oxygen", 
        "Helium", "Hydrogen", "Argon", "R404A", "R407C", "R507A"
    ]
    return common_fluids

def main():
    if len(sys.argv) < 6:
        print("Usage: python coolprop_cli.py <property> <input1_type> <input1_value> <input2_type> <input2_value> [fluid]")
        print("Example: python coolprop_cli.py H P 101325 T 373.15 Water")
        print("Example: python coolprop_cli.py H P 101325 T 300 Air")
        print("Example: python coolprop_cli.py S P 500000 T 273.15 R134a")
        print("\nCommon fluids:", ", ".join(list_common_fluids()))
        print("\nSupported properties: H (Enthalpy), S (Entropy), Q (Quality), T (Temperature), P (Pressure), D (Density), U (Internal Energy), etc.")
        print("Supported input types: T (Temperature, K), P (Pressure, Pa), Q (Quality), D (Density, kg/m^3), H (Enthalpy, J/kg), S (Entropy, J/kg/K)")
        sys.exit(1)

    prop = sys.argv[1]
    in1_type = sys.argv[2]
    in1_val = float(sys.argv[3])
    in2_type = sys.argv[4]
    in2_val = float(sys.argv[5])
    
    # Default to Water if no fluid specified (backwards compatibility)
    fluid = sys.argv[6] if len(sys.argv) > 6 else 'Water'

    # Supported properties: H (Enthalpy), S (Entropy), Q (Quality), T (Temperature), P (Pressure), D (Density), U (Internal Energy), etc.
    # Supported input types: T (Temperature, K), P (Pressure, Pa), Q (Quality), D (Density, kg/m^3), H (Enthalpy, J/kg), S (Entropy, J/kg/K)
    try:
        result = PropsSI(prop, in1_type, in1_val, in2_type, in2_val, fluid)
        print(f"{prop} at {in1_type}={in1_val}, {in2_type}={in2_val} for {fluid}: {result}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Make sure '{fluid}' is a valid CoolProp fluid name.")
        print("Common fluids:", ", ".join(list_common_fluids()))
        print("\nFor a complete list of fluids, visit: http://www.coolprop.org/fluid_properties/PurePseudoPure.html")

if __name__ == "__main__":
    main()