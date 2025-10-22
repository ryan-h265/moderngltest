"""
UI Renderer

Renders text and UI elements as a final overlay pass.
Uses orthographic projection for pixel-perfect positioning.
"""

import moderngl
import numpy as np
from typing import Tuple
from .text_manager import TextManager


class UIRenderer:
    """
    Renders UI text layers as final pass.

    Pipeline:
    1. Set orthographic projection (screen space)
    2. Enable alpha blending
    3. Disable depth testing (UI always on top)
    4. Render each text layer
    5. Restore OpenGL state
    """

    def __init__(self, ctx: moderngl.Context, shader_program: moderngl.Program, font_texture: moderngl.Texture):
        """
        Initialize UI renderer.

        Args:
            ctx: ModernGL context
            shader_program: Compiled UI shader program
            font_texture: Font atlas texture
        """
        self.ctx = ctx
        self.program = shader_program
        self.font_texture = font_texture

        # VAO cache by layer
        self._vao_cache = {}
        self._vbo_cache = {}

    def render(self, text_manager: TextManager, screen_size: Tuple[int, int]):
        """
        Render all text layers.

        Args:
            text_manager: TextManager with text data
            screen_size: Screen size (width, height) for orthographic projection
        """
        # Get all layers
        layers = text_manager.get_all_layers()
        if not layers:
            print("UIRenderer: No layers to render")
            return

        # Debug output disabled
        # print(f"UIRenderer: Rendering {len(layers)} layers, screen={screen_size}")

        # Setup OpenGL state for UI rendering
        self._setup_ui_state()

        # Create orthographic projection matrix
        proj_matrix = self._create_ortho_matrix(screen_size)
        self.program['projection'].write(proj_matrix.tobytes())

        # Bind font texture (only if used in shader)
        if 'fontAtlas' in self.program:
            self.font_texture.use(location=0)
            self.program['fontAtlas'].value = 0

        # Render each layer
        for layer in layers:
            self._render_layer(text_manager, layer)

        # Restore OpenGL state
        self._restore_state()

    def _setup_ui_state(self):
        """Setup OpenGL state for UI rendering."""
        # Enable alpha blending
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # Disable depth testing (UI always on top)
        self.ctx.disable(moderngl.DEPTH_TEST)

        # Disable face culling for UI
        self.ctx.disable(moderngl.CULL_FACE)

    def _restore_state(self):
        """Restore OpenGL state after UI rendering."""
        # Re-enable depth testing
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Re-enable face culling
        self.ctx.enable(moderngl.CULL_FACE)

        # Disable blending
        self.ctx.disable(moderngl.BLEND)

    def _create_ortho_matrix(self, screen_size: Tuple[int, int]) -> np.ndarray:
        """
        Create orthographic projection matrix for screen-space rendering.

        Maps (0,0) to top-left, (width, height) to bottom-right.

        Args:
            screen_size: Screen dimensions (width, height)

        Returns:
            4x4 projection matrix
        """
        width, height = screen_size

        # Orthographic projection: left, right, bottom, top, near, far
        # Map (0, 0) to top-left corner
        left = 0.0
        right = float(width)
        bottom = float(height)  # Bottom = height (Y increases downward)
        top = 0.0               # Top = 0
        near = -1.0
        far = 1.0

        # Build orthographic projection matrix
        # Use pyrr for correct matrix format
        from pyrr import matrix44
        matrix = matrix44.create_orthogonal_projection_matrix(
            left, right, bottom, top, near, far, dtype=np.float32
        )

        return matrix

    def _render_layer(self, text_manager: TextManager, layer: str):
        """
        Render a single text layer.

        Args:
            text_manager: TextManager instance
            layer: Layer name to render
        """
        # Get geometry for this layer
        geometry = text_manager.get_layer_geometry(layer)
        if not geometry or geometry['vertex_count'] == 0:
            print(f"UIRenderer: Layer '{layer}' has no geometry")
            return

        # Debug output disabled
        # print(f"UIRenderer: Rendering layer '{layer}' with {geometry['vertex_count']} vertices, {geometry['index_count']//3} triangles")

        # Create or update VAO for this layer
        vao = self._get_or_create_vao(layer, geometry)

        # Render
        vao.render(moderngl.TRIANGLES)

    def _get_or_create_vao(self, layer: str, geometry: dict) -> moderngl.VertexArray:
        """
        Get or create VAO for a layer.

        Args:
            layer: Layer name
            geometry: Geometry dictionary

        Returns:
            VAO for rendering
        """
        # Check if VAO exists and is up-to-date
        # For simplicity, recreate VAO each time (can optimize later with dirty flags)

        # Release old VAO/VBOs if they exist
        if layer in self._vao_cache:
            self._vao_cache[layer].release()
        if layer in self._vbo_cache:
            for vbo in self._vbo_cache[layer]:
                vbo.release()

        # Create VBOs
        vertices_vbo = self.ctx.buffer(geometry['vertices'].tobytes())
        uvs_vbo = self.ctx.buffer(geometry['uvs'].tobytes())
        colors_vbo = self.ctx.buffer(geometry['colors'].tobytes())
        indices_vbo = self.ctx.buffer(geometry['indices'].tobytes())

        # Create VAO
        vao = self.ctx.vertex_array(
            self.program,
            [
                (vertices_vbo, '2f', 'in_position'),
                (uvs_vbo, '2f', 'in_uv'),
                (colors_vbo, '4f', 'in_color')
            ],
            index_buffer=indices_vbo
        )

        # Cache VAO and VBOs
        self._vao_cache[layer] = vao
        self._vbo_cache[layer] = [vertices_vbo, uvs_vbo, colors_vbo, indices_vbo]

        return vao

    def resize(self, screen_size: Tuple[int, int]):
        """
        Handle screen resize.

        Args:
            screen_size: New screen size (width, height)
        """
        # Projection matrix is recalculated each frame, so nothing to do here
        pass

    def release(self):
        """Release all GPU resources."""
        # Release all VAOs and VBOs
        for vao in self._vao_cache.values():
            vao.release()
        for vbos in self._vbo_cache.values():
            for vbo in vbos:
                vbo.release()

        self._vao_cache.clear()
        self._vbo_cache.clear()
