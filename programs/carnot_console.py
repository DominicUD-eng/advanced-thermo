#!/usr/bin/env python3
"""
Problem 14: Carnot Cycle Heat Engines - Concentrated Solar Power Analysis (Console Version)

Calculates the total efficiency of an ideal concentrated solar power plant
as the product of receiver efficiency and Carnot heat engine efficiency.

Console output version without GUI plots.
"""

import numpy as np

# Physical constants and parameters
SIGMA = 5.67e-8  # Stefan-Boltzmann constant [W/(m²·K⁴)]
I = 1000  # Solar irradiance [W/m²]
T_L = 300  # Cold reservoir temperature [K]

# Concentration ratios [suns]
concentration_ratios = [100, 500, 1000, 2000, 3000]

# Temperature range for analysis
T_H_min = 300  # K
T_H_max = 2600  # K

def receiver_efficiency(T_H, C):
    """Calculate receiver efficiency: η_receiver = 1 - σT_H⁴/(C·I)"""
    return 1 - (SIGMA * T_H**4) / (C * I)

def carnot_efficiency(T_H, T_L):
    """Calculate Carnot heat engine efficiency: η_Carnot = 1 - T_L/T_H"""
    return 1 - T_L / T_H

def total_efficiency(T_H, C, T_L):
    """Calculate total system efficiency: η_total = η_receiver × η_Carnot"""
    eta_recv = receiver_efficiency(T_H, C)
    eta_carnot = carnot_efficiency(T_H, T_L)
    return eta_recv * eta_carnot

def find_optimal_temperature(C, T_L, tolerance=1e-6):
    """Find the temperature that maximizes total efficiency using golden section search"""
    
    # Golden section search parameters
    phi = (1 + 5**0.5) / 2  # Golden ratio
    resphi = 2 - phi
    
    # Search bounds
    a = T_L + 50  # Minimum reasonable temperature
    b = T_H_max   # Maximum temperature
    
    # Initial points
    tol = tolerance * (b - a)
    x1 = a + resphi * (b - a)
    x2 = a + (1 - resphi) * (b - a)
    
    # Evaluate function at initial points (negative for maximization)
    f1 = -total_efficiency(x1, C, T_L)
    f2 = -total_efficiency(x2, C, T_L)
    
    # Golden section search
    for _ in range(100):  # Maximum iterations
        if abs(b - a) < tol:
            break
            
        if f1 > f2:
            b = x2
            x2 = x1
            f2 = f1
            x1 = a + resphi * (b - a)
            f1 = -total_efficiency(x1, C, T_L)
        else:
            a = x1
            x1 = x2
            f1 = f2
            x2 = a + (1 - resphi) * (b - a)
            f2 = -total_efficiency(x2, C, T_L)
    
    # Return optimal point
    optimal_T_H = (a + b) / 2
    max_efficiency = total_efficiency(optimal_T_H, C, T_L)
    
    return optimal_T_H, max_efficiency

def create_data_table():
    """Generate data table for plotting and analysis"""
    
    print("Generating efficiency data...")
    
    # Temperature array for calculations
    T_H_range = np.linspace(T_H_min, T_H_max, 50)
    
    # Store results
    results = {}
    optimal_results = []
    
    print("\nCalculating optimal operating points...")
    
    for C in concentration_ratios:
        print(f"  Processing C = {C} suns...")
        
        # Calculate efficiencies across temperature range
        eta_receiver = [receiver_efficiency(T_H, C) for T_H in T_H_range]
        eta_carnot = [carnot_efficiency(T_H, T_L) for T_H in T_H_range]
        eta_total = [total_efficiency(T_H, C, T_L) for T_H in T_H_range]
        
        # Store data
        results[C] = {
            'T_H': T_H_range,
            'eta_receiver': eta_receiver,
            'eta_carnot': eta_carnot,
            'eta_total': eta_total
        }
        
        # Find optimal temperature
        T_H_opt, eta_max = find_optimal_temperature(C, T_L)
        
        optimal_results.append({
            'C': C,
            'T_H_optimal_K': T_H_opt,
            'T_H_optimal_C': T_H_opt - 273.15,
            'eta_max': eta_max,
            'eta_receiver_opt': receiver_efficiency(T_H_opt, C),
            'eta_carnot_opt': carnot_efficiency(T_H_opt, T_L)
        })
    
    return results, optimal_results

def print_analysis(optimal_results):
    """Print comprehensive analysis results"""
    
    print("="*80)
    print("PROBLEM 14: CARNOT CYCLE HEAT ENGINES - ANALYSIS RESULTS")
    print("="*80)
    
    print("\nPART A: OPTIMAL OPERATING CONDITIONS")
    print("-" * 60)
    print(f"{'C [suns]':>8} {'T_H,opt [K]':>12} {'T_H,opt [°C]':>13} {'η_total,max':>12} {'η_receiver':>11} {'η_Carnot':>10}")
    print("-" * 60)
    
    for result in optimal_results:
        print(f"{result['C']:8.0f} {result['T_H_optimal_K']:12.1f} {result['T_H_optimal_C']:13.1f} "
              f"{result['eta_max']:12.1%} {result['eta_receiver_opt']:11.1%} {result['eta_carnot_opt']:10.1%}")
    
    print("\n" + "="*80)
    print("PART B: PHYSICAL ANALYSIS AND TRENDS")
    print("="*80)
    
    # Calculate trends
    T_opt_min = min(r['T_H_optimal_K'] for r in optimal_results)
    T_opt_max = max(r['T_H_optimal_K'] for r in optimal_results)
    eta_min = min(r['eta_max'] for r in optimal_results)
    eta_max = max(r['eta_max'] for r in optimal_results)
    
    print(f"\n1. OPTIMAL TEMPERATURE TRENDS:")
    print(f"   • As concentration ratio increases from {min(concentration_ratios)} to {max(concentration_ratios)} suns:")
    print(f"   • Optimal T_H increases from {T_opt_min:.1f}K to {T_opt_max:.1f}K")
    print(f"   • Maximum efficiency increases from {eta_min:.1%} to {eta_max:.1%}")
    
    print(f"\n2. PHYSICAL TRADE-OFFS:")
    print(f"   • CARNOT EFFICIENCY: η_Carnot = 1 - T_L/T_H")
    print(f"     → Increases with T_H (better thermodynamic limit)")
    print(f"     → At T_H = 1000K: η_Carnot = {carnot_efficiency(1000, T_L):.1%}")
    print(f"     → At T_H = 2000K: η_Carnot = {carnot_efficiency(2000, T_L):.1%}")
    
    print(f"\n   • RECEIVER EFFICIENCY: η_receiver = 1 - σT_H⁴/(C·I)")
    print(f"     → Decreases with T_H (radiation losses scale as T⁴)")
    print(f"     → At T_H = 1000K, C = 1000: η_receiver = {receiver_efficiency(1000, 1000):.1%}")
    print(f"     → At T_H = 2000K, C = 1000: η_receiver = {receiver_efficiency(2000, 1000):.1%}")
    
    print(f"\n3. CONCENTRATION RATIO EFFECTS:")
    print(f"   • Higher C allows operation at higher T_H before radiation losses dominate")
    print(f"   • Critical balance: Concentrated sunlight (C·I) vs. radiation losses (σT_H⁴)")
    
    # Calculate breakeven temperatures
    print(f"\n4. BREAKEVEN ANALYSIS:")
    print(f"   • Temperature where receiver efficiency = 50%:")
    for C in [100, 1000, 3000]:
        T_breakeven = ((0.5 * C * I) / SIGMA) ** 0.25
        print(f"     → C = {C:4.0f} suns: T_H = {T_breakeven:.0f}K ({T_breakeven-273.15:.0f}°C)")
    
    print(f"\n5. ENGINEERING IMPLICATIONS:")
    print(f"   • Low concentration (C = {min(concentration_ratios)}): Optimal at moderate T_H ≈ {optimal_results[0]['T_H_optimal_C']:.0f}°C")
    print(f"   • High concentration (C = {max(concentration_ratios)}): Can achieve {optimal_results[-1]['eta_max']:.1%} efficiency at {optimal_results[-1]['T_H_optimal_C']:.0f}°C")
    print(f"   • Trade-off between system complexity (high C) and performance")

def generate_sample_data():
    """Generate sample data points for plotting"""
    
    print("\n" + "="*80)
    print("SAMPLE DATA FOR PLOTTING")
    print("="*80)
    
    # Selected temperatures for data table
    T_sample = [500, 750, 1000, 1250, 1500, 1750, 2000]
    
    print(f"\nTotal Efficiency Data (η_total = η_receiver × η_Carnot):")
    print(f"{'T_H [K]':>8}", end="")
    for C in concentration_ratios:
        print(f"{f'C={C}':>10}", end="")
    print()
    print("-" * (8 + 10 * len(concentration_ratios)))
    
    for T_H in T_sample:
        print(f"{T_H:8.0f}", end="")
        for C in concentration_ratios:
            eta = total_efficiency(T_H, C, T_L)
            print(f"{eta:10.3f}", end="")
        print()

def main():
    """Main analysis function"""
    
    print("CARNOT CYCLE HEAT ENGINES - CONCENTRATED SOLAR POWER ANALYSIS")
    print("="*80)
    print("Parameters:")
    print(f"  Solar irradiance (I): {I} W/m²")
    print(f"  Cold reservoir (T_L): {T_L} K ({T_L-273.15:.1f}°C)")
    print(f"  Stefan-Boltzmann constant (σ): {SIGMA:.2e} W/(m²·K⁴)")
    print(f"  Temperature range: {T_H_min}-{T_H_max} K")
    print(f"  Concentration ratios: {concentration_ratios} suns")
    
    # Generate efficiency data
    results, optimal_results = create_data_table()
    
    # Print analysis
    print_analysis(optimal_results)
    
    # Generate sample data for plotting
    generate_sample_data()
    
    print(f"\n✅ Problem 14 analysis complete!")
    print(f"📝 Use the data above to create plots in Excel/Python/MATLAB")
    print(f"📊 Plot η_total vs T_H with separate curves for each concentration ratio")

if __name__ == "__main__":
    main()