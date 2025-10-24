"""Terrain generation algorithms and height data creation.

Provides noise functions and terrain generation algorithms for procedural terrain.
Adapted from pandas3d terrain generation for ModernGL.
"""

import numpy as np
import math


def simple_noise(x, y, seed=0):
    """Simple pseudo-noise function using sine waves and random-like behavior.

    Args:
        x: X coordinate
        y: Y coordinate
        seed: Random seed for variation

    Returns:
        Float value between -1 and 1
    """
    # Use multiple sine waves with different frequencies and phases for more dramatic terrain
    n = (
        math.sin(x * 0.1 + seed) * 0.6
        + math.sin(y * 0.1 + seed * 1.1) * 0.6
        + math.sin((x + y) * 0.05 + seed * 1.3) * 0.4
        + math.sin((x - y) * 0.08 + seed * 1.7) * 0.3
        +
        # Add sharper features for mountain ridges
        math.sin(x * 0.03 + y * 0.02 + seed * 2.1) * 0.7
        + math.sin(math.sqrt(x * x + y * y) * 0.02 + seed * 3.7) * 0.5
    )
    return n / 2.5  # Normalize to roughly -1 to 1


def fractal_noise(x, y, octaves=4, persistence=0.5, lacunarity=2.0, seed=0):
    """Generate fractal noise by combining multiple octaves.

    Args:
        x: X coordinate
        y: Y coordinate
        octaves: Number of noise layers to combine
        persistence: How much each octave contributes (amplitude multiplier)
        lacunarity: Frequency multiplier for each octave
        seed: Random seed

    Returns:
        Float noise value
    """
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0

    for i in range(octaves):
        value += simple_noise(x * frequency, y * frequency, seed + i) * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    return value / max_value


def generate_donut_height_data(resolution, outer_radius=200, inner_radius=80, height=50, rim_width=40, seed=42):
    """Generate height data for a donut-shaped terrain with a thick, walkable top surface.

    Creates a 2D grid of height values forming a donut/torus shape with:
    - Flat walkable surface on the top rim
    - Smooth slopes on inner and outer edges
    - Procedural noise for natural variation
    - Angular variation for interesting shape

    Args:
        resolution: Number of vertices per edge (creates resolution x resolution grid)
        outer_radius: Outer radius of the donut
        inner_radius: Inner radius (hole size)
        height: Height of the donut rim
        rim_width: Width of the thick, flat top surface
        seed: Random seed for noise variation

    Returns:
        2D numpy array of height values (resolution x resolution)
    """
    heights = np.zeros((resolution, resolution))

    # Calculate the world size to fit the donut
    world_size = outer_radius * 2.2  # Add some padding
    spacing = world_size / (resolution - 1)

    for x in range(resolution):
        for z in range(resolution):
            # Calculate world position centered at origin
            world_x = (x * spacing) - (world_size / 2)
            world_z = (z * spacing) - (world_size / 2)

            # Calculate distance from center
            center_dist = math.sqrt(world_x * world_x + world_z * world_z)

            # Create donut shape with thick, flat top
            if center_dist <= outer_radius and center_dist >= inner_radius:
                # We're in the donut rim area

                # Calculate rim position (0 = inner edge, 1 = outer edge)
                rim_position = (center_dist - inner_radius) / (outer_radius - inner_radius)

                # Create thick, flat top surface in the middle of the rim
                inner_rim_start = 0.2  # Start of thick top (20% from inner edge)
                inner_rim_end = 0.8    # End of thick top (80% from inner edge)

                if rim_position >= inner_rim_start and rim_position <= inner_rim_end:
                    # We're on the thick top surface - make it flat and walkable
                    base_height = height

                    # Add very subtle noise for texture (much less than slopes)
                    noise_height = fractal_noise(
                        world_x * 0.02,
                        world_z * 0.02,
                        octaves=2,
                        persistence=0.3,
                        lacunarity=2.0,
                        seed=seed
                    ) * 1  # Very small noise for subtle texture

                    terrain_height = base_height + noise_height

                else:
                    # We're on the sloping edges of the donut
                    if rim_position < inner_rim_start:
                        # Inner slope (from hole to thick top)
                        slope_factor = rim_position / inner_rim_start
                        base_height = height * slope_factor
                    else:
                        # Outer slope (from thick top to ground)
                        slope_factor = (1 - rim_position) / (1 - inner_rim_end)
                        base_height = height * slope_factor

                    # Add more noise on slopes for natural appearance
                    noise_height = fractal_noise(
                        world_x * 0.01,
                        world_z * 0.01,
                        octaves=3,
                        persistence=0.5,
                        lacunarity=2.0,
                        seed=seed
                    ) * 3

                    terrain_height = base_height + noise_height

                # Add subtle angular variation for more interesting shape
                angle = math.atan2(world_z, world_x)
                angle_variation = math.sin(angle * 4) * 2  # 4 lobes, smaller variation
                terrain_height += angle_variation

                heights[x][z] = max(0, terrain_height)
            else:
                # Outside the donut - flat ground
                heights[x][z] = 0

    return heights
