"""Test terrain_generation integration with fractal_perlin."""

import unittest
import numpy as np
from src.gamelib.core.terrain_generation import (
    fractal_noise, 
    generate_donut_height_data,
    generate_fractal_terrain,
    HAS_PERLIN
)


class TestTerrainGenerationIntegration(unittest.TestCase):
    """Test integration of fractal_perlin with terrain_generation."""

    def test_fractal_noise_backward_compatibility(self):
        """Test that fractal_noise still works without use_perlin flag."""
        # Should use original sine-based noise by default
        result = fractal_noise(1.5, 2.3, octaves=3, seed=42)
        self.assertIsInstance(result, float)
        self.assertLessEqual(abs(result), 2.0)

    def test_fractal_noise_deterministic(self):
        """Test that fractal_noise is deterministic."""
        result1 = fractal_noise(3.14, 2.71, seed=123)
        result2 = fractal_noise(3.14, 2.71, seed=123)
        self.assertAlmostEqual(result1, result2)

    @unittest.skipIf(not HAS_PERLIN, "fractal_perlin not available")
    def test_fractal_noise_with_perlin(self):
        """Test that fractal_noise can use Perlin when requested."""
        result_sine = fractal_noise(1.5, 2.3, octaves=3, seed=42, use_perlin=False)
        result_perlin = fractal_noise(1.5, 2.3, octaves=3, seed=42, use_perlin=True)
        
        # Both should return valid values
        self.assertIsInstance(result_sine, float)
        self.assertIsInstance(result_perlin, float)
        
        # They should differ (different noise algorithms)
        self.assertNotAlmostEqual(result_sine, result_perlin, places=2)

    def test_generate_donut_backward_compatibility(self):
        """Test that generate_donut_height_data works without use_perlin."""
        heights = generate_donut_height_data(
            resolution=50,
            outer_radius=100,
            inner_radius=40,
            height=25,
            seed=42
        )
        
        self.assertEqual(heights.shape, (50, 50))
        self.assertTrue(np.all(np.isfinite(heights)))
        self.assertGreaterEqual(heights.min(), 0)

    @unittest.skipIf(not HAS_PERLIN, "fractal_perlin not available")
    def test_generate_donut_with_perlin(self):
        """Test that generate_donut_height_data can use Perlin noise."""
        heights = generate_donut_height_data(
            resolution=50,
            outer_radius=100,
            inner_radius=40,
            height=25,
            seed=42,
            use_perlin=True
        )
        
        self.assertEqual(heights.shape, (50, 50))
        self.assertTrue(np.all(np.isfinite(heights)))
        self.assertGreaterEqual(heights.min(), 0)

    @unittest.skipIf(not HAS_PERLIN, "fractal_perlin not available")
    def test_generate_fractal_terrain(self):
        """Test the new generate_fractal_terrain function."""
        heights = generate_fractal_terrain(
            resolution=50,
            world_size=200.0,
            preset='mountainous',
            seed=42
        )
        
        self.assertEqual(heights.shape, (50, 50))
        self.assertTrue(np.all(np.isfinite(heights)))

    @unittest.skipIf(not HAS_PERLIN, "fractal_perlin not available")
    def test_generate_fractal_terrain_deterministic(self):
        """Test that generate_fractal_terrain is deterministic."""
        heights1 = generate_fractal_terrain(resolution=50, seed=123, preset='rolling')
        heights2 = generate_fractal_terrain(resolution=50, seed=123, preset='rolling')
        
        np.testing.assert_array_equal(heights1, heights2)

    @unittest.skipIf(not HAS_PERLIN, "fractal_perlin not available")
    def test_generate_fractal_terrain_presets(self):
        """Test that all presets work."""
        for preset in ['mountainous', 'rolling', 'plateau']:
            heights = generate_fractal_terrain(
                resolution=30,
                preset=preset,
                seed=42
            )
            self.assertEqual(heights.shape, (30, 30))
            self.assertTrue(np.all(np.isfinite(heights)))


if __name__ == '__main__':
    unittest.main()
