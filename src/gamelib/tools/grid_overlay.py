"""
Grid Overlay

Renders a visual grid on surfaces for snapping feedback.
"""

from typing import Optional, TYPE_CHECKING
from pyrr import Vector3, Matrix44
import moderngl
import numpy as np

if TYPE_CHECKING:
    pass


class GridOverlay:
    """
    Renders a visual grid overlay for level editing.

    Features:
    - Projects grid onto ground plane (Y=0)
    - Configurable grid size
    - Toggle visibility
    - Fades at distance
    """

    def __init__(self, ctx: moderngl.Context, grid_size: float = 1.0, grid_extent: int = 500):
        """
        Initialize grid overlay.

        Args:
            ctx: ModernGL context
            grid_size: Size of each grid cell
            grid_extent: Number of grid lines in each direction from center (default 500 for near-infinite coverage)
        """
        self.ctx = ctx
        self.grid_size = grid_size
        self.grid_extent = grid_extent
        self.visible = True

        # Generate grid geometry
        self._generate_grid_geometry()

        # Create shader program (simple line shader with distance fade)
        self._create_shader_program()

    def _generate_grid_geometry(self):
        """Generate grid line vertices with much larger extent."""
        vertices = []

        # Calculate grid bounds - much larger extent for visible grid
        half_extent = self.grid_extent * self.grid_size

        # Vertical lines (along Z axis)
        for i in range(-self.grid_extent, self.grid_extent + 1):
            x = i * self.grid_size
            # Line from (x, 0, -half_extent) to (x, 0, +half_extent)
            vertices.extend([x, 0.0, -half_extent])
            vertices.extend([x, 0.0, half_extent])

        # Horizontal lines (along X axis)
        for i in range(-self.grid_extent, self.grid_extent + 1):
            z = i * self.grid_size
            # Line from (-half_extent, 0, z) to (+half_extent, 0, z)
            vertices.extend([-half_extent, 0.0, z])
            vertices.extend([half_extent, 0.0, z])

        # Convert to numpy array
        vertices_np = np.array(vertices, dtype='f4')

        # Create VBO
        self.vbo = self.ctx.buffer(vertices_np.tobytes())

        # Number of lines
        self.num_vertices = len(vertices) // 3

    def _create_shader_program(self):
        """Create simple shader for grid lines."""
        vertex_shader = """
        #version 410

        in vec3 in_position;

        uniform mat4 mvp;

        void main() {
            gl_Position = mvp * vec4(in_position, 1.0);
        }
        """

        fragment_shader = """
        #version 410

        out vec4 fragColor;

        uniform vec4 grid_color;

        void main() {
            fragColor = grid_color;
        }
        """

        self.program = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )

        # Create VAO
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f', 'in_position')]
        )

    def render(self, view_matrix: Matrix44, projection_matrix: Matrix44, camera_pos: Vector3 | None = None):
        """
        Render the grid overlay.

        Args:
            view_matrix: Camera view matrix
            projection_matrix: Camera projection matrix
            camera_pos: Camera position (optional, not used in simple shader)
        """
        if not self.visible:
            return

        # Calculate MVP matrix
        model = Matrix44.identity()
        mvp = projection_matrix * view_matrix * model

        # Set uniforms
        self.program['mvp'].write(mvp.astype('f4').tobytes())
        self.program['grid_color'].value = (0.5, 0.5, 0.5, 0.3)  # Semi-transparent gray

        # Save and modify GL state for grid rendering
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.depth_mask = False  # Don't write to depth buffer

        # Render grid lines
        self.vao.render(moderngl.LINES)

        # Restore GL state
        self.ctx.disable(moderngl.BLEND)
        self.ctx.depth_mask = True  # Re-enable depth writing

    def set_visible(self, visible: bool):
        """
        Set grid visibility.

        Args:
            visible: True to show grid, False to hide
        """
        self.visible = visible

    def toggle_visible(self):
        """Toggle grid visibility."""
        self.visible = not self.visible
        return self.visible

    def set_grid_size(self, size: float):
        """
        Change grid cell size.

        Args:
            size: New grid size
        """
        self.grid_size = size
        self._generate_grid_geometry()

    def set_grid_extent(self, extent: int):
        """
        Change grid extent (number of lines).

        Args:
            extent: New extent (number of grid lines in each direction)
        """
        self.grid_extent = extent
        self._generate_grid_geometry()

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'vbo'):
            self.vbo.release()
        if hasattr(self, 'vao'):
            self.vao.release()
        if hasattr(self, 'program'):
            self.program.release()
