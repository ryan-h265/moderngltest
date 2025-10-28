"""Example of loading and using fractal terrain heightmaps.

Demonstrates how to:
1. Load a heightmap from .npz file
2. Build a mesh from the heightmap
3. Use the terrain in a scene

This is a standalone example showing the integration pattern.
For actual game integration, adapt this code to your scene loader.
"""

import numpy as np
import json
import os
from pathlib import Path


def load_heightmap(npz_path):
    """Load heightmap and metadata from .npz file.
    
    Args:
        npz_path: Path to the .npz heightmap file
        
    Returns:
        Tuple of (heights array, metadata dict)
    """
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"Heightmap not found: {npz_path}")
    
    data = np.load(npz_path)
    heights = data['heights']
    meta = json.loads(str(data['meta']))
    
    print(f"Loaded heightmap: {npz_path}")
    print(f"  Resolution: {meta['resolution']}x{meta['resolution']}")
    print(f"  World size: {meta['world_size']}")
    print(f"  Preset: {meta['preset']}")
    print(f"  Seed: {meta['seed']}")
    print(f"  Height range: [{heights.min():.2f}, {heights.max():.2f}]")
    
    return heights, meta


def build_terrain_mesh_data(heights, world_size):
    """Build vertex and index arrays for rendering a heightmap terrain.
    
    Args:
        heights: 2D numpy array of height values (resolution x resolution)
        world_size: World size in units
        
    Returns:
        Tuple of (vertices, normals, indices) as numpy arrays
    """
    res_x, res_z = heights.shape
    dx = world_size / (res_x - 1)
    dz = world_size / (res_z - 1)
    
    # Build vertices (x, y, z)
    vertices = []
    for i in range(res_x):
        for j in range(res_z):
            x = -world_size / 2.0 + i * dx
            z = -world_size / 2.0 + j * dz
            y = float(heights[i, j])
            vertices.append([x, y, z])
    
    vertices = np.array(vertices, dtype='f4')
    
    # Calculate normals (using cross product of adjacent triangles)
    normals = np.zeros((res_x * res_z, 3), dtype='f4')
    
    def idx(i, j):
        return i * res_z + j
    
    for i in range(res_x - 1):
        for j in range(res_z - 1):
            # Get vertices of the quad
            v0 = vertices[idx(i, j)]
            v1 = vertices[idx(i + 1, j)]
            v2 = vertices[idx(i + 1, j + 1)]
            v3 = vertices[idx(i, j + 1)]
            
            # Calculate normals for both triangles
            n1 = np.cross(v1 - v0, v2 - v0)
            n2 = np.cross(v2 - v0, v3 - v0)
            
            # Normalize
            n1_norm = n1 / (np.linalg.norm(n1) + 1e-8)
            n2_norm = n2 / (np.linalg.norm(n2) + 1e-8)
            
            # Accumulate normals at vertices
            normals[idx(i, j)] += n1_norm + n2_norm
            normals[idx(i + 1, j)] += n1_norm
            normals[idx(i + 1, j + 1)] += n1_norm + n2_norm
            normals[idx(i, j + 1)] += n2_norm
    
    # Normalize accumulated normals
    for i in range(len(normals)):
        norm = np.linalg.norm(normals[i])
        if norm > 0:
            normals[i] /= norm
        else:
            normals[i] = [0, 1, 0]  # Default up
    
    # Build indices (two triangles per quad)
    indices = []
    for i in range(res_x - 1):
        for j in range(res_z - 1):
            v0 = idx(i, j)
            v1 = idx(i + 1, j)
            v2 = idx(i + 1, j + 1)
            v3 = idx(i, j + 1)
            
            # Triangle 1: v0, v1, v2
            indices.extend([v0, v1, v2])
            # Triangle 2: v0, v2, v3
            indices.extend([v0, v2, v3])
    
    indices = np.array(indices, dtype='i4')
    
    print(f"Built mesh:")
    print(f"  Vertices: {len(vertices)}")
    print(f"  Triangles: {len(indices) // 3}")
    
    return vertices, normals, indices


def load_scene_json(scene_path):
    """Load a fractal terrain scene JSON.
    
    Args:
        scene_path: Path to scene JSON file
        
    Returns:
        Scene dictionary
    """
    with open(scene_path, 'r') as fh:
        scene = json.load(fh)
    
    print(f"Loaded scene: {scene_path}")
    print(f"  Type: {scene['type']}")
    print(f"  Heightmap: {scene['heightmap']}")
    
    return scene


def example_usage():
    """Example of loading and processing a fractal terrain."""
    
    # Path to scene JSON (relative to project root)
    scene_path = 'assets/scenes/fractal_terrain_scene.json'
    
    if not os.path.exists(scene_path):
        print(f"Scene file not found: {scene_path}")
        print("Generate one first with:")
        print("  PYTHONPATH=. python3 examples/generate_fractal_scene.py --preset mountainous --res 100")
        return
    
    # Load scene
    scene = load_scene_json(scene_path)
    
    # Resolve heightmap path (relative to scene JSON location)
    scene_dir = Path(scene_path).parent
    heightmap_path = scene_dir / scene['heightmap']
    
    # Load heightmap
    heights, meta = load_heightmap(str(heightmap_path))
    
    # Build mesh data
    vertices, normals, indices = build_terrain_mesh_data(heights, meta['world_size'])
    
    print("\nMesh data ready for rendering!")
    print("Next steps:")
    print("  1. Create ModernGL buffers from vertices, normals, indices")
    print("  2. Create a VAO with appropriate attributes")
    print("  3. Render with your terrain shader")
    print("\nExample ModernGL setup:")
    print("  vbo_vertices = ctx.buffer(vertices.tobytes())")
    print("  vbo_normals = ctx.buffer(normals.tobytes())")
    print("  ibo = ctx.buffer(indices.tobytes())")
    print("  vao = ctx.vertex_array(program, [")
    print("      (vbo_vertices, '3f', 'in_position'),")
    print("      (vbo_normals, '3f', 'in_normal'),")
    print("  ], index_buffer=ibo)")
    print("  vao.render()")
    
    return vertices, normals, indices, meta


if __name__ == '__main__':
    example_usage()
