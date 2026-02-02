#!/usr/bin/env python3
"""
Problem 14: Carnot Cycle Heat Engines - Pure Python Analysis

Calculates the total efficiency of concentrated solar power plants
using only built-in Python functions (no external dependencies).
"""

import math

# Physical constants and parameters
SIGMA = 5.67e-8  # Stefan-Boltzmann constant [W/(m²·K⁴)]
I = 1000  # Solar irradiance [W/m²]
T_L = 300  # Cold reservoir temperature [K]

# Concentration ratios [suns]
concentration_ratios = [100, 500, 1000, 2000, 3000]

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

def find_optimal_temperature(C, T_L, tolerance=1e-3):
    """Find optimal temperature by scanning the valid range"""
    
    # Temperature range to search
    T_range = range(int(T_L + 50), 2601, 10)  # 350K to 2600K in 10K steps
    
    max_efficiency = -1
    optimal_T_H = T_L + 50
    
    for T_H in T_range:
        eta = total_efficiency(T_H, C, T_L)
        if eta > max_efficiency:
            max_efficiency = eta
            optimal_T_H = T_H
    
    # Refine the search around the best point
    if optimal_T_H > T_L + 50:
        T_fine = [optimal_T_H + i for i in range(-20, 21, 1)]
        for T_H in T_fine:
            if T_H > T_L and T_H < 2601:
                eta = total_efficiency(T_H, C, T_L)
                if eta > max_efficiency:
                    max_efficiency = eta
                    optimal_T_H = T_H
    
    return float(optimal_T_H), max_efficiency

def main():
    print("PROBLEM 14: CARNOT CYCLE HEAT ENGINES")
    print("=" * 80)
    print("Concentrated Solar Power Plant Efficiency Analysis")
    print()
    print("Parameters:")
    print(f"  Solar irradiance (I): {I} W/m²")
    print(f"  Cold reservoir (T_L): {T_L} K ({T_L-273.15:.1f}°C)")
    print(f"  Stefan-Boltzmann constant (σ): {SIGMA:.2e} W/(m²·K⁴)")
    print(f"  Concentration ratios: {concentration_ratios} suns")
    print()
    
    print("PART A: OPTIMAL OPERATING CONDITIONS")
    print("-" * 70)
    print(f"{'C [suns]':>8} {'T_opt [K]':>10} {'T_opt [°C]':>11} {'η_max':>8} {'η_recv':>8} {'η_Carnot':>10}")
    print("-" * 70)
    
    optimal_results = []
    
    for C in concentration_ratios:
        T_H_opt, eta_max = find_optimal_temperature(C, T_L)
        eta_recv_opt = receiver_efficiency(T_H_opt, C)
        eta_carnot_opt = carnot_efficiency(T_H_opt, T_L)
        
        optimal_results.append({
            'C': C,
            'T_H_opt': T_H_opt,
            'eta_max': eta_max
        })
        
        print(f"{C:8.0f} {T_H_opt:10.1f} {T_H_opt-273.15:11.1f} {eta_max:8.1%} {eta_recv_opt:8.1%} {eta_carnot_opt:10.1%}")
    
    print()
    print("PART B: PHYSICAL ANALYSIS")
    print("-" * 70)
    
    T_opt_min = min(r['T_H_opt'] for r in optimal_results)
    T_opt_max = max(r['T_H_opt'] for r in optimal_results)
    eta_min = min(r['eta_max'] for r in optimal_results)
    eta_max = max(r['eta_max'] for r in optimal_results)
    
    print(f"1. OPTIMAL TEMPERATURE TRENDS:")
    print(f"   • As C increases: {T_opt_min:.0f}K → {T_opt_max:.0f}K")
    print(f"   • Maximum efficiency: {eta_min:.1%} → {eta_max:.1%}")
    print()
    
    print(f"2. PHYSICAL TRADE-OFFS:")
    print(f"   • Carnot efficiency ↑ with T_H (thermodynamic limit)")
    print(f"   • Receiver efficiency ↓ with T_H (radiation losses ∝ T⁴)")
    print(f"   • Optimal = balance point of competing effects")
    print()
    
    print(f"3. CONCENTRATION EFFECTS:")
    print(f"   • Higher C → can operate at higher T_H")
    print(f"   • Concentrated energy (C·I) vs radiation losses (σT⁴)")
    print()
    
    print("SAMPLE DATA FOR PLOTTING:")
    print("-" * 70)
    print(f"{'T_H [K]':>8}", end="")
    for C in concentration_ratios:
        print(f"{'C='+str(C):>10}", end="")
    print()
    print("-" * (8 + 10 * len(concentration_ratios)))
    
    T_sample = [500, 750, 1000, 1250, 1500, 1750, 2000, 2250]
    
    for T_H in T_sample:
        print(f"{T_H:8.0f}", end="")
        for C in concentration_ratios:
            eta = total_efficiency(T_H, C, T_L)
            if eta > 0:
                print(f"{eta:10.3f}", end="")
            else:
                print(f"{'--':>10}", end="")
        print()
    
    print()
    print("=" * 80)
    print("✅ Analysis complete!")
    print("📊 Use the sample data above to create plots")
    print("📝 Plot η_total vs T_H with curves for each concentration ratio")

if __name__ == "__main__":
    main()