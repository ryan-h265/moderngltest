"""Terrain generation algorithms and height data creation."""

import numpy as np
import math
from testgame.config.settings import WORLD_TYPE, TERRAIN_RESOLUTION, MODIFIABLE_TERRAIN


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


class TerrainGenerator:
    """Handles terrain height data generation."""

    def __init__(self, chunk_size, resolution):
        """Initialize the terrain generator.

        Args:
            chunk_size: Size of each terrain chunk in world units
            resolution: Number of vertices per chunk edge
        """
        self.chunk_size = chunk_size
        self.resolution = resolution

    def generate_flat_terrain(self, resolution):
        """Generate flat terrain data.

        Args:
            resolution: Number of vertices per chunk edge

        Returns:
            2D numpy array of height values (all zeros)
        """
        return np.zeros((resolution + 1, resolution + 1))

    def generate_donut_terrain(self, chunk_x, chunk_z, world_x, world_z, 
                              outer_radius=200, inner_radius=80, height=50, rim_width=40):
        """Generate donut-shaped terrain with a thick, walkable top surface.

        Args:
            chunk_x: Chunk X coordinate
            chunk_z: Chunk Z coordinate  
            world_x: World X position of chunk
            world_z: World Z position of chunk
            outer_radius: Outer radius of the donut
            inner_radius: Inner radius (hole size)
            height: Height of the donut rim
            rim_width: Width of the thick, flat top surface

        Returns:
            2D numpy array of height values
        """
        heights = np.zeros((self.resolution + 1, self.resolution + 1))
        
        # Calculate spacing between vertices in world units
        spacing = self.chunk_size / self.resolution

        for x in range(self.resolution + 1):
            for z in range(self.resolution + 1):
                current_world_x = world_x + (x * spacing)
                current_world_z = world_z + (z * spacing)

                # Calculate distance from center
                center_dist = math.sqrt(current_world_x * current_world_x + current_world_z * current_world_z)
                
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
                        
                        # Add very subtle noise for texture (much less than before)
                        noise_height = fractal_noise(
                            current_world_x * 0.02,
                            current_world_z * 0.02,
                            octaves=2,
                            persistence=0.3,
                            lacunarity=2.0,
                            seed=42
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
                            current_world_x * 0.01,
                            current_world_z * 0.01,
                            octaves=3,
                            persistence=0.5,
                            lacunarity=2.0,
                            seed=42
                        ) * 3
                        
                        terrain_height = base_height + noise_height
                    
                    # Add subtle angular variation for more interesting shape
                    angle = math.atan2(current_world_z, current_world_x)
                    angle_variation = math.sin(angle * 4) * 2  # 4 lobes, smaller variation
                    terrain_height += angle_variation
                    
                    heights[x][z] = max(0, terrain_height)
                else:
                    # Outside the donut - flat ground
                    heights[x][z] = 0

        return heights

    def generate_height_data(self, chunk_x, chunk_z, world_x, world_z):
        """Generate height data for a terrain chunk using donut terrain generation.

        Args:
            chunk_x: Chunk X coordinate
            chunk_z: Chunk Z coordinate
            world_x: World X position of chunk
            world_z: World Z position of chunk

        Returns:
            2D numpy array of height values
        """
        # If flat world is enabled, use donut terrain instead of flat plane
        if WORLD_TYPE == "donut":
            return self.generate_donut_terrain(
                chunk_x, chunk_z, world_x, world_z,
                outer_radius=200, inner_radius=80, height=50
            )
        elif WORLD_TYPE == "flat":
            return self.generate_flat_terrain(self.resolution)
        elif WORLD_TYPE == "mountain":
            return self.generate_mountain_terrain(chunk_x, chunk_z, world_x, world_z)
        else:
            raise ValueError(f"Unknown WORLD_TYPE: {WORLD_TYPE}")

    def generate_mountain_terrain(self, chunk_x, chunk_z, world_x, world_z):
        """Generate mountainous terrain data for a chunk.
        Args:
            chunk_x: Chunk X coordinate
            chunk_z: Chunk Z coordinate
            world_x: World X position of chunk
            world_z: World Z position of chunk
        Returns:
            2D numpy array of height values
        """
        heights = np.zeros((self.resolution + 1, self.resolution + 1))

        # Calculate spacing between vertices in world units
        spacing = self.chunk_size / self.resolution

        for x in range(self.resolution + 1):
            for z in range(self.resolution + 1):
                current_world_x = world_x + (x * spacing)
                current_world_z = world_z + (z * spacing)

                # Multi-octave noise for Everest-like mountainous terrain with large base
                height = 0

                # Distance from center (0,0) for pyramid-like structure
                center_dist = math.sqrt(current_world_x * current_world_x + current_world_z * current_world_z)

                # Create a large stable base around the mountain (like a plateau/valley floor)
                # This creates a flat-ish area extending far from the mountain
                base_radius = 400  # Large base area radius
                if center_dist > base_radius:
                    # Far from mountain - create gentle rolling hills at base level
                    base_height = (
                        20
                        + fractal_noise(
                            current_world_x * 0.002,
                            current_world_z * 0.002,
                            octaves=3,
                            persistence=0.3,
                            lacunarity=2.0,
                            seed=10,
                        )
                        * 15
                    )
                else:
                    # Within base area - gradually rise toward mountain
                    base_height = 20 + (base_radius - center_dist) / base_radius * 50

                height += base_height

                # Mountain structure only applies within a certain radius
                mountain_radius = 300
                if center_dist < mountain_radius:
                    # Mountain influence factor (1.0 at center, 0.0 at mountain_radius)
                    mountain_factor = max(
                        0, (mountain_radius - center_dist) / mountain_radius
                    )

                    # Primary mountain mass - creates the main peak structure
                    primary_mountain = (
                        fractal_noise(
                            current_world_x * 0.003,
                            current_world_z * 0.003,
                            octaves=8,
                            persistence=0.8,
                            lacunarity=2.3,
                            seed=0,
                        )
                        * 650
                        * mountain_factor  # Slightly taller for more dramatic peaks
                    )
                    height += max(0, primary_mountain)

                    # Sharp ridges and knife-edge features (aretes)
                    ridge_noise = abs(
                        fractal_noise(
                            current_world_x * 0.006,
                            current_world_z * 0.006,
                            octaves=6,
                            persistence=0.9,
                            lacunarity=2.8,
                            seed=1,
                        )
                    )
                    height += ridge_noise * 450 * mountain_factor

                    # Vertical cliff faces and ice walls
                    # Using stepped noise to create sheer vertical sections
                    cliff_noise = fractal_noise(
                        current_world_x * 0.008,
                        current_world_z * 0.008,
                        octaves=4,
                        persistence=0.7,
                        lacunarity=2.4,
                        seed=3,
                    )
                    # Create terraced cliff effect by quantizing the noise
                    cliff_steps = math.floor(abs(cliff_noise) * 8) / 8.0
                    cliff_height = cliff_steps * 280 * mountain_factor
                    height += cliff_height

                    # Secondary peaks and shoulders
                    secondary_peaks = (
                        fractal_noise(
                            current_world_x * 0.01,
                            current_world_z * 0.01,
                            octaves=5,
                            persistence=0.7,
                            lacunarity=2.2,
                            seed=2,
                        )
                        * 280
                        * mountain_factor
                    )
                    height += max(0, secondary_peaks)

                    # Ice walls and seracs (ice formations)
                    ice_wall_noise = abs(
                        fractal_noise(
                            current_world_x * 0.012,
                            current_world_z * 0.012,
                            octaves=5,
                            persistence=0.75,
                            lacunarity=2.6,
                            seed=6,
                        )
                    )
                    # Create steep ice wall sections
                    if ice_wall_noise > 0.4:
                        ice_wall_height = (ice_wall_noise - 0.4) * 200 * mountain_factor
                        height += ice_wall_height

                    # Rock face stratification (horizontal banding)
                    rock_layers = fractal_noise(
                        current_world_x * 0.001,
                        current_world_z * 0.015,
                        octaves=3,
                        persistence=0.5,
                        lacunarity=2.0,
                        seed=7,
                    )
                    height += abs(rock_layers) * 80 * mountain_factor

                    # Fine rocky details and surface texture
                    surface_detail = (
                        fractal_noise(
                            current_world_x * 0.04,
                            current_world_z * 0.04,
                            octaves=3,
                            persistence=0.4,
                            lacunarity=2.0,
                            seed=4,
                        )
                        * 60
                        * mountain_factor
                    )
                    height += max(0, surface_detail)

                    # Glacial features and crevasses
                    glacial_features = (
                        fractal_noise(
                            current_world_x * 0.015,
                            current_world_z * 0.015,
                            octaves=3,
                            persistence=0.5,
                            lacunarity=2.1,
                            seed=5,
                        )
                        * 100
                        * mountain_factor
                    )
                    height += max(0, glacial_features)

                    # Cornices and overhanging snow features at higher elevations
                    if height > 400:
                        cornice_noise = fractal_noise(
                            current_world_x * 0.025,
                            current_world_z * 0.025,
                            octaves=2,
                            persistence=0.6,
                            lacunarity=2.0,
                            seed=8,
                        )
                        height += abs(cornice_noise) * 40 * mountain_factor

                # Ensure reasonable minimum height
                height = max(height, 15)

                heights[x][z] = height

        return heights
