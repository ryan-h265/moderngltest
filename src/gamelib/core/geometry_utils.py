"""
Custom Geometry Utilities

Provides additional geometry primitives not available in moderngl_window.geometry
"""

import numpy as np
from moderngl_window.opengl.vao import VAO
from moderngl_window.meta import ProgramDescription
from .terrain_generation import generate_donut_height_data


def pyramid(base_size=1.0, height=1.0):
    """
    Create a pyramid geometry (square base with 4 triangular faces).

    Args:
        base_size: Size of the square base
        height: Height of the pyramid from base to apex

    Returns:
        VAO object compatible with moderngl_window rendering
    """
    half_base = base_size / 2.0

    # Vertices: base corners + apex
    # Base is at y=0, apex at y=height
    vertices = np.array([
        # Base vertices (y=0)
        [-half_base, 0.0, -half_base],  # 0: back-left
        [ half_base, 0.0, -half_base],  # 1: back-right
        [ half_base, 0.0,  half_base],  # 2: front-right
        [-half_base, 0.0,  half_base],  # 3: front-left
        # Apex
        [0.0, height, 0.0],             # 4: top
    ], dtype='f4')

    # Calculate normals for each face
    def calc_normal(v0, v1, v2):
        """Calculate face normal from three vertices"""
        edge1 = v1 - v0
        edge2 = v2 - v0
        normal = np.cross(edge1, edge2)
        norm = np.linalg.norm(normal)
        return normal / norm if norm > 0 else normal

    # Build vertex data with positions and normals
    # Each triangle: 3 vertices, each with position (3 floats) + normal (3 floats)
    vertex_data = []

    # Base (bottom, two triangles - CCW from below = CW from above)
    base_normal = np.array([0.0, -1.0, 0.0], dtype='f4')
    for indices in [
        [0, 1, 2],  # Triangle 1
        [0, 2, 3],  # Triangle 2
    ]:
        for idx in indices:
            vertex_data.extend(vertices[idx])
            vertex_data.extend(base_normal)

    # Side faces (counter-clockwise from outside)
    # Looking from outside: vertices should go CCW
    # Front face (+Z): looking from front, goes 3 -> 2 -> 4
    side_faces = [
        ([3, 2, 4], calc_normal(vertices[3], vertices[2], vertices[4])),  # Front
        ([2, 1, 4], calc_normal(vertices[2], vertices[1], vertices[4])),  # Right
        ([1, 0, 4], calc_normal(vertices[1], vertices[0], vertices[4])),  # Back
        ([0, 3, 4], calc_normal(vertices[0], vertices[3], vertices[4])),  # Left
    ]

    for indices, normal in side_faces:
        for idx in indices:
            vertex_data.extend(vertices[idx])
            vertex_data.extend(normal)

    # Convert to numpy array
    vertex_data = np.array(vertex_data, dtype='f4')

    # Create VAO
    vao = VAO(name="pyramid")

    # Configure vertex attributes
    # Position: 3 floats, Normal: 3 floats (interleaved)
    vao.buffer(vertex_data, '3f 3f', ['in_position', 'in_normal'])

    return vao


def cone(radius=1.0, height=1.0, segments=32):
    """
    Create a cone geometry.

    Args:
        radius: Radius of the base circle
        height: Height of the cone
        segments: Number of segments around the base circle

    Returns:
        VAO object compatible with moderngl_window rendering
    """
    vertices = []
    normals = []

    # Apex at (0, height, 0)
    apex = np.array([0.0, height, 0.0], dtype='f4')

    # Generate base circle vertices
    base_vertices = []
    for i in range(segments):
        angle = 2.0 * np.pi * i / segments
        x = radius * np.cos(angle)
        z = radius * np.sin(angle)
        base_vertices.append(np.array([x, 0.0, z], dtype='f4'))

    # Build triangles
    vertex_data = []

    # Side faces
    slant_height = np.sqrt(height * height + radius * radius)
    normal_y = radius / slant_height
    normal_xz_scale = height / slant_height

    for i in range(segments):
        next_i = (i + 1) % segments

        v0 = base_vertices[i]
        v1 = base_vertices[next_i]

        # Calculate normal (pointing outward and up)
        mid_angle = 2.0 * np.pi * (i + 0.5) / segments
        normal = np.array([
            normal_xz_scale * np.cos(mid_angle),
            normal_y,
            normal_xz_scale * np.sin(mid_angle)
        ], dtype='f4')

        # Triangle: base[i], apex, base[i+1]
        vertex_data.extend(v0)
        vertex_data.extend(normal)
        vertex_data.extend(apex)
        vertex_data.extend(normal)
        vertex_data.extend(v1)
        vertex_data.extend(normal)

    # Base (triangle fan from center)
    base_center = np.array([0.0, 0.0, 0.0], dtype='f4')
    base_normal = np.array([0.0, -1.0, 0.0], dtype='f4')

    for i in range(segments):
        next_i = (i + 1) % segments

        # Triangle: center, base[i+1], base[i] (clockwise from below)
        vertex_data.extend(base_center)
        vertex_data.extend(base_normal)
        vertex_data.extend(base_vertices[next_i])
        vertex_data.extend(base_normal)
        vertex_data.extend(base_vertices[i])
        vertex_data.extend(base_normal)

    # Convert to numpy array
    vertex_data = np.array(vertex_data, dtype='f4')

    # Create VAO
    vao = VAO(name="cone")
    vao.buffer(vertex_data, '3f 3f', ['in_position', 'in_normal'])

    return vao


def donut_terrain(resolution=128, outer_radius=200.0, inner_radius=80.0, height=50.0, rim_width=40.0, seed=42):
    """
    Create a donut-shaped terrain mesh with procedurally generated heights.

    Generates a ring-shaped terrain feature with:
    - Flat walkable surface on the top rim
    - Smooth slopes on inner and outer edges
    - Procedural noise for natural variation
    - Proper normals for lighting

    Args:
        resolution: Grid resolution (higher = more detail, default 128)
        outer_radius: Outer radius of the donut in world units (default 200.0)
        inner_radius: Inner radius/hole size in world units (default 80.0)
        height: Maximum height of the rim in world units (default 50.0)
        rim_width: Width parameter for the flat top surface (default 40.0, currently unused in height gen)
        seed: Random seed for procedural noise (default 42)

    Returns:
        VAO object compatible with moderngl_window rendering
    """
    # Generate height data using terrain generation
    heights = generate_donut_height_data(
        resolution=resolution,
        outer_radius=outer_radius,
        inner_radius=inner_radius,
        height=height,
        rim_width=rim_width,
        seed=seed
    )

    # Calculate world size and spacing
    world_size = outer_radius * 2.2
    spacing = world_size / (resolution - 1)
    offset = world_size / 2

    # Generate vertices and calculate normals
    vertices = []
    normals = []
    indices = []

    # Create vertex grid with positions and calculate normals
    for x in range(resolution):
        for z in range(resolution):
            # World position
            world_x = (x * spacing) - offset
            world_z = (z * spacing) - offset
            world_y = heights[x][z]

            vertices.append([world_x, world_y, world_z])

            # Calculate normal using finite differences (central differences when possible)
            # Get neighboring heights for normal calculation
            dx = 0.0
            dz = 0.0

            if x > 0 and x < resolution - 1:
                dx = (heights[x + 1][z] - heights[x - 1][z]) / (2 * spacing)
            elif x > 0:
                dx = (heights[x][z] - heights[x - 1][z]) / spacing
            elif x < resolution - 1:
                dx = (heights[x + 1][z] - heights[x][z]) / spacing

            if z > 0 and z < resolution - 1:
                dz = (heights[x][z + 1] - heights[x][z - 1]) / (2 * spacing)
            elif z > 0:
                dz = (heights[x][z] - heights[x][z - 1]) / spacing
            elif z < resolution - 1:
                dz = (heights[x][z + 1] - heights[x][z]) / spacing

            # Normal is perpendicular to the tangent plane
            # Tangent vectors: (1, dx, 0) and (0, dz, 1)
            # Normal = cross product = (-dx, 1, -dz)
            normal = np.array([-dx, 1.0, -dz], dtype='f4')
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm
            else:
                normal = np.array([0.0, 1.0, 0.0], dtype='f4')

            normals.append(normal)

    # Generate indices for triangles (two triangles per quad)
    # Grid layout: each quad is defined by 4 vertices
    # Triangle winding: counter-clockwise from above
    for x in range(resolution - 1):
        for z in range(resolution - 1):
            # Vertex indices for this quad
            top_left = x * resolution + z
            top_right = (x + 1) * resolution + z
            bottom_left = x * resolution + (z + 1)
            bottom_right = (x + 1) * resolution + (z + 1)

            # First triangle: top-left, bottom-left, top-right
            indices.append(top_left)
            indices.append(bottom_left)
            indices.append(top_right)

            # Second triangle: top-right, bottom-left, bottom-right
            indices.append(top_right)
            indices.append(bottom_left)
            indices.append(bottom_right)

    # Convert to numpy arrays
    vertices = np.array(vertices, dtype='f4')
    normals = np.array(normals, dtype='f4')
    indices = np.array(indices, dtype='i4')

    # Interleave vertex positions and normals
    vertex_data = np.zeros(len(vertices) * 6, dtype='f4')
    vertex_data[0::6] = vertices[:, 0]  # x
    vertex_data[1::6] = vertices[:, 1]  # y
    vertex_data[2::6] = vertices[:, 2]  # z
    vertex_data[3::6] = normals[:, 0]   # nx
    vertex_data[4::6] = normals[:, 1]   # ny
    vertex_data[5::6] = normals[:, 2]   # nz

    # Create VAO with indexed rendering
    vao = VAO(name="donut_terrain")
    vao.buffer(vertex_data, '3f 3f', ['in_position', 'in_normal'])
    vao.index_buffer(indices)

    return vao


def heightmap_terrain(heightmap_path):
    """
    Create a terrain mesh from a pre-generated heightmap file.

    Loads a .npz heightmap (generated by fractal_perlin module) and builds
    a renderable mesh with vertices, normals, and indices.

    Args:
        heightmap_path: Path to .npz heightmap file

    Returns:
        VAO object compatible with moderngl_window rendering
    """
    import numpy as np
    import json
    
    # Load heightmap data
    data = np.load(heightmap_path)
    heights = data['heights']
    meta = json.loads(str(data['meta']))
    
    resolution = meta['resolution']
    world_size = meta['world_size']
    
    # Calculate spacing
    dx = world_size / (resolution - 1)
    dz = world_size / (resolution - 1)
    offset = world_size / 2.0
    
    # Build vertices
    vertices = []
    for i in range(resolution):
        for j in range(resolution):
            x = -offset + i * dx
            z = -offset + j * dz
            y = float(heights[i, j])
            vertices.append([x, y, z])
    
    vertices = np.array(vertices, dtype='f4')
    
    # Calculate normals using finite differences (gradient method)
    # This matches the approach used in donut_terrain for smooth, accurate normals
    normals = []

    def idx(i, j):
        return i * resolution + j

    for i in range(resolution):
        for j in range(resolution):
            # Calculate gradients using finite differences
            di = 0.0
            dj = 0.0

            # Central differences when possible, forward/backward at edges
            if i > 0 and i < resolution - 1:
                di = (heights[i + 1, j] - heights[i - 1, j]) / (2 * dx)
            elif i > 0:
                di = (heights[i, j] - heights[i - 1, j]) / dx
            elif i < resolution - 1:
                di = (heights[i + 1, j] - heights[i, j]) / dx

            if j > 0 and j < resolution - 1:
                dj = (heights[i, j + 1] - heights[i, j - 1]) / (2 * dz)
            elif j > 0:
                dj = (heights[i, j] - heights[i, j - 1]) / dz
            elif j < resolution - 1:
                dj = (heights[i, j + 1] - heights[i, j]) / dz

            # Normal is perpendicular to the tangent plane
            # Tangent vectors: (1, di, 0) in i-direction and (0, dj, 1) in j-direction
            # Normal = cross product = (-di, 1, -dj)
            normal = np.array([-di, 1.0, -dj], dtype='f4')
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm
            else:
                normal = np.array([0.0, 1.0, 0.0], dtype='f4')

            normals.append(normal)

    normals = np.array(normals, dtype='f4')
    
    # Build indices (two triangles per quad)
    # Using counter-clockwise winding when viewed from above
    indices = []
    for i in range(resolution - 1):
        for j in range(resolution - 1):
            v0 = idx(i, j)
            v1 = idx(i + 1, j)
            v2 = idx(i + 1, j + 1)
            v3 = idx(i, j + 1)

            # Triangle 1: v0, v3, v1 (counter-clockwise from above)
            indices.extend([v0, v3, v1])
            # Triangle 2: v1, v3, v2 (counter-clockwise from above)
            indices.extend([v1, v3, v2])
    
    indices = np.array(indices, dtype='i4')
    
    # Interleave vertex positions and normals
    vertex_data = np.zeros(len(vertices) * 6, dtype='f4')
    vertex_data[0::6] = vertices[:, 0]  # x
    vertex_data[1::6] = vertices[:, 1]  # y
    vertex_data[2::6] = vertices[:, 2]  # z
    vertex_data[3::6] = normals[:, 0]   # nx
    vertex_data[4::6] = normals[:, 1]   # ny
    vertex_data[5::6] = normals[:, 2]   # nz
    
    # Create VAO with indexed rendering
    vao = VAO(name=f"heightmap_terrain_{meta.get('preset', 'unknown')}")
    vao.buffer(vertex_data, '3f 3f', ['in_position', 'in_normal'])
    vao.index_buffer(indices)
    
    return vao
