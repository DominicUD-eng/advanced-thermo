#!/usr/bin/env python3
"""
Problem 14: Carnot Cycle Heat Engines - Plotting Analysis

Generates plots for concentrated solar power plant efficiency analysis
with matplotlib for professional visualization.
"""

import math
import matplotlib.pyplot as plt
import numpy as np
import os

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
    if eta_recv <= 0:  # Invalid operating regime
        return 0
    return eta_recv * eta_carnot

def find_optimal_temperature(C, T_L, tolerance=1e-3):
    """Find optimal temperature by scanning the valid range"""
    
    # Temperature range to search
    T_range = np.arange(T_L + 50, 2601, 1)  # 350K to 2600K in 1K steps
    
    max_efficiency = -1
    optimal_T_H = T_L + 50
    
    for T_H in T_range:
        eta = total_efficiency(T_H, C, T_L)
        if eta > max_efficiency:
            max_efficiency = eta
            optimal_T_H = T_H
    
    return float(optimal_T_H), max_efficiency

def create_efficiency_plot():
    """Create the main efficiency vs temperature plot"""
    
    # Temperature range for plotting (K)
    T_H_range = np.linspace(350, 2600, 300)
    
    plt.figure(figsize=(12, 8))
    
    # Colors for different concentration ratios
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    # Plot efficiency curves for each concentration ratio
    for i, C in enumerate(concentration_ratios):
        efficiencies = []
        valid_temps = []
        
        for T_H in T_H_range:
            eta = total_efficiency(T_H, C, T_L)
            if eta > 0:  # Only plot positive efficiencies
                efficiencies.append(eta * 100)  # Convert to percentage
                valid_temps.append(T_H)
        
        if valid_temps:
            plt.plot(valid_temps, efficiencies, color=colors[i], 
                    linewidth=2.5, label=f'C = {C} suns')
            
            # Mark optimal point
            T_opt, eta_opt = find_optimal_temperature(C, T_L)
            if eta_opt > 0:
                plt.plot(T_opt, eta_opt * 100, 'o', color=colors[i], 
                        markersize=8, markeredgecolor='black', markeredgewidth=1.5)
    
    plt.xlabel('Hot Reservoir Temperature, $T_H$ (K)', fontsize=14)
    plt.ylabel('Total System Efficiency, $η_{total}$ (%)', fontsize=14)
    plt.title('Concentrated Solar Power Plant Efficiency vs Operating Temperature', fontsize=16, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Formatting
    plt.xlim(350, 2600)
    plt.ylim(0, 80)
    plt.xticks(np.arange(400, 2601, 200))
    plt.yticks(np.arange(0, 81, 10))
    
    # Add annotation
    plt.text(0.02, 0.98, 'Optimal points marked with circles', 
             transform=plt.gca().transAxes, fontsize=10, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # Save plot
    output_dir = "../images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    plt.savefig(f"{output_dir}/carnot_efficiency_plot.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{output_dir}/carnot_efficiency_plot.pdf", bbox_inches='tight')
    
    print("✅ Plot saved as carnot_efficiency_plot.png and .pdf")
    return plt.gcf()

def create_component_efficiency_plot():
    """Create plots showing receiver and Carnot efficiencies separately"""
    
    T_H_range = np.linspace(350, 2600, 300)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    # Receiver efficiency plot
    for i, C in enumerate(concentration_ratios):
        eta_recv = [receiver_efficiency(T_H, C) * 100 for T_H in T_H_range]
        eta_recv = [max(0, eta) for eta in eta_recv]  # Remove negative values
        ax1.plot(T_H_range, eta_recv, color=colors[i], linewidth=2.5, label=f'C = {C} suns')
    
    ax1.set_xlabel('Hot Reservoir Temperature, $T_H$ (K)', fontsize=12)
    ax1.set_ylabel('Receiver Efficiency, $η_{receiver}$ (%)', fontsize=12)
    ax1.set_title('Solar Receiver Efficiency vs Temperature', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    ax1.set_xlim(350, 2600)
    ax1.set_ylim(0, 100)
    
    # Carnot efficiency plot
    eta_carnot = [carnot_efficiency(T_H, T_L) * 100 for T_H in T_H_range]
    ax2.plot(T_H_range, eta_carnot, color='black', linewidth=2.5, label='Carnot Limit')
    
    ax2.set_xlabel('Hot Reservoir Temperature, $T_H$ (K)', fontsize=12)
    ax2.set_ylabel('Carnot Efficiency, $η_{Carnot}$ (%)', fontsize=12)
    ax2.set_title('Carnot Heat Engine Efficiency vs Temperature', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10)
    ax2.set_xlim(350, 2600)
    ax2.set_ylim(0, 100)
    
    plt.tight_layout()
    
    # Save plot
    output_dir = "../images"
    plt.savefig(f"{output_dir}/carnot_components_plot.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{output_dir}/carnot_components_plot.pdf", bbox_inches='tight')
    
    print("✅ Component plots saved as carnot_components_plot.png and .pdf")
    return fig

def print_analysis_results():
    """Print the numerical analysis results"""
    
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
    
    print("OPTIMAL OPERATING CONDITIONS")
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
    return optimal_results

def main():
    """Main execution function"""
    
    print("Creating Carnot cycle efficiency plots...")
    print()
    
    # Print numerical results
    optimal_results = print_analysis_results()
    
    # Create plots
    print("Generating plots...")
    fig1 = create_efficiency_plot()
    fig2 = create_component_efficiency_plot()
    
    # Show plots
    plt.show()
    
    print()
    print("=" * 80)
    print("✅ Analysis and plotting complete!")
    print("📊 Plots saved in ../images/ directory")
    print("📈 Use plots in LaTeX document with \\includegraphics{}")

if __name__ == "__main__":
    main()