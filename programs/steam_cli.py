import sys
from CoolProp.CoolProp import PropsSI

# Usage: python steam_cli.py <property> <input1_type> <input1_value> <input2_type> <input2_value>
# Example: python steam_cli.py H P 101325 T 373.15
# Returns enthalpy (H) of steam at 101325 Pa and 373.15 K

def main():
    if len(sys.argv) != 6:
        print("Usage: python steam_cli.py <property> <input1_type> <input1_value> <input2_type> <input2_value>")
        print("Example: python steam_cli.py H P 101325 T 373.15")
        sys.exit(1)

    prop = sys.argv[1]
    in1_type = sys.argv[2]
    in1_val = float(sys.argv[3])
    in2_type = sys.argv[4]
    in2_val = float(sys.argv[5])

    # Supported properties: H (Enthalpy), S (Entropy), Q (Quality), T (Temperature), P (Pressure), D (Density), U (Internal Energy), etc.
    # Supported input types: T (Temperature, K), P (Pressure, Pa), Q (Quality), D (Density, kg/m^3), H (Enthalpy, J/kg), S (Entropy, J/kg/K)
    try:
        result = PropsSI(prop, in1_type, in1_val, in2_type, in2_val, 'Water')
        print(f"{prop} at {in1_type}={in1_val}, {in2_type}={in2_val} for Water: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
