"""
Custom Geometry Utilities

Provides additional geometry primitives not available in moderngl_window.geometry
"""

import numpy as np
from moderngl_window.opengl.vao import VAO
from moderngl_window.meta import ProgramDescription


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
