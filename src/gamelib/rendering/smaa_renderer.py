"""
SMAA Renderer

Implements Enhanced Subpixel Morphological Antialiasing (SMAA).
A 3-pass technique that provides better quality than FXAA.

Uses official SMAA 1.0 precomputed lookup textures for professional-grade antialiasing.
"""

from typing import Tuple
import moderngl
import numpy as np
from pathlib import Path
import sys

# Add assets directory to path to import textures
assets_path = Path(__file__).parent.parent.parent.parent / "assets"
sys.path.insert(0, str(assets_path))

from textures.smaa_textures import (
    get_area_texture_data,
    get_search_texture_data,
    AREA_TEX_WIDTH,
    AREA_TEX_HEIGHT,
    AREA_TEX_COMPONENTS,
    SEARCH_TEX_WIDTH,
    SEARCH_TEX_HEIGHT,
    SEARCH_TEX_COMPONENTS
)


class SMAARenderer:
    """
    SMAA (Enhanced Subpixel Morphological Antialiasing) Renderer.
    
    SMAA is a 3-pass technique:
    1. Edge Detection - Find edges using color/luma
    2. Blending Weight Calculation - Determine blend amounts
    3. Neighborhood Blending - Apply the anti-aliasing
    
    Provides better quality than FXAA with comparable performance.
    """
    
    def __init__(
        self, 
        ctx: moderngl.Context, 
        size: Tuple[int, int],
        edge_program: moderngl.Program,
        blend_program: moderngl.Program,
        neighborhood_program: moderngl.Program
    ):
        """
        Initialize SMAA renderer.
        
        Args:
            ctx: ModernGL context
            size: Screen size (width, height)
            edge_program: Edge detection shader program
            blend_program: Blending weight calculation shader program
            neighborhood_program: Neighborhood blending shader program
        """
        self.ctx = ctx
        self.size = size
        self.edge_program = edge_program
        self.blend_program = blend_program
        self.neighborhood_program = neighborhood_program
        
        # Framebuffers and textures
        self.edges_fbo: moderngl.Framebuffer = None
        self.blend_fbo: moderngl.Framebuffer = None
        self.edges_texture: moderngl.Texture = None
        self.blend_texture: moderngl.Texture = None
        
        # Precomputed lookup textures (simplified - would normally be loaded from files)
        self.area_texture: moderngl.Texture = None
        self.search_texture: moderngl.Texture = None
        
        # Full-screen quad
        self._create_fullscreen_quad()
        
        # Create framebuffers and textures
        self._create_framebuffers()
        self._create_lookup_textures()
    
    def _create_fullscreen_quad(self):
        """Create geometry for full-screen quad"""
        # Full-screen quad vertices (position + texcoords)
        vertices = np.array([
            # Position    # TexCoord
            -1.0, -1.0,   0.0, 0.0,  # Bottom-left
             1.0, -1.0,   1.0, 0.0,  # Bottom-right
             1.0,  1.0,   1.0, 1.0,  # Top-right
            -1.0,  1.0,   0.0, 1.0,  # Top-left
        ], dtype=np.float32)
        
        indices = np.array([
            0, 1, 2,
            2, 3, 0
        ], dtype=np.uint32)
        
        # Create buffers
        self.quad_vbo = self.ctx.buffer(vertices.tobytes())
        self.quad_ibo = self.ctx.buffer(indices.tobytes())
        
        # Create VAOs for each pass
        self.edge_vao = self._create_vao(self.edge_program)
        self.blend_vao = self._create_vao(self.blend_program)
        self.neighborhood_vao = self._create_vao(self.neighborhood_program)
    
    def _create_vao(self, program: moderngl.Program) -> moderngl.VertexArray:
        """Create VAO for a specific program"""
        return self.ctx.vertex_array(
            program,
            [(self.quad_vbo, '2f 2f', 'in_position', 'in_texcoord')],
            self.quad_ibo
        )
    
    def _create_framebuffers(self):
        """Create framebuffers for SMAA passes"""
        w, h = self.size
        
        # Edge detection framebuffer (RG format for horizontal/vertical edges)
        self.edges_texture = self.ctx.texture((w, h), 2)  # RG format
        self.edges_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.edges_fbo = self.ctx.framebuffer(color_attachments=[self.edges_texture])
        
        # Blending weights framebuffer (RGBA format for blend weights)
        self.blend_texture = self.ctx.texture((w, h), 4)  # RGBA format
        self.blend_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.blend_fbo = self.ctx.framebuffer(color_attachments=[self.blend_texture])
    
    def _create_lookup_textures(self):
        """Create precomputed lookup textures for SMAA using official SMAA 1.0 data"""
        # Load official SMAA area texture (160x560, RG8 format)
        # Used for coverage area lookup in blending weight calculation
        area_data = get_area_texture_data()
        area_size = (AREA_TEX_WIDTH, AREA_TEX_HEIGHT)

        self.area_texture = self.ctx.texture(area_size, AREA_TEX_COMPONENTS, area_data)
        self.area_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.area_texture.repeat_x = False
        self.area_texture.repeat_y = False

        # Load official SMAA search texture (64x16, R8 format)
        # Used for pattern searching in blending weight calculation
        search_data = get_search_texture_data()
        search_size = (SEARCH_TEX_WIDTH, SEARCH_TEX_HEIGHT)

        self.search_texture = self.ctx.texture(search_size, SEARCH_TEX_COMPONENTS, search_data)
        self.search_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.search_texture.repeat_x = False
        self.search_texture.repeat_y = False
    
    def apply_smaa(self, input_texture: moderngl.Texture, output_fbo: moderngl.Framebuffer):
        """
        Apply SMAA to input texture and render to output framebuffer.
        
        Args:
            input_texture: Input color texture
            output_fbo: Output framebuffer to render final result
        """
        w, h = self.size
        rt_metrics = (1.0 / w, 1.0 / h, float(w), float(h))
        
        # Pass 1: Edge Detection
        self._edge_detection_pass(input_texture, rt_metrics)
        
        # Pass 2: Blending Weight Calculation
        self._blending_weight_pass(rt_metrics)
        
        # Pass 3: Neighborhood Blending
        self._neighborhood_blending_pass(input_texture, output_fbo, rt_metrics)
    
    def _edge_detection_pass(self, input_texture: moderngl.Texture, rt_metrics: tuple):
        """Pass 1: Edge Detection"""
        self.edges_fbo.use()
        self.edges_fbo.clear(0.0, 0.0, 0.0, 0.0)
        
        # Set uniforms
        self.edge_program['SMAA_RT_METRICS'] = rt_metrics
        
        # Bind input texture
        input_texture.use(0)
        self.edge_program['colorTex'] = 0
        
        # Render
        self.edge_vao.render()
    
    def _blending_weight_pass(self, rt_metrics: tuple):
        """Pass 2: Blending Weight Calculation"""
        self.blend_fbo.use()
        self.blend_fbo.clear(0.0, 0.0, 0.0, 0.0)

        # Note: SMAA_RT_METRICS is only used in the vertex shader,
        # passed to fragment shader via varyings (pixcoord, offset)

        # Bind textures
        self.edges_texture.use(0)
        self.area_texture.use(1)
        self.search_texture.use(2)

        self.blend_program['edgesTex'] = 0
        self.blend_program['areaTex'] = 1
        self.blend_program['searchTex'] = 2

        # Render
        self.blend_vao.render()
    
    def _neighborhood_blending_pass(self, input_texture: moderngl.Texture, output_fbo: moderngl.Framebuffer, rt_metrics: tuple):
        """Pass 3: Neighborhood Blending"""
        output_fbo.use()
        
        # Set uniforms
        self.neighborhood_program['SMAA_RT_METRICS'] = rt_metrics
        
        # Bind textures
        input_texture.use(0)
        self.blend_texture.use(1)
        
        self.neighborhood_program['colorTex'] = 0
        self.neighborhood_program['blendTex'] = 1
        
        # Render
        self.neighborhood_vao.render()
    
    def resize(self, size: Tuple[int, int]):
        """
        Resize framebuffers for new screen size.
        
        Args:
            size: New screen size (width, height)
        """
        if size != self.size:
            self.size = size
            self._cleanup_framebuffers()
            self._create_framebuffers()
    
    def _cleanup_framebuffers(self):
        """Clean up framebuffers"""
        if self.edges_fbo:
            self.edges_fbo.release()
            self.edges_fbo = None
        if self.blend_fbo:
            self.blend_fbo.release()
            self.blend_fbo = None
        if self.edges_texture:
            self.edges_texture.release()
            self.edges_texture = None
        if self.blend_texture:
            self.blend_texture.release()
            self.blend_texture = None
    
    def cleanup(self):
        """Clean up all resources"""
        self._cleanup_framebuffers()
        
        if self.area_texture:
            self.area_texture.release()
        if self.search_texture:
            self.search_texture.release()
        
        if hasattr(self, 'edge_vao'):
            self.edge_vao.release()
        if hasattr(self, 'blend_vao'):
            self.blend_vao.release()
        if hasattr(self, 'neighborhood_vao'):
            self.neighborhood_vao.release()
        if hasattr(self, 'quad_vbo'):
            self.quad_vbo.release()
        if hasattr(self, 'quad_ibo'):
            self.quad_ibo.release()