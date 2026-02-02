#!/usr/bin/env python3
"""
Property Solver for CoolProp
Iteratively solves for an unknown property when two other properties are specified.

Usage:
python property_solver.py <target_prop> <target_value> <known_prop1> <known_value1> <unknown_prop> <min_guess> <max_guess> [fluid] [tolerance]

Example: Find temperature where entropy = 4468.7 J/kg/K at P = 100000 Pa for Air
python property_solver.py S 4468.7 P 100000 T 300 1500 Air

Example: Find pressure where enthalpy = 2500000 J/kg at T = 400 K for Water  
python property_solver.py H 2500000 T 400 P 100000 10000000 Water
"""

import subprocess
import sys

def call_coolprop_cli(prop, input1_type, input1_value, input2_type, input2_value, fluid="Water"):
    """Call the coolprop_cli.py script and return the result"""
    try:
        cmd = [
            "python", "coolprop_cli.py", 
            prop, 
            input1_type, str(input1_value), 
            input2_type, str(input2_value), 
            fluid
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output_lines = result.stdout.strip().split('\n')
        
        # Parse the last line which contains the result
        last_line = output_lines[-1]
        if ":" in last_line:
            value_str = last_line.split(":")[-1].strip()
            return float(value_str)
        else:
            raise ValueError(f"Unexpected output format: {last_line}")
            
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"CoolProp CLI failed: {e.stderr}")
    except (ValueError, IndexError) as e:
        raise RuntimeError(f"Failed to parse CoolProp output: {e}")

def solve_property(target_prop, target_value, known_prop, known_value, unknown_prop, 
                  min_guess, max_guess, fluid="Water", tolerance=1e-3, max_iterations=50):
    """
    Solve for unknown_prop such that target_prop equals target_value
    
    Args:
        target_prop: Property we want to match (e.g., "S" for entropy)
        target_value: Target value for that property
        known_prop: Known property type (e.g., "P" for pressure) 
        known_value: Known property value
        unknown_prop: Property to solve for (e.g., "T" for temperature)
        min_guess: Minimum bound for unknown property
        max_guess: Maximum bound for unknown property
        fluid: Fluid name (default "Water")
        tolerance: Relative tolerance for convergence (default 1e-3)
        max_iterations: Maximum number of iterations (default 50)
    
    Returns:
        tuple: (solved_value, actual_target_value, iterations_used)
    """
    
    print(f"Solving for {unknown_prop} where {target_prop} = {target_value} at {known_prop} = {known_value} for {fluid}")
    print(f"Search range: {min_guess} to {max_guess}")
    print(f"Tolerance: {tolerance}, Max iterations: {max_iterations}")
    print("-" * 60)
    
    # Binary search algorithm
    low = min_guess
    high = max_guess
    
    for iteration in range(max_iterations):
        # Try the midpoint
        guess = (low + high) / 2.0
        
        try:
            # Get the target property value at this guess
            actual_value = call_coolprop_cli(target_prop, known_prop, known_value, 
                                           unknown_prop, guess, fluid)
            
            # Calculate relative error
            error = abs(actual_value - target_value) / abs(target_value)
            
            print(f"Iter {iteration+1:2d}: {unknown_prop} = {guess:10.3f} → "
                  f"{target_prop} = {actual_value:10.3f} (target: {target_value:10.3f}, "
                  f"error: {error:.6f})")
            
            # Check convergence
            if error < tolerance:
                print("-" * 60)
                print(f"✓ Converged! {unknown_prop} = {guess:.6f}")
                print(f"  Final {target_prop} = {actual_value:.6f} (target: {target_value:.6f})")
                print(f"  Final error: {error:.8f}")
                print(f"  Iterations: {iteration + 1}")
                return guess, actual_value, iteration + 1
            
            # Update search bounds based on result
            if actual_value < target_value:
                low = guess  # Need higher value
            else:
                high = guess  # Need lower value
                
        except Exception as e:
            print(f"Iter {iteration+1:2d}: {unknown_prop} = {guess:10.3f} → ERROR: {e}")
            # If we get an error, try to continue by adjusting bounds
            if iteration == 0:
                raise  # Fail early if first guess doesn't work
            # Narrow the search space
            if actual_value < target_value:
                low = guess
            else:
                high = guess
    
    # Didn't converge
    final_guess = (low + high) / 2.0
    final_value = call_coolprop_cli(target_prop, known_prop, known_value, 
                                   unknown_prop, final_guess, fluid)
    final_error = abs(final_value - target_value) / abs(target_value)
    
    print("-" * 60)
    print(f"⚠ Maximum iterations reached without convergence!")
    print(f"  Final {unknown_prop} = {final_guess:.6f}")
    print(f"  Final {target_prop} = {final_value:.6f} (target: {target_value:.6f})")
    print(f"  Final error: {final_error:.8f}")
    print(f"  Iterations: {max_iterations}")
    
    return final_guess, final_value, max_iterations

def main():
    if len(sys.argv) < 8:
        print(__doc__)
        sys.exit(1)
    
    target_prop = sys.argv[1]
    target_value = float(sys.argv[2])
    known_prop = sys.argv[3] 
    known_value = float(sys.argv[4])
    unknown_prop = sys.argv[5]
    min_guess = float(sys.argv[6])
    max_guess = float(sys.argv[7])
    
    fluid = sys.argv[8] if len(sys.argv) > 8 else "Water"
    tolerance = float(sys.argv[9]) if len(sys.argv) > 9 else 1e-3
    
    try:
        solved_value, actual_value, iterations = solve_property(
            target_prop, target_value, known_prop, known_value, unknown_prop,
            min_guess, max_guess, fluid, tolerance
        )
        
        print(f"\n🎯 Solution: {unknown_prop} = {solved_value:.6f}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()