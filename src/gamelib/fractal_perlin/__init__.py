"""Fractal Perlin noise utilities.

Provides a pure-Python implementation of 2D Perlin noise and fractal Brownian
motion (fBm), plus helpers to generate heightmaps and export them. Designed
to be deterministic given a seed and usable for baking heightmaps at multiple
resolutions by sampling the same continuous noise field.

API:
 - perlin(x, y, seed=0): scalar or numpy-array inputs -> noise in [-1,1]
 - fbm(x, y, octaves=4, persistence=0.5, lacunarity=2.0, seed=0)
 - generate_noise_grid(resolution, scale, world_size, preset, seed, amplitude)
 - save_heightmap(path, heights, metadata, json_fallback=False)

All functions are pure Python and use numpy for array work.
"""

from __future__ import annotations

import numpy as np
import math
import json
import os
from typing import Tuple, Dict, Any


def _make_perm(seed: int) -> np.ndarray:
    rng = np.random.RandomState(seed)
    p = np.arange(256, dtype=int)
    rng.shuffle(p)
    # Repeat to avoid overflow in indexing
    return np.concatenate([p, p])


def _fade(t: np.ndarray) -> np.ndarray:
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
    return a + t * (b - a)


def _grad(hash_vals: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    # Use 8 gradient directions
    h = hash_vals & 7
    vectors = np.array([[1,1],[-1,1],[1,-1],[-1,-1],[1,0],[-1,0],[0,1],[0,-1]], dtype=float)
    g = vectors[h]
    return g[..., 0] * x + g[..., 1] * y


def perlin(x: np.ndarray | float, y: np.ndarray | float, seed: int = 0) -> np.ndarray:
    """2D Perlin noise. Accepts scalar or numpy arrays for x and y.

    Returns values approximately in [-1,1].
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)

    # Ensure broadcasting
    x_b, y_b = np.broadcast_arrays(x_arr, y_arr)

    perm = _make_perm(seed)

    xi = np.floor(x_b).astype(int) & 255
    yi = np.floor(y_b).astype(int) & 255

    xf = x_b - np.floor(x_b)
    yf = y_b - np.floor(y_b)

    u = _fade(xf)
    v = _fade(yf)

    aa = perm[perm[xi] + yi]
    ab = perm[perm[xi] + yi + 1]
    ba = perm[perm[xi + 1] + yi]
    bb = perm[perm[xi + 1] + yi + 1]

    x1 = _grad(aa, xf, yf)
    x2 = _grad(ba, xf - 1, yf)
    y1 = _lerp(x1, x2, u)

    x3 = _grad(ab, xf, yf - 1)
    x4 = _grad(bb, xf - 1, yf - 1)
    y2 = _lerp(x3, x4, u)

    out = _lerp(y1, y2, v)

    # Normalize roughly to [-1,1]
    out = out * 0.7071
    return out


def fbm(x: np.ndarray | float, y: np.ndarray | float, octaves: int = 4, persistence: float = 0.5,
        lacunarity: float = 2.0, seed: int = 0) -> np.ndarray:
    """Fractal Brownian Motion using Perlin noise."""
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0

    for i in range(octaves):
        value += perlin(np.array(x) * frequency, np.array(y) * frequency, seed + i) * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    return value / max_value


PRESETS: Dict[str, Dict[str, Any]] = {
    'mountainous': dict(scale=0.006, octaves=6, persistence=0.55, lacunarity=2.1, amplitude=120.0),
    'rolling': dict(scale=0.02, octaves=4, persistence=0.5, lacunarity=2.0, amplitude=30.0),
    'plateau': dict(scale=0.01, octaves=5, persistence=0.6, lacunarity=2.0, amplitude=60.0),
}


def generate_noise_grid(resolution: int = 100, *, scale: float = 0.01, world_size: float = 400.0,
                        preset: str | None = 'mountainous', seed: int = 42,
                        octaves: int | None = None, persistence: float | None = None,
                        lacunarity: float | None = None, amplitude: float | None = None) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Generate a height grid (resolution x resolution) and return heights and metadata.

    The noise field is sampled across [-world_size/2, world_size/2] in X and Z.
    """
    if preset and preset in PRESETS:
        p = PRESETS[preset]
        if scale is None or scale == 0.01:  # Use preset if default value
            scale = p['scale']
        if octaves is None:
            octaves = p['octaves']
        if persistence is None:
            persistence = p['persistence']
        if lacunarity is None:
            lacunarity = p['lacunarity']
        if amplitude is None:
            amplitude = p['amplitude']

    # Fallback defaults
    scale = float(scale or 0.01)
    octaves = int(octaves or 4)
    persistence = float(persistence or 0.5)
    lacunarity = float(lacunarity or 2.0)
    amplitude = float(amplitude or 50.0)

    # Create sample grid in world coordinates
    xs = np.linspace(-world_size / 2.0, world_size / 2.0, resolution)
    zs = np.linspace(-world_size / 2.0, world_size / 2.0, resolution)
    xv, zv = np.meshgrid(xs, zs, indexing='ij')

    # Sample continuous noise field at scaled coordinates
    sample_x = xv * scale
    sample_z = zv * scale

    heights = fbm(sample_x, sample_z, octaves=octaves, persistence=persistence, lacunarity=lacunarity, seed=seed)

    # Normalize fbm to [-1,1], then scale by amplitude
    # fbm output is roughly in [-1,1] but can be smaller; we clip for safety
    heights = np.clip(heights, -1.0, 1.0) * amplitude

    metadata = dict(
        resolution=resolution,
        scale=scale,
        world_size=world_size,
        preset=preset,
        seed=int(seed),
        octaves=int(octaves),
        persistence=float(persistence),
        lacunarity=float(lacunarity),
        amplitude=float(amplitude),
    )

    return heights, metadata


def save_heightmap(path: str, heights: np.ndarray, metadata: Dict[str, Any], json_fallback: bool = False) -> None:
    """Save heights and metadata to .npz file. If json_fallback True also write a JSON with base64 (not used by default).

    The .npz will contain 'heights' (float32) and 'meta' (json string).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez_compressed(path, heights=heights.astype('f4'), meta=json.dumps(metadata))

    if json_fallback:
        # Export a lightweight JSON referencing file and metadata
        meta_path = os.path.splitext(path)[0] + '.json'
        payload = dict(metadata=metadata, path=os.path.basename(path))
        with open(meta_path, 'w') as fh:
            json.dump(payload, fh, indent=2)


def export_obj(path: str, heights: np.ndarray, world_size: float) -> None:
    """Export a simple OBJ mesh for the heightmap. Vertices are laid out on X,Z plane.

    Faces are two triangles per grid cell. Normals and UVs are not included (simple mesh).
    """
    res_x, res_z = heights.shape
    dx = world_size / (res_x - 1)
    dz = world_size / (res_z - 1)

    with open(path, 'w') as fh:
        # vertices
        for i in range(res_x):
            for j in range(res_z):
                x = -world_size / 2.0 + i * dx
                z = -world_size / 2.0 + j * dz
                y = float(heights[i, j])
                fh.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")

        # faces (1-based indexing)
        def idx(i, j):
            return i * res_z + j + 1

        for i in range(res_x - 1):
            for j in range(res_z - 1):
                v0 = idx(i, j)
                v1 = idx(i + 1, j)
                v2 = idx(i + 1, j + 1)
                v3 = idx(i, j + 1)
                # two triangles v0,v1,v2 and v0,v2,v3
                fh.write(f"f {v0} {v1} {v2}\n")
                fh.write(f"f {v0} {v2} {v3}\n")
