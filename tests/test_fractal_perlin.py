"""Unit tests for fractal_perlin module."""

import unittest
import numpy as np
import tempfile
import os
import json

from src.gamelib.fractal_perlin import (
    perlin, fbm, generate_noise_grid, save_heightmap, export_obj, PRESETS
)


class TestPerlinNoise(unittest.TestCase):
    """Test basic Perlin noise function."""

    def test_perlin_scalar_input(self):
        """Test that perlin accepts scalar inputs."""
        result = perlin(0.5, 1.2, seed=0)
        # Result is a numpy scalar (0-d array)
        self.assertTrue(np.isscalar(result) or result.ndim == 0)

    def test_perlin_array_input(self):
        """Test that perlin accepts array inputs."""
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 1.0, 2.0])
        result = perlin(x, y, seed=0)
        self.assertEqual(result.shape, (3,))

    def test_perlin_value_range(self):
        """Test that perlin output is roughly in expected range."""
        x = np.linspace(-10, 10, 50)
        y = np.linspace(-10, 10, 50)
        xv, yv = np.meshgrid(x, y)
        result = perlin(xv, yv, seed=42)
        # Perlin should be roughly in [-1, 1] but can exceed slightly
        self.assertLessEqual(np.max(np.abs(result)), 2.0)

    def test_perlin_deterministic(self):
        """Test that same seed produces same output."""
        result1 = perlin(3.14, 2.71, seed=123)
        result2 = perlin(3.14, 2.71, seed=123)
        np.testing.assert_array_equal(result1, result2)

    def test_perlin_different_seeds(self):
        """Test that different seeds produce different output."""
        # Use non-integer coordinates to avoid grid points
        result1 = perlin(1.5, 1.7, seed=1)
        result2 = perlin(1.5, 1.7, seed=2)
        self.assertNotAlmostEqual(float(result1), float(result2))


class TestFBM(unittest.TestCase):
    """Test fractal Brownian motion."""

    def test_fbm_scalar_input(self):
        """Test fbm with scalar inputs."""
        result = fbm(1.5, 2.5, octaves=4, seed=0)
        self.assertIsInstance(result, (float, np.ndarray))

    def test_fbm_array_input(self):
        """Test fbm with array inputs."""
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 1.0, 2.0])
        result = fbm(x, y, octaves=3, seed=42)
        self.assertEqual(result.shape, (3,))

    def test_fbm_value_range(self):
        """Test that fbm output is normalized."""
        x = np.linspace(-5, 5, 30)
        y = np.linspace(-5, 5, 30)
        xv, yv = np.meshgrid(x, y)
        result = fbm(xv, yv, octaves=5, persistence=0.5, lacunarity=2.0, seed=7)
        # fbm normalizes to roughly [-1, 1]
        self.assertLessEqual(np.max(np.abs(result)), 1.5)

    def test_fbm_deterministic(self):
        """Test that same seed produces same fbm output."""
        result1 = fbm(2.0, 3.0, octaves=4, persistence=0.6, lacunarity=2.1, seed=99)
        result2 = fbm(2.0, 3.0, octaves=4, persistence=0.6, lacunarity=2.1, seed=99)
        np.testing.assert_allclose(result1, result2, rtol=1e-7)

    def test_fbm_octaves_effect(self):
        """Test that more octaves add detail (different from fewer octaves)."""
        x = np.linspace(0, 10, 20)
        y = np.linspace(0, 10, 20)
        result_low = fbm(x, y, octaves=1, seed=42)
        result_high = fbm(x, y, octaves=6, seed=42)
        # With more octaves, output should differ (more detail added)
        self.assertFalse(np.allclose(result_low, result_high))


class TestGenerateNoiseGrid(unittest.TestCase):
    """Test generate_noise_grid function."""

    def test_grid_shape(self):
        """Test that generate_noise_grid returns correct shape."""
        heights, meta = generate_noise_grid(resolution=50, seed=42)
        self.assertEqual(heights.shape, (50, 50))

    def test_grid_metadata(self):
        """Test that metadata is returned with correct keys."""
        heights, meta = generate_noise_grid(resolution=100, seed=42, preset='mountainous')
        self.assertIn('resolution', meta)
        self.assertIn('seed', meta)
        self.assertIn('preset', meta)
        self.assertEqual(meta['resolution'], 100)
        self.assertEqual(meta['seed'], 42)

    def test_grid_deterministic(self):
        """Test that same parameters produce same grid."""
        heights1, _ = generate_noise_grid(resolution=100, seed=123, preset='rolling')
        heights2, _ = generate_noise_grid(resolution=100, seed=123, preset='rolling')
        np.testing.assert_array_equal(heights1, heights2)

    def test_grid_different_seeds(self):
        """Test that different seeds produce different grids."""
        heights1, _ = generate_noise_grid(resolution=100, seed=1, preset='mountainous')
        heights2, _ = generate_noise_grid(resolution=100, seed=2, preset='mountainous')
        self.assertFalse(np.array_equal(heights1, heights2))

    def test_grid_presets(self):
        """Test that all presets work."""
        for preset_name in PRESETS.keys():
            heights, meta = generate_noise_grid(resolution=50, preset=preset_name, seed=42)
            self.assertEqual(heights.shape, (50, 50))
            self.assertEqual(meta['preset'], preset_name)

    def test_grid_custom_params(self):
        """Test that custom parameters override preset."""
        heights, meta = generate_noise_grid(
            resolution=50, preset='mountainous', seed=42,
            octaves=3, persistence=0.4, lacunarity=3.0, amplitude=200.0
        )
        self.assertEqual(meta['octaves'], 3)
        self.assertEqual(meta['persistence'], 0.4)
        self.assertEqual(meta['lacunarity'], 3.0)
        self.assertEqual(meta['amplitude'], 200.0)

    def test_grid_resolution_100(self):
        """Test default test resolution of 100."""
        heights, meta = generate_noise_grid(resolution=100, seed=42)
        self.assertEqual(heights.shape, (100, 100))
        # Check that values are finite
        self.assertTrue(np.all(np.isfinite(heights)))


class TestSaveAndLoadHeightmap(unittest.TestCase):
    """Test saving and loading heightmap files."""

    def test_save_and_load_npz(self):
        """Test that heightmap can be saved and loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.npz')
            heights, meta = generate_noise_grid(resolution=50, seed=42)
            save_heightmap(path, heights, meta)

            # Load and verify
            loaded = np.load(path)
            loaded_heights = loaded['heights']
            loaded_meta = json.loads(str(loaded['meta']))

            # Allow small float32 precision loss
            np.testing.assert_allclose(heights, loaded_heights, rtol=1e-6, atol=1e-6)
            self.assertEqual(meta['seed'], loaded_meta['seed'])
            self.assertEqual(meta['resolution'], loaded_meta['resolution'])

    def test_save_with_json_fallback(self):
        """Test that JSON metadata file is created when requested."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.npz')
            heights, meta = generate_noise_grid(resolution=50, seed=42)
            save_heightmap(path, heights, meta, json_fallback=True)

            # Check JSON file exists
            json_path = os.path.join(tmpdir, 'test.json')
            self.assertTrue(os.path.exists(json_path))

            # Load and verify JSON
            with open(json_path, 'r') as fh:
                json_data = json.load(fh)
            self.assertIn('metadata', json_data)
            self.assertEqual(json_data['metadata']['seed'], 42)


class TestOBJExport(unittest.TestCase):
    """Test OBJ mesh export."""

    def test_export_obj(self):
        """Test that OBJ file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.obj')
            heights = np.random.randn(10, 10)
            export_obj(path, heights, world_size=100.0)

            # Check file exists and has content
            self.assertTrue(os.path.exists(path))
            with open(path, 'r') as fh:
                content = fh.read()
            self.assertIn('v ', content)  # Vertices
            self.assertIn('f ', content)  # Faces

    def test_obj_vertex_count(self):
        """Test that OBJ has correct number of vertices."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.obj')
            res = 5
            heights = np.zeros((res, res))
            export_obj(path, heights, world_size=100.0)

            with open(path, 'r') as fh:
                lines = fh.readlines()
            vertex_lines = [l for l in lines if l.startswith('v ')]
            self.assertEqual(len(vertex_lines), res * res)

    def test_obj_face_count(self):
        """Test that OBJ has correct number of faces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test.obj')
            res = 5
            heights = np.zeros((res, res))
            export_obj(path, heights, world_size=100.0)

            with open(path, 'r') as fh:
                lines = fh.readlines()
            face_lines = [l for l in lines if l.startswith('f ')]
            # Each grid cell = 2 triangles
            expected_faces = 2 * (res - 1) * (res - 1)
            self.assertEqual(len(face_lines), expected_faces)


if __name__ == '__main__':
    unittest.main()
