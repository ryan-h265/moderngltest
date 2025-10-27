"""
TERRAIN GENERATION USAGE GUIDE
==============================

This guide explains how to use the fractal terrain generation system
and tune parameters to avoid the "garbage output" problem.
"""

import numpy as np
import matplotlib.pyplot as plt
from fractal_terrain import FractalTerrain, TerrainErosion, generate_mountain_terrain
from terrain_advanced import AdvancedTerrain, TerrainPresets


# =============================================================================
# QUICK START - Using Presets (Recommended for beginners)
# =============================================================================

def quick_start_example():
    """The easiest way to get good results - use presets!"""
    
    # Create terrain generator
    terrain_gen = AdvancedTerrain(width=512, height=512, seed=42)
    
    # Generate using a preset (no parameter tuning needed!)
    terrain = terrain_gen.generate_with_preset('mountain_range')
    
    # That's it! The preset handles all the parameter balancing
    return terrain


# =============================================================================
# PARAMETER TUNING GUIDE - Avoiding "Garbage Output"
# =============================================================================

def understanding_parameters():
    """
    Critical parameters and their safe ranges to avoid broken terrain.
    
    THE MAIN CULPRITS OF BAD TERRAIN:
    1. Persistence too high (>0.7) = Too noisy, loses structure
    2. Erosion rate too high (>0.5) = Terrain becomes flat mud
    3. Too many octaves (>10) = Excessive detail, loses large features
    4. Scale too small (<20) = Features too tiny to see
    5. Hydraulic iterations too high (>100000) = Over-eroded flat terrain
    """
    
    # SAFE PARAMETER RANGES (stick to these to avoid problems):
    safe_params = {
        'octaves': (3, 8),           # Number of detail layers
        'persistence': (0.2, 0.65),   # How rough the terrain is
        'lacunarity': (1.8, 2.5),     # Frequency scaling between octaves
        'scale': (50, 200),           # Size of terrain features
        'erosion_rate': (0.1, 0.45),  # Hydraulic erosion strength
        'hydraulic_iterations': (0, 60000),  # Erosion simulation steps
        'talus_angle': (0.3, 0.6),    # Thermal erosion angle
        'warp_strength': (0.0, 0.25),  # Domain warping amount
    }
    
    return safe_params


# =============================================================================
# STEP-BY-STEP PARAMETER TUNING
# =============================================================================

def parameter_tuning_workflow():
    """
    Recommended workflow for tuning parameters from scratch.
    Follow these steps IN ORDER to avoid garbage output!
    """
    
    width, height = 256, 256
    seed = 42
    
    # STEP 1: Start with basic noise (no erosion yet!)
    print("Step 1: Basic terrain shape")
    terrain_gen = FractalTerrain(width, height, seed)
    
    # Start with conservative values
    terrain = terrain_gen.generate_fractal_noise(
        octaves=5,        # Start with 5, adjust ±2
        persistence=0.5,  # Start at 0.5, adjust ±0.15
        lacunarity=2.0,   # Usually leave at 2.0
        scale=100.0,      # Start at 100, adjust 50-150
        ridge_noise=False # Try both False and True
    )
    
    # STEP 2: Add domain warping (optional, adds realism)
    print("Step 2: Domain warping")
    terrain = terrain_gen.apply_domain_warping(
        warp_strength=0.1  # Start at 0.1, max 0.25
    )
    
    # STEP 3: Add LIGHT erosion first
    print("Step 3: Light erosion test")
    erosion = TerrainErosion(terrain)
    terrain = erosion.hydraulic_erosion(
        iterations=10000,      # Start low!
        erosion_rate=0.3,      # Start at 0.3
        sediment_capacity=4.0,  # Usually fine at 4.0
        deposition_rate=0.3     # Match erosion_rate initially
    )
    
    # STEP 4: If happy, increase erosion gradually
    print("Step 4: Refined erosion")
    # Only increase if terrain still has good features!
    
    return terrain


# =============================================================================
# COMMON PROBLEMS AND SOLUTIONS
# =============================================================================

def fixing_common_problems():
    """Solutions to common parameter tuning problems."""
    
    problems_and_solutions = {
        "Terrain is completely flat": [
            "- Reduce hydraulic_iterations (try half)",
            "- Reduce erosion_rate (max 0.4)",
            "- Increase persistence slightly",
            "- Check if scale is too small"
        ],
        
        "Terrain is just random noise": [
            "- Reduce octaves (max 8)",
            "- Reduce persistence (max 0.6)",
            "- Increase scale (try 1.5x current)",
            "- Disable ridge_noise if enabled"
        ],
        
        "No mountain peaks visible": [
            "- Enable ridge_noise=True",
            "- Increase persistence to 0.55-0.65",
            "- Reduce erosion iterations",
            "- Increase base_amplitude"
        ],
        
        "Terrain looks artificial/geometric": [
            "- Enable domain warping",
            "- Increase warp_strength to 0.15",
            "- Add more octaves (6-7)",
            "- Apply hydraulic erosion"
        ],
        
        "Erosion creates unrealistic channels": [
            "- Reduce erosion_rate",
            "- Increase evaporation_rate",
            "- Reduce sediment_capacity",
            "- Add thermal erosion after hydraulic"
        ]
    }
    
    return problems_and_solutions


# =============================================================================
# COMPLETE EXAMPLES WITH DIFFERENT STYLES
# =============================================================================

def gentle_hills_example():
    """Create gentle, rolling hills (easy difficulty)."""
    
    terrain = generate_mountain_terrain(
        width=512, height=512, seed=42,
        # Smooth parameters
        octaves=4,                # Few octaves = smooth
        persistence=0.35,          # Low persistence = gentle
        lacunarity=2.0,
        scale=80,                  # Medium-large features
        ridge_noise=False,         # No sharp ridges
        # Light erosion
        hydraulic_iterations=5000,  # Light water erosion
        erosion_rate=0.25,
        thermal_iterations=10
    )
    return terrain


def sharp_mountains_example():
    """Create sharp, Alpine-style peaks (medium difficulty)."""
    
    terrain = generate_mountain_terrain(
        width=512, height=512, seed=42,
        # Sharp mountain parameters
        octaves=7,                 # More detail
        persistence=0.6,           # Higher = rougher
        lacunarity=2.2,
        scale=120,
        ridge_noise=True,          # Creates sharp ridges!
        # Moderate erosion
        hydraulic_iterations=20000,
        erosion_rate=0.35,
        thermal_iterations=25,
        talus_angle=0.4           # Steeper slopes allowed
    )
    return terrain


def heavily_eroded_canyon():
    """Create canyon-like eroded terrain (hard difficulty - easy to break!)."""
    
    # BE CAREFUL with these parameters!
    terrain = generate_mountain_terrain(
        width=512, height=512, seed=42,
        # Start with medium terrain
        octaves=5,
        persistence=0.45,
        lacunarity=2.1,
        scale=90,
        ridge_noise=False,
        # Heavy erosion (DANGER ZONE - tune carefully!)
        hydraulic_iterations=50000,  # High but not too high
        erosion_rate=0.4,            # Near maximum safe value
        thermal_iterations=20,
        talus_angle=0.35             # Lower = more collapse
    )
    return terrain


# =============================================================================
# INTERACTIVE PARAMETER EXPLORER
# =============================================================================

def interactive_parameter_test():
    """
    Test different parameter values to understand their effects.
    Run this to see how each parameter changes the terrain!
    """
    
    fig, axes = plt.subplots(3, 3, figsize=(15, 15))
    
    # Base parameters
    base_params = {
        'width': 256, 'height': 256, 'seed': 42,
        'octaves': 5, 'persistence': 0.5, 'lacunarity': 2.0,
        'scale': 100, 'ridge_noise': False,
        'hydraulic_iterations': 10000, 'erosion_rate': 0.3
    }
    
    # Test variations
    tests = [
        ('Base Settings', {}),
        ('High Octaves (8)', {'octaves': 8}),
        ('Low Octaves (3)', {'octaves': 3}),
        ('High Persistence (0.65)', {'persistence': 0.65}),
        ('Low Persistence (0.3)', {'persistence': 0.3}),
        ('Large Scale (150)', {'scale': 150}),
        ('Small Scale (50)', {'scale': 50}),
        ('Ridge Noise', {'ridge_noise': True}),
        ('Heavy Erosion', {'hydraulic_iterations': 40000, 'erosion_rate': 0.4})
    ]
    
    for idx, (title, params) in enumerate(tests):
        row, col = idx // 3, idx % 3
        
        # Merge parameters
        test_params = base_params.copy()
        test_params.update(params)
        
        # Generate terrain
        terrain = generate_mountain_terrain(**test_params)
        
        # Display
        im = axes[row, col].imshow(terrain, cmap='terrain', vmin=0, vmax=1)
        axes[row, col].set_title(title)
        axes[row, col].axis('off')
    
    plt.suptitle('Parameter Effects on Terrain', fontsize=16)
    plt.tight_layout()
    return fig


# =============================================================================
# MAIN EXECUTION - Demonstrates everything
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FRACTAL TERRAIN GENERATION - USAGE GUIDE")
    print("=" * 60)
    
    # Show safe parameter ranges
    print("\nSAFE PARAMETER RANGES:")
    safe_params = understanding_parameters()
    for param, (min_val, max_val) in safe_params.items():
        print(f"  {param:20s}: {min_val:6.2f} - {max_val:6.2f}")
    
    # Generate example terrains
    print("\nGenerating example terrains...")
    
    # Method 1: Using presets (easiest)
    print("\n1. Using preset (easiest method):")
    terrain1 = quick_start_example()
    print(f"   Generated terrain shape: {terrain1.shape}")
    
    # Method 2: Manual parameters
    print("\n2. Manual parameter tuning:")
    terrain2 = parameter_tuning_workflow()
    print(f"   Generated terrain shape: {terrain2.shape}")
    
    # Show common problems
    print("\n3. Common Problems and Solutions:")
    problems = fixing_common_problems()
    for problem, solutions in problems.items():
        print(f"\n   Problem: {problem}")
        for solution in solutions:
            print(f"     {solution}")
    
    # Generate comparison plot
    print("\n4. Generating comparison plots...")
    fig = interactive_parameter_test()
    plt.show()
    
    # Generate different terrain styles
    print("\n5. Generating different terrain styles...")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    terrain_gentle = gentle_hills_example()
    terrain_sharp = sharp_mountains_example()
    terrain_canyon = heavily_eroded_canyon()
    
    axes[0].imshow(terrain_gentle, cmap='terrain')
    axes[0].set_title('Gentle Hills')
    axes[0].axis('off')
    
    axes[1].imshow(terrain_sharp, cmap='terrain')
    axes[1].set_title('Sharp Alpine Peaks')
    axes[1].axis('off')
    
    axes[2].imshow(terrain_canyon, cmap='terrain')
    axes[2].set_title('Eroded Canyons')
    axes[2].axis('off')
    
    plt.suptitle('Different Terrain Styles', fontsize=16)
    plt.tight_layout()
    plt.show()
    
    print("\n" + "=" * 60)
    print("GUIDE COMPLETE!")
    print("Remember: Start with presets or safe parameter ranges.")
    print("Tune gradually and test each change!")
    print("=" * 60)
