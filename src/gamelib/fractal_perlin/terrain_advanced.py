"""
Advanced Terrain Generation Utilities
Provides preset configurations and additional features for terrain generation.
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
from fractal_terrain import FractalTerrain, TerrainErosion, PerlinNoise


class TerrainPresets:
    """Preset parameter configurations for different terrain types."""
    
    @staticmethod
    def get_preset(preset_name: str) -> Dict[str, Any]:
        """
        Get preset parameters for terrain generation.
        
        Available presets:
        - 'rolling_hills': Gentle, smooth terrain
        - 'mountain_range': Classic mountain peaks
        - 'alpine_peaks': Sharp, jagged mountain peaks
        - 'canyon_lands': Heavily eroded terrain with valleys
        - 'volcanic': Volcanic terrain with sharp peaks and flows
        - 'highlands': Scottish highlands style terrain
        - 'dunes': Sand dune-like formations
        - 'plateau': Flat-topped mesas and plateaus
        """
        
        presets = {
            'rolling_hills': {
                'octaves': 4,
                'persistence': 0.35,
                'lacunarity': 2.0,
                'scale': 80,
                'ridge_noise': False,
                'apply_warping': True,
                'warp_strength': 0.08,
                'hydraulic_iterations': 5000,
                'erosion_rate': 0.25,
                'thermal_iterations': 10,
                'talus_angle': 0.5
            },
            'mountain_range': {
                'octaves': 6,
                'persistence': 0.5,
                'lacunarity': 2.0,
                'scale': 100,
                'ridge_noise': False,
                'apply_warping': True,
                'warp_strength': 0.12,
                'hydraulic_iterations': 20000,
                'erosion_rate': 0.3,
                'thermal_iterations': 20,
                'talus_angle': 0.45
            },
            'alpine_peaks': {
                'octaves': 7,
                'persistence': 0.6,
                'lacunarity': 2.2,
                'scale': 120,
                'ridge_noise': True,
                'apply_warping': True,
                'warp_strength': 0.15,
                'hydraulic_iterations': 15000,
                'erosion_rate': 0.35,
                'thermal_iterations': 25,
                'talus_angle': 0.4
            },
            'canyon_lands': {
                'octaves': 5,
                'persistence': 0.45,
                'lacunarity': 2.1,
                'scale': 90,
                'ridge_noise': False,
                'apply_warping': True,
                'warp_strength': 0.2,
                'hydraulic_iterations': 60000,
                'erosion_rate': 0.45,
                'thermal_iterations': 15,
                'talus_angle': 0.35
            },
            'volcanic': {
                'octaves': 8,
                'persistence': 0.65,
                'lacunarity': 2.3,
                'scale': 150,
                'ridge_noise': True,
                'apply_warping': False,
                'warp_strength': 0.0,
                'hydraulic_iterations': 8000,
                'erosion_rate': 0.2,
                'thermal_iterations': 30,
                'talus_angle': 0.3
            },
            'highlands': {
                'octaves': 5,
                'persistence': 0.42,
                'lacunarity': 2.05,
                'scale': 70,
                'ridge_noise': False,
                'apply_warping': True,
                'warp_strength': 0.18,
                'hydraulic_iterations': 35000,
                'erosion_rate': 0.38,
                'thermal_iterations': 18,
                'talus_angle': 0.42
            },
            'dunes': {
                'octaves': 3,
                'persistence': 0.3,
                'lacunarity': 1.8,
                'scale': 60,
                'ridge_noise': False,
                'apply_warping': True,
                'warp_strength': 0.25,
                'hydraulic_iterations': 0,  # No water erosion for dunes
                'erosion_rate': 0.0,
                'thermal_iterations': 40,  # High thermal erosion
                'talus_angle': 0.6
            },
            'plateau': {
                'octaves': 4,
                'persistence': 0.25,
                'lacunarity': 1.9,
                'scale': 100,
                'ridge_noise': False,
                'apply_warping': True,
                'warp_strength': 0.05,
                'hydraulic_iterations': 25000,
                'erosion_rate': 0.5,
                'thermal_iterations': 12,
                'talus_angle': 0.3
            }
        }
        
        if preset_name not in presets:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(presets.keys())}")
        
        return presets[preset_name]


class AdvancedTerrain:
    """Advanced terrain generation with additional features."""
    
    def __init__(self, width: int = 512, height: int = 512, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        self.terrain = None
        
    def generate_with_preset(self, preset_name: str) -> np.ndarray:
        """Generate terrain using a preset configuration."""
        from fractal_terrain import generate_mountain_terrain
        
        params = TerrainPresets.get_preset(preset_name)
        self.terrain = generate_mountain_terrain(
            width=self.width,
            height=self.height,
            seed=self.seed,
            **params
        )
        return self.terrain
    
    def add_terraces(self, 
                     num_levels: int = 8,
                     terrace_strength: float = 0.5) -> np.ndarray:
        """
        Add terracing effect to terrain (creates stepped/layered appearance).
        
        Args:
            num_levels: Number of terrace levels
            terrace_strength: How pronounced the terraces are (0.0-1.0)
        """
        if self.terrain is None:
            raise ValueError("Generate terrain first")
        
        # Create terraced version
        terraced = np.round(self.terrain * num_levels) / num_levels
        
        # Blend with original
        self.terrain = self.terrain * (1 - terrace_strength) + terraced * terrace_strength
        return self.terrain
    
    def add_rivers(self,
                   num_rivers: int = 3,
                   river_depth: float = 0.1,
                   river_width: float = 3.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Carve river valleys into the terrain.
        
        Args:
            num_rivers: Number of rivers to generate
            river_depth: How deep to carve the rivers
            river_width: Width of river valleys
            
        Returns:
            Tuple of (modified terrain, river mask)
        """
        if self.terrain is None:
            raise ValueError("Generate terrain first")
        
        river_mask = np.zeros_like(self.terrain, dtype=bool)
        
        for _ in range(num_rivers):
            # Start from a high point
            high_points = np.where(self.terrain > np.percentile(self.terrain, 80))
            if len(high_points[0]) == 0:
                continue
                
            idx = np.random.randint(0, len(high_points[0]))
            y, x = high_points[0][idx], high_points[1][idx]
            
            # Flow downhill
            path = [(y, x)]
            visited = set([(y, x)])
            
            while True:
                # Find lowest neighbor
                neighbors = []
                for dy, dx in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,1), (-1,1), (1,-1)]:
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < self.height and 0 <= nx < self.width and 
                        (ny, nx) not in visited):
                        neighbors.append((self.terrain[ny, nx], ny, nx))
                
                if not neighbors:
                    break
                    
                # Move to lowest neighbor
                neighbors.sort()
                _, y, x = neighbors[0]
                path.append((y, x))
                visited.add((y, x))
                
                # Stop if we reach a low point
                if self.terrain[y, x] < np.percentile(self.terrain, 20):
                    break
            
            # Carve the river valley
            for y, x in path:
                # Create a wider valley around the river path
                for dy in range(int(-river_width), int(river_width)+1):
                    for dx in range(int(-river_width), int(river_width)+1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < self.height and 0 <= nx < self.width:
                            dist = np.sqrt(dy**2 + dx**2)
                            if dist <= river_width:
                                depth_factor = 1.0 - (dist / river_width)
                                self.terrain[ny, nx] -= river_depth * depth_factor
                                if dist <= 1:
                                    river_mask[ny, nx] = True
        
        # Ensure terrain stays in valid range
        self.terrain = np.clip(self.terrain, 0, 1)
        return self.terrain, river_mask
    
    def apply_smoothing(self, kernel_size: int = 3, iterations: int = 1) -> np.ndarray:
        """
        Apply Gaussian smoothing to terrain.
        
        Args:
            kernel_size: Size of smoothing kernel (odd number)
            iterations: Number of smoothing passes
        """
        if self.terrain is None:
            raise ValueError("Generate terrain first")
        
        from scipy.ndimage import gaussian_filter
        
        for _ in range(iterations):
            self.terrain = gaussian_filter(self.terrain, sigma=kernel_size/3)
        
        return self.terrain
    
    def get_slope_map(self) -> np.ndarray:
        """Calculate slope magnitude at each point."""
        if self.terrain is None:
            raise ValueError("Generate terrain first")
        
        # Calculate gradients
        gy, gx = np.gradient(self.terrain)
        
        # Calculate slope magnitude
        slope = np.sqrt(gx**2 + gy**2)
        return slope
    
    def classify_terrain_types(self,
                               height_threshold: float = 0.6,
                               slope_threshold: float = 0.3) -> Dict[str, np.ndarray]:
        """
        Classify terrain into different types based on height and slope.
        
        Returns dict with boolean masks for:
        - 'peaks': High altitude, any slope
        - 'cliffs': Steep slopes
        - 'valleys': Low altitude, low slope
        - 'slopes': Medium altitude, medium slope
        - 'plateaus': High altitude, low slope
        """
        if self.terrain is None:
            raise ValueError("Generate terrain first")
        
        slope = self.get_slope_map()
        
        classifications = {
            'peaks': (self.terrain > height_threshold) & (slope > slope_threshold),
            'cliffs': slope > slope_threshold * 1.5,
            'valleys': (self.terrain < (1 - height_threshold)) & (slope < slope_threshold),
            'slopes': (slope >= slope_threshold) & (slope <= slope_threshold * 1.5),
            'plateaus': (self.terrain > height_threshold) & (slope < slope_threshold * 0.5)
        }
        
        return classifications


class TerrainSampler:
    """Utilities for sampling and analyzing terrain."""
    
    @staticmethod
    def get_height_at_point(terrain: np.ndarray, x: float, y: float) -> float:
        """
        Get interpolated height at a specific point.
        
        Args:
            terrain: The terrain heightmap
            x, y: Coordinates (can be fractional)
            
        Returns:
            Interpolated height value
        """
        height, width = terrain.shape
        
        # Clamp coordinates
        x = np.clip(x, 0, width - 1.001)
        y = np.clip(y, 0, height - 1.001)
        
        # Get integer parts
        x0, y0 = int(x), int(y)
        x1, y1 = min(x0 + 1, width - 1), min(y0 + 1, height - 1)
        
        # Get fractional parts
        fx, fy = x - x0, y - y0
        
        # Bilinear interpolation
        h00 = terrain[y0, x0]
        h10 = terrain[y0, x1]
        h01 = terrain[y1, x0]
        h11 = terrain[y1, x1]
        
        h0 = h00 * (1 - fx) + h10 * fx
        h1 = h01 * (1 - fx) + h11 * fx
        
        return h0 * (1 - fy) + h1 * fy
    
    @staticmethod
    def get_normal_at_point(terrain: np.ndarray, x: float, y: float, 
                            scale: float = 1.0) -> np.ndarray:
        """
        Calculate surface normal at a point.
        
        Args:
            terrain: The terrain heightmap
            x, y: Coordinates
            scale: Terrain scale factor
            
        Returns:
            3D normal vector [nx, ny, nz]
        """
        height, width = terrain.shape
        
        # Sample heights around the point
        h_left = TerrainSampler.get_height_at_point(terrain, max(x - 1, 0), y)
        h_right = TerrainSampler.get_height_at_point(terrain, min(x + 1, width - 1), y)
        h_down = TerrainSampler.get_height_at_point(terrain, x, max(y - 1, 0))
        h_up = TerrainSampler.get_height_at_point(terrain, x, min(y + 1, height - 1))
        
        # Calculate gradients
        dx = (h_right - h_left) / 2.0 * scale
        dy = (h_up - h_down) / 2.0 * scale
        
        # Calculate normal (cross product of tangent vectors)
        normal = np.array([-dx, -dy, 1.0])
        normal = normal / np.linalg.norm(normal)
        
        return normal


# Example usage demonstrating all features
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    # Generate terrain with different presets
    terrain_gen = AdvancedTerrain(width=256, height=256, seed=42)
    
    # Test different presets
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    
    presets = ['rolling_hills', 'mountain_range', 'alpine_peaks', 'canyon_lands',
               'volcanic', 'highlands', 'dunes', 'plateau']
    
    for idx, preset in enumerate(presets):
        row = idx // 4
        col = idx % 4
        
        # Generate terrain with preset
        terrain_gen = AdvancedTerrain(width=256, height=256, seed=42 + idx)
        terrain = terrain_gen.generate_with_preset(preset)
        
        # Display
        im = axes[row, col].imshow(terrain, cmap='terrain', vmin=0, vmax=1)
        axes[row, col].set_title(preset.replace('_', ' ').title())
        axes[row, col].axis('off')
    
    plt.suptitle('Terrain Generation Presets', fontsize=16)
    plt.tight_layout()
    plt.show()
    
    # Demonstrate advanced features
    print("\nDemonstrating advanced features...")
    
    # Generate base terrain
    adv_terrain = AdvancedTerrain(width=512, height=512, seed=123)
    terrain = adv_terrain.generate_with_preset('mountain_range')
    
    # Add terraces
    terraced = adv_terrain.add_terraces(num_levels=10, terrace_strength=0.3)
    
    # Add rivers
    terrain_with_rivers, river_mask = adv_terrain.add_rivers(num_rivers=5)
    
    # Get terrain classifications
    classifications = adv_terrain.classify_terrain_types()
    
    # Create visualization
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    axes[0, 0].imshow(terrain, cmap='terrain')
    axes[0, 0].set_title('Original Terrain')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(terraced, cmap='terrain')
    axes[0, 1].set_title('With Terracing')
    axes[0, 1].axis('off')
    
    axes[0, 2].imshow(terrain_with_rivers, cmap='terrain')
    axes[0, 2].set_title('With Rivers')
    axes[0, 2].axis('off')
    
    # Show classifications
    axes[1, 0].imshow(classifications['peaks'], cmap='RdYlBu')
    axes[1, 0].set_title('Peak Regions')
    axes[1, 0].axis('off')
    
    axes[1, 1].imshow(classifications['cliffs'], cmap='Reds')
    axes[1, 1].set_title('Cliff Regions')
    axes[1, 1].axis('off')
    
    axes[1, 2].imshow(classifications['valleys'], cmap='Blues')
    axes[1, 2].set_title('Valley Regions')
    axes[1, 2].axis('off')
    
    plt.suptitle('Advanced Terrain Features', fontsize=16)
    plt.tight_layout()
    plt.show()
    
    print("Advanced terrain generation complete!")
