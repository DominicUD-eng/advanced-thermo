#!/usr/bin/env python3
"""
Problem 14: Carnot Cycle Heat Engines - Concentrated Solar Power Analysis

Calculates and plots the total efficiency of an ideal concentrated solar power plant
as the product of receiver efficiency and Carnot heat engine efficiency.

Analysis includes finding optimal receiver temperatures for different concentration ratios.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar
import pandas as pd

# Physical constants and parameters
SIGMA = 5.67e-8  # Stefan-Boltzmann constant [W/(m²·K⁴)]
I = 1000  # Solar irradiance [W/m²]
T_L = 300  # Cold reservoir temperature [K]

# Concentration ratios [suns]
concentration_ratios = [100, 500, 1000, 2000, 3000]

# Temperature range for analysis
T_H_min = 300  # K
T_H_max = 2600  # K
T_H_range = np.linspace(T_H_min, T_H_max, 100)

def receiver_efficiency(T_H, C):
    """
    Calculate receiver efficiency
    η_receiver = 1 - σT_H⁴/(C·I)
    """
    return 1 - (SIGMA * T_H**4) / (C * I)

def carnot_efficiency(T_H, T_L):
    """
    Calculate Carnot heat engine efficiency
    η_Carnot = 1 - T_L/T_H
    """
    return 1 - T_L / T_H

def total_efficiency(T_H, C, T_L):
    """
    Calculate total system efficiency
    η_total = η_receiver × η_Carnot
    """
    eta_recv = receiver_efficiency(T_H, C)
    eta_carnot = carnot_efficiency(T_H, T_L)
    return eta_recv * eta_carnot

def find_optimal_temperature(C, T_L):
    """
    Find the temperature that maximizes total efficiency for a given concentration ratio
    """
    # Objective function to minimize (negative total efficiency)
    def objective(T_H):
        return -total_efficiency(T_H, C, T_L)
    
    # Find minimum (maximum efficiency) in the valid range
    result = minimize_scalar(objective, bounds=(T_L + 50, T_H_max), method='bounded')
    
    if result.success:
        optimal_T_H = result.x
        max_efficiency = -result.fun
        return optimal_T_H, max_efficiency
    else:
        return None, None

def create_efficiency_plots():
    """Create plots for Part A"""
    
    plt.figure(figsize=(12, 8))
    
    # Colors for different concentration ratios
    colors = ['blue', 'green', 'red', 'purple', 'orange']
    
    # Store optimal points for Part B analysis
    optimal_results = []
    
    for i, C in enumerate(concentration_ratios):
        # Calculate efficiencies for this concentration ratio
        eta_total = [total_efficiency(T_H, C, T_L) for T_H in T_H_range]
        
        # Find optimal temperature and efficiency
        T_H_opt, eta_max = find_optimal_temperature(C, T_L)
        
        if T_H_opt is not None:
            optimal_results.append({
                'C': C,
                'T_H_optimal': T_H_opt,
                'eta_max': eta_max,
                'T_H_optimal_C': T_H_opt - 273.15  # Convert to Celsius
            })
            
            # Plot the efficiency curve
            plt.plot(T_H_range, eta_total, color=colors[i], linewidth=2, 
                    label=f'C = {C} suns')
            
            # Mark the optimal point
            plt.plot(T_H_opt, eta_max, 'o', color=colors[i], markersize=8,
                    markerfacecolor='white', markeredgewidth=2)
            plt.annotate(f'({T_H_opt:.0f}K, {eta_max:.3f})', 
                        xy=(T_H_opt, eta_max), xytext=(10, 10),
                        textcoords='offset points', fontsize=9,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor=colors[i], alpha=0.3))
    
    # Formatting
    plt.xlabel('Hot Reservoir Temperature, $T_H$ [K]', fontsize=14)
    plt.ylabel('Total System Efficiency, $\\eta_{total}$', fontsize=14)
    plt.title('Concentrated Solar Power Plant Efficiency\n'
             '$\\eta_{total} = \\eta_{receiver} \\times \\eta_{Carnot}$', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12, loc='upper right')
    plt.xlim(T_H_min, T_H_max)
    plt.ylim(0, max([max(total_efficiency(T_H, C, T_L) for T_H in T_H_range) 
                    for C in concentration_ratios]) * 1.1)
    
    plt.tight_layout()
    plt.savefig('carnot_cycle_efficiency.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return optimal_results

def analyze_component_efficiencies():
    """Create additional plots showing receiver vs Carnot efficiency trade-offs"""
    
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
    
    # Plot receiver efficiency vs temperature
    for i, C in enumerate(concentration_ratios):
        eta_recv = [receiver_efficiency(T_H, C) for T_H in T_H_range]
        ax1.plot(T_H_range, eta_recv, label=f'C = {C} suns', linewidth=2)
    
    ax1.set_xlabel('Temperature, $T_H$ [K]')
    ax1.set_ylabel('Receiver Efficiency, $\\eta_{receiver}$')
    ax1.set_title('Receiver Efficiency\n$\\eta_{recv} = 1 - \\frac{\\sigma T_H^4}{C \\cdot I}$')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot Carnot efficiency vs temperature
    eta_carnot = [carnot_efficiency(T_H, T_L) for T_H in T_H_range]
    ax2.plot(T_H_range, eta_carnot, 'black', linewidth=2, label='Carnot Efficiency')
    ax2.set_xlabel('Temperature, $T_H$ [K]')
    ax2.set_ylabel('Carnot Efficiency, $\\eta_{Carnot}$')
    ax2.set_title('Carnot Heat Engine Efficiency\n$\\eta_{Carnot} = 1 - \\frac{T_L}{T_H}$')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Plot total efficiency for selected concentration ratios
    selected_C = [100, 1000, 3000]
    colors_sel = ['blue', 'red', 'orange']
    
    for i, C in enumerate(selected_C):
        eta_total = [total_efficiency(T_H, C, T_L) for T_H in T_H_range]
        ax3.plot(T_H_range, eta_total, color=colors_sel[i], linewidth=2, 
                label=f'C = {C} suns')
    
    ax3.set_xlabel('Temperature, $T_H$ [K]')
    ax3.set_ylabel('Total Efficiency, $\\eta_{total}$')
    ax3.set_title('Total System Efficiency\n$\\eta_{total} = \\eta_{recv} \\times \\eta_{Carnot}$')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    plt.tight_layout()
    plt.savefig('efficiency_components.png', dpi=300, bbox_inches='tight')
    plt.show()

def print_analysis(optimal_results):
    """Print Part B analysis results"""
    
    print("="*80)
    print("PROBLEM 14: CARNOT CYCLE HEAT ENGINES - ANALYSIS RESULTS")
    print("="*80)
    
    print("\nPART A: OPTIMAL OPERATING CONDITIONS")
    print("-" * 50)
    
    df = pd.DataFrame(optimal_results)
    df['T_H_optimal'] = df['T_H_optimal'].round(1)
    df['T_H_optimal_C'] = df['T_H_optimal_C'].round(1)
    df['eta_max'] = df['eta_max'].round(4)
    
    print(df.to_string(index=False, columns=['C', 'T_H_optimal', 'T_H_optimal_C', 'eta_max'],
                       formatters={
                           'C': '{:.0f}'.format,
                           'T_H_optimal': '{:.1f} K'.format,
                           'T_H_optimal_C': '{:.1f}°C'.format,
                           'eta_max': '{:.1%}'.format
                       }))
    
    print("\n" + "="*80)
    print("PART B: PHYSICAL ANALYSIS AND TRENDS")
    print("="*80)
    
    print("\n1. OPTIMAL TEMPERATURE TRENDS:")
    print(f"   • As concentration ratio increases from {min(concentration_ratios)} to {max(concentration_ratios)} suns:")
    print(f"   • Optimal T_H increases from {df['T_H_optimal'].min():.1f}K to {df['T_H_optimal'].max():.1f}K")
    print(f"   • Maximum efficiency increases from {df['eta_max'].min():.1%} to {df['eta_max'].max():.1%}")
    
    print("\n2. PHYSICAL TRADE-OFFS:")
    print("   • CARNOT EFFICIENCY: η_Carnot = 1 - T_L/T_H")
    print("     → Increases with T_H (better thermodynamic limit)")
    print("     → Approaches 100% as T_H → ∞")
    
    print("\n   • RECEIVER EFFICIENCY: η_receiver = 1 - σT_H⁴/(C·I)")
    print("     → Decreases with T_H (radiation losses scale as T⁴)")
    print("     → Higher concentration C offsets radiation losses")
    
    print("\n   • TOTAL EFFICIENCY: η_total = η_receiver × η_Carnot")
    print("     → Product of two competing effects")
    print("     → Optimum occurs where d(η_total)/dT_H = 0")
    
    print("\n3. CONCENTRATION RATIO EFFECTS:")
    print("   • Higher C allows operation at higher T_H before radiation losses dominate")
    print("   • Concentrated sunlight (C·I) must exceed radiation losses (σT_H⁴)")
    print("   • At very high T_H, even high concentration cannot overcome T⁴ losses")
    
    print("\n4. ENGINEERING IMPLICATIONS:")
    print("   • Lower concentration systems optimal at moderate temperatures")
    print("   • High concentration systems can achieve better efficiency at high temperatures")
    print("   • Trade-off between system complexity (high C) and performance")

def main():
    """Main analysis function"""
    
    print("Calculating concentrated solar power plant efficiency...")
    print("Parameters:")
    print(f"  Solar irradiance (I): {I} W/m²")
    print(f"  Cold reservoir (T_L): {T_L} K ({T_L-273.15:.1f}°C)")
    print(f"  Stefan-Boltzmann constant (σ): {SIGMA:.2e} W/(m²·K⁴)")
    print(f"  Temperature range: {T_H_min}-{T_H_max} K")
    print(f"  Concentration ratios: {concentration_ratios} suns")
    print()
    
    # Part A: Create efficiency plots
    optimal_results = create_efficiency_plots()
    
    # Additional component analysis
    analyze_component_efficiencies()
    
    # Part B: Analysis and discussion
    print_analysis(optimal_results)
    
    print(f"\n📊 Plots saved as 'carnot_cycle_efficiency.png' and 'efficiency_components.png'")
    print("✅ Problem 14 analysis complete!")

if __name__ == "__main__":
    main()