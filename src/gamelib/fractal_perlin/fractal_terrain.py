"""
Fractal Terrain Generation with Perlin Noise and Erosion Simulation
Author: Claude
Description: Generate realistic mountain terrain using fractal Perlin noise
            and hydraulic/thermal erosion simulation.
"""

import numpy as np
from typing import Tuple, Optional
import math


class PerlinNoise:
    """Basic Perlin noise implementation for terrain generation."""
    
    def __init__(self, seed: int = 42):
        """Initialize Perlin noise with a seed for reproducibility."""
        np.random.seed(seed)
        self.permutation = np.arange(256, dtype=int)
        np.random.shuffle(self.permutation)
        self.permutation = np.tile(self.permutation, 2)
        
    def _fade(self, t: np.ndarray) -> np.ndarray:
        """Fade function for smooth interpolation."""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, t: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Linear interpolation."""
        return a + t * (b - a)
    
    def _grad(self, hash_val: int, x: float, y: float) -> float:
        """Calculate gradient contribution."""
        h = hash_val & 3
        if h == 0:
            return x + y
        elif h == 1:
            return -x + y
        elif h == 2:
            return x - y
        else:
            return -x - y
    
    def noise(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Generate 2D Perlin noise."""
        # Find unit grid cell containing point
        xi = np.floor(x).astype(int) & 255
        yi = np.floor(y).astype(int) & 255
        
        # Find relative x,y of point in cell
        xf = x - np.floor(x)
        yf = y - np.floor(y)
        
        # Compute fade curves
        u = self._fade(xf)
        v = self._fade(yf)
        
        # Hash coordinates of the 4 cube corners
        aa = self.permutation[self.permutation[xi] + yi]
        ab = self.permutation[self.permutation[xi] + yi + 1]
        ba = self.permutation[self.permutation[xi + 1] + yi]
        bb = self.permutation[self.permutation[xi + 1] + yi + 1]
        
        # Calculate gradient contributions from each corner
        result = np.zeros_like(x)
        for i in range(x.shape[0]):
            for j in range(x.shape[1]):
                # Gradients at corners
                g_aa = self._grad(aa[i, j], xf[i, j], yf[i, j])
                g_ba = self._grad(ba[i, j], xf[i, j] - 1, yf[i, j])
                g_ab = self._grad(ab[i, j], xf[i, j], yf[i, j] - 1)
                g_bb = self._grad(bb[i, j], xf[i, j] - 1, yf[i, j] - 1)
                
                # Interpolate
                x1 = self._lerp(u[i, j], g_aa, g_ba)
                x2 = self._lerp(u[i, j], g_ab, g_bb)
                result[i, j] = self._lerp(v[i, j], x1, x2)
        
        return result


class FractalTerrain:
    """Generate fractal terrain using layered Perlin noise."""
    
    def __init__(self, 
                 width: int = 512, 
                 height: int = 512,
                 seed: int = 42):
        """
        Initialize fractal terrain generator.
        
        Args:
            width: Width of the terrain grid
            height: Height of the terrain grid
            seed: Random seed for reproducibility
        """
        self.width = width
        self.height = height
        self.seed = seed
        self.perlin = PerlinNoise(seed)
        self.terrain = None
        
    def generate_fractal_noise(self,
                               octaves: int = 6,
                               persistence: float = 0.5,
                               lacunarity: float = 2.0,
                               scale: float = 100.0,
                               base_amplitude: float = 1.0,
                               ridge_noise: bool = False,
                               ridge_offset: float = 1.0) -> np.ndarray:
        """
        Generate fractal noise by layering multiple octaves of Perlin noise.
        
        Args:
            octaves: Number of noise layers to combine (more = more detail)
                    Typical: 4-8. Higher values add finer details.
            persistence: How much each octave contributes (amplitude multiplier)
                        Range: 0.0-1.0. Lower = smoother, Higher = rougher
                        Typical: 0.4-0.6
            lacunarity: Frequency multiplier between octaves
                       Typical: 2.0. Higher = more rapid frequency increase
            scale: Base frequency of the noise (size of features)
                  Lower = larger features, Higher = smaller features
            base_amplitude: Initial amplitude of the first octave
            ridge_noise: If True, creates ridged mountains (sharp peaks)
            ridge_offset: Offset for ridge calculation (typically 0.7-1.0)
            
        Returns:
            2D array of fractal noise values
        """
        # Create coordinate grids
        x = np.linspace(0, self.width / scale, self.width)
        y = np.linspace(0, self.height / scale, self.height)
        xx, yy = np.meshgrid(x, y)
        
        # Initialize the terrain
        terrain = np.zeros((self.height, self.width))
        amplitude = base_amplitude
        frequency = 1.0
        max_value = 0.0  # For normalizing
        
        for octave in range(octaves):
            # Generate noise at this octave
            noise = self.perlin.noise(xx * frequency, yy * frequency)
            
            if ridge_noise:
                # Create ridged noise (sharp mountain peaks)
                noise = ridge_offset - np.abs(noise)
                noise = noise * noise  # Square to sharpen ridges
            
            # Add to terrain with current amplitude
            terrain += noise * amplitude
            
            # Update values for next octave
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        
        # Normalize to [0, 1]
        terrain = terrain / max_value
        terrain = (terrain - terrain.min()) / (terrain.max() - terrain.min())
        
        self.terrain = terrain
        return terrain
    
    def apply_domain_warping(self,
                            warp_strength: float = 0.1,
                            warp_scale: float = 50.0) -> np.ndarray:
        """
        Apply domain warping to create more interesting, natural-looking features.
        
        Args:
            warp_strength: How much to warp the terrain (0.0-1.0)
            warp_scale: Scale of the warping noise
            
        Returns:
            Warped terrain
        """
        if self.terrain is None:
            raise ValueError("Generate terrain first using generate_fractal_noise()")
        
        # Generate warping offsets
        x = np.linspace(0, self.width / warp_scale, self.width)
        y = np.linspace(0, self.height / warp_scale, self.height)
        xx, yy = np.meshgrid(x, y)
        
        warp_x = self.perlin.noise(xx, yy) * warp_strength * self.width
        warp_y = self.perlin.noise(xx + 100, yy + 100) * warp_strength * self.height
        
        # Create warped coordinates
        indices_x = np.clip(np.arange(self.width)[None, :] + warp_x, 0, self.width - 1).astype(int)
        indices_y = np.clip(np.arange(self.height)[:, None] + warp_y, 0, self.height - 1).astype(int)
        
        # Apply warping
        self.terrain = self.terrain[indices_y, indices_x]
        return self.terrain


class TerrainErosion:
    """Simulate erosion to create more realistic terrain."""
    
    def __init__(self, terrain: np.ndarray):
        """
        Initialize erosion simulator.
        
        Args:
            terrain: 2D heightmap array to erode
        """
        self.terrain = terrain.copy()
        self.height = terrain.shape[0]
        self.width = terrain.shape[1]
        
    def hydraulic_erosion(self,
                          iterations: int = 50000,
                          rain_amount: float = 0.01,
                          evaporation_rate: float = 0.01,
                          sediment_capacity: float = 4.0,
                          deposition_rate: float = 0.3,
                          erosion_rate: float = 0.3,
                          gravity: float = 4.0,
                          max_lifetime: int = 30,
                          inertia: float = 0.05) -> np.ndarray:
        """
        Simulate hydraulic erosion (water flowing and carving terrain).
        
        Args:
            iterations: Number of water droplets to simulate
            rain_amount: Initial water volume of each droplet
            evaporation_rate: Rate at which water evaporates
            sediment_capacity: Maximum sediment a droplet can carry
            deposition_rate: Rate of sediment deposition (0.0-1.0)
            erosion_rate: Rate of terrain erosion (0.0-1.0)
            gravity: Acceleration due to gravity
            max_lifetime: Maximum steps per droplet
            inertia: How much previous direction affects movement (0.0-1.0)
            
        Returns:
            Eroded terrain
        """
        for _ in range(iterations):
            # Random starting position
            pos_x = np.random.uniform(1, self.width - 2)
            pos_y = np.random.uniform(1, self.height - 2)
            
            # Initial droplet properties
            dir_x, dir_y = 0, 0
            speed = 1.0
            water = rain_amount
            sediment = 0.0
            
            for lifetime in range(max_lifetime):
                # Get grid coordinates
                grid_x = int(pos_x)
                grid_y = int(pos_y)
                
                # Check bounds
                if (grid_x <= 0 or grid_x >= self.width - 1 or 
                    grid_y <= 0 or grid_y >= self.height - 1):
                    break
                
                # Calculate height gradient using bilinear interpolation
                cell_x = pos_x - grid_x
                cell_y = pos_y - grid_y
                
                # Get heights of surrounding cells
                heights = np.array([
                    [self.terrain[grid_y, grid_x],     self.terrain[grid_y, grid_x + 1]],
                    [self.terrain[grid_y + 1, grid_x], self.terrain[grid_y + 1, grid_x + 1]]
                ])
                
                # Bilinear interpolation for current height
                height_x0 = heights[0, 0] * (1 - cell_x) + heights[0, 1] * cell_x
                height_x1 = heights[1, 0] * (1 - cell_x) + heights[1, 1] * cell_x
                height = height_x0 * (1 - cell_y) + height_x1 * cell_y
                
                # Calculate gradient
                grad_x = (heights[0, 1] - heights[0, 0]) * (1 - cell_y) + \
                        (heights[1, 1] - heights[1, 0]) * cell_y
                grad_y = (heights[1, 0] - heights[0, 0]) * (1 - cell_x) + \
                        (heights[1, 1] - heights[0, 1]) * cell_x
                
                # Update direction with inertia
                new_dir_x = grad_x * (1 - inertia) - dir_x * inertia
                new_dir_y = grad_y * (1 - inertia) - dir_y * inertia
                
                # Normalize direction
                dir_len = np.sqrt(new_dir_x**2 + new_dir_y**2)
                if dir_len > 0:
                    new_dir_x /= dir_len
                    new_dir_y /= dir_len
                
                dir_x, dir_y = new_dir_x, new_dir_y
                
                # Update position
                pos_x += dir_x
                pos_y += dir_y
                
                # Stop if stuck or out of bounds
                if (dir_len == 0 or pos_x < 1 or pos_x >= self.width - 1 or 
                    pos_y < 1 or pos_y >= self.height - 1):
                    break
                
                # Calculate new height after moving
                new_grid_x = int(pos_x)
                new_grid_y = int(pos_y)
                new_cell_x = pos_x - new_grid_x
                new_cell_y = pos_y - new_grid_y
                
                new_heights = np.array([
                    [self.terrain[new_grid_y, new_grid_x],     
                     self.terrain[new_grid_y, new_grid_x + 1]],
                    [self.terrain[new_grid_y + 1, new_grid_x], 
                     self.terrain[new_grid_y + 1, new_grid_x + 1]]
                ])
                
                new_height_x0 = new_heights[0, 0] * (1 - new_cell_x) + \
                                new_heights[0, 1] * new_cell_x
                new_height_x1 = new_heights[1, 0] * (1 - new_cell_x) + \
                                new_heights[1, 1] * new_cell_x
                new_height = new_height_x0 * (1 - new_cell_y) + \
                            new_height_x1 * new_cell_y
                
                # Calculate height difference
                height_diff = new_height - height
                
                # Calculate sediment capacity
                capacity = max(-height_diff, 0.01) * speed * water * sediment_capacity
                
                # Erosion or deposition
                if sediment > capacity or height_diff > 0:
                    # Deposit sediment
                    amount_to_deposit = (sediment - capacity) * deposition_rate
                    if height_diff > 0:
                        amount_to_deposit = min(height_diff, sediment)
                    
                    sediment -= amount_to_deposit
                    self.terrain[grid_y, grid_x] += amount_to_deposit * (1 - cell_x) * (1 - cell_y)
                    self.terrain[grid_y, grid_x + 1] += amount_to_deposit * cell_x * (1 - cell_y)
                    self.terrain[grid_y + 1, grid_x] += amount_to_deposit * (1 - cell_x) * cell_y
                    self.terrain[grid_y + 1, grid_x + 1] += amount_to_deposit * cell_x * cell_y
                else:
                    # Erode terrain
                    amount_to_erode = min((capacity - sediment) * erosion_rate, -height_diff)
                    
                    sediment += amount_to_erode
                    self.terrain[grid_y, grid_x] -= amount_to_erode * (1 - cell_x) * (1 - cell_y)
                    self.terrain[grid_y, grid_x + 1] -= amount_to_erode * cell_x * (1 - cell_y)
                    self.terrain[grid_y + 1, grid_x] -= amount_to_erode * (1 - cell_x) * cell_y
                    self.terrain[grid_y + 1, grid_x + 1] -= amount_to_erode * cell_x * cell_y
                
                # Update speed and water
                speed = np.sqrt(speed * speed + height_diff * gravity)
                water *= (1 - evaporation_rate)
                
                # Stop if no water left
                if water <= 0:
                    break
        
        return self.terrain
    
    def thermal_erosion(self,
                        iterations: int = 50,
                        talus_angle: float = 0.5,
                        erosion_rate: float = 0.5) -> np.ndarray:
        """
        Simulate thermal erosion (material falling due to gravity).
        
        Args:
            iterations: Number of erosion iterations
            talus_angle: Maximum stable slope angle (typically 0.3-0.8)
            erosion_rate: Rate of material movement (0.0-1.0)
            
        Returns:
            Eroded terrain
        """
        for _ in range(iterations):
            # Calculate height differences to neighbors
            diff_right = np.zeros_like(self.terrain)
            diff_left = np.zeros_like(self.terrain)
            diff_down = np.zeros_like(self.terrain)
            diff_up = np.zeros_like(self.terrain)
            
            diff_right[:, :-1] = self.terrain[:, :-1] - self.terrain[:, 1:]
            diff_left[:, 1:] = self.terrain[:, 1:] - self.terrain[:, :-1]
            diff_down[:-1, :] = self.terrain[:-1, :] - self.terrain[1:, :]
            diff_up[1:, :] = self.terrain[1:, :] - self.terrain[:-1, :]
            
            # Find unstable slopes
            max_diff = np.maximum.reduce([diff_right, diff_left, diff_down, diff_up])
            
            # Move material where slope exceeds talus angle
            unstable = max_diff > talus_angle
            erosion_amount = np.where(unstable, (max_diff - talus_angle) * erosion_rate, 0)
            
            # Distribute eroded material to neighbors
            self.terrain -= erosion_amount
            
            # Add to lower neighbors
            self.terrain[:, 1:] += np.where(diff_right[:, :-1] == max_diff[:, :-1], 
                                           erosion_amount[:, :-1] * 0.25, 0)
            self.terrain[:, :-1] += np.where(diff_left[:, 1:] == max_diff[:, 1:], 
                                            erosion_amount[:, 1:] * 0.25, 0)
            self.terrain[1:, :] += np.where(diff_down[:-1, :] == max_diff[:-1, :], 
                                           erosion_amount[:-1, :] * 0.25, 0)
            self.terrain[:-1, :] += np.where(diff_up[1:, :] == max_diff[1:, :], 
                                            erosion_amount[1:, :] * 0.25, 0)
        
        return self.terrain


def generate_mountain_terrain(width: int = 512,
                             height: int = 512,
                             seed: int = 42,
                             # Fractal noise parameters
                             octaves: int = 6,
                             persistence: float = 0.5,
                             lacunarity: float = 2.0,
                             scale: float = 100.0,
                             ridge_noise: bool = True,
                             # Domain warping
                             apply_warping: bool = True,
                             warp_strength: float = 0.1,
                             # Hydraulic erosion
                             hydraulic_iterations: int = 30000,
                             erosion_rate: float = 0.3,
                             # Thermal erosion  
                             thermal_iterations: int = 20,
                             talus_angle: float = 0.4) -> np.ndarray:
    """
    Generate complete mountain terrain with fractal noise and erosion.
    
    This is a high-level function that combines all techniques.
    
    Args:
        width, height: Dimensions of the terrain
        seed: Random seed for reproducibility
        octaves: Number of noise layers (4-8 typical)
        persistence: Amplitude decay per octave (0.4-0.6 typical)
        lacunarity: Frequency multiplier (2.0 typical)
        scale: Base feature size (50-200 typical)
        ridge_noise: Create sharp mountain ridges if True
        apply_warping: Apply domain warping for more natural shapes
        warp_strength: Strength of domain warping (0.05-0.2)
        hydraulic_iterations: Number of water droplets to simulate
        erosion_rate: Hydraulic erosion strength (0.2-0.5)
        thermal_iterations: Number of thermal erosion passes
        talus_angle: Maximum stable slope (0.3-0.6)
    
    Returns:
        Generated terrain as 2D numpy array (values 0-1)
    """
    # Generate fractal terrain
    terrain_gen = FractalTerrain(width, height, seed)
    terrain = terrain_gen.generate_fractal_noise(
        octaves=octaves,
        persistence=persistence,
        lacunarity=lacunarity,
        scale=scale,
        ridge_noise=ridge_noise
    )
    
    # Apply domain warping
    if apply_warping:
        terrain = terrain_gen.apply_domain_warping(warp_strength)
    
    # Apply erosion
    erosion = TerrainErosion(terrain)
    
    # Hydraulic erosion
    if hydraulic_iterations > 0:
        terrain = erosion.hydraulic_erosion(
            iterations=hydraulic_iterations,
            erosion_rate=erosion_rate
        )
    
    # Thermal erosion
    if thermal_iterations > 0:
        terrain = erosion.thermal_erosion(
            iterations=thermal_iterations,
            talus_angle=talus_angle
        )
    
    # Final normalization
    terrain = (terrain - terrain.min()) / (terrain.max() - terrain.min())
    
    return terrain


# Example usage and testing
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    
    # Generate terrain with different parameter settings
    
    # Setting 1: Smooth rolling hills
    terrain_smooth = generate_mountain_terrain(
        width=256, height=256, seed=42,
        octaves=4, persistence=0.4, lacunarity=2.0,
        scale=80, ridge_noise=False,
        hydraulic_iterations=10000, thermal_iterations=10
    )
    
    # Setting 2: Sharp mountain ridges
    terrain_ridged = generate_mountain_terrain(
        width=256, height=256, seed=42,
        octaves=6, persistence=0.55, lacunarity=2.2,
        scale=100, ridge_noise=True,
        hydraulic_iterations=20000, thermal_iterations=15
    )
    
    # Setting 3: Heavily eroded terrain
    terrain_eroded = generate_mountain_terrain(
        width=256, height=256, seed=42,
        octaves=7, persistence=0.6, lacunarity=2.0,
        scale=120, ridge_noise=True,
        hydraulic_iterations=50000, erosion_rate=0.4,
        thermal_iterations=30, talus_angle=0.35
    )
    
    # Visualization
    fig = plt.figure(figsize=(15, 5))
    
    # Plot 1: Smooth terrain
    ax1 = fig.add_subplot(131, projection='3d')
    x = np.linspace(0, 10, 256)
    y = np.linspace(0, 10, 256)
    X, Y = np.meshgrid(x, y)
    ax1.plot_surface(X, Y, terrain_smooth, cmap='terrain', alpha=0.8)
    ax1.set_title('Smooth Rolling Hills')
    ax1.set_zlabel('Height')
    
    # Plot 2: Ridged mountains
    ax2 = fig.add_subplot(132, projection='3d')
    ax2.plot_surface(X, Y, terrain_ridged, cmap='terrain', alpha=0.8)
    ax2.set_title('Sharp Mountain Ridges')
    ax2.set_zlabel('Height')
    
    # Plot 3: Heavily eroded
    ax3 = fig.add_subplot(133, projection='3d')
    ax3.plot_surface(X, Y, terrain_eroded, cmap='terrain', alpha=0.8)
    ax3.set_title('Heavily Eroded Terrain')
    ax3.set_zlabel('Height')
    
    plt.tight_layout()
    plt.show()
    
    # Also create 2D heightmap views
    fig2, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    axes[0].imshow(terrain_smooth, cmap='terrain')
    axes[0].set_title('Smooth Hills - Heightmap')
    axes[0].axis('off')
    
    axes[1].imshow(terrain_ridged, cmap='terrain')
    axes[1].set_title('Ridged Mountains - Heightmap')
    axes[1].axis('off')
    
    axes[2].imshow(terrain_eroded, cmap='terrain')
    axes[2].set_title('Eroded Terrain - Heightmap')
    axes[2].axis('off')
    
    plt.tight_layout()
    plt.show()
    
    print("Terrain generation complete!")
    print(f"Smooth terrain range: [{terrain_smooth.min():.3f}, {terrain_smooth.max():.3f}]")
    print(f"Ridged terrain range: [{terrain_ridged.min():.3f}, {terrain_ridged.max():.3f}]")
    print(f"Eroded terrain range: [{terrain_eroded.min():.3f}, {terrain_eroded.max():.3f}]")
