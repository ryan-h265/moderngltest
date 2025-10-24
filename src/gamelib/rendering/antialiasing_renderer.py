"""
Anti-Aliasing Renderer

Handles MSAA, FXAA, and SMAA anti-aliasing techniques.
"""

from typing import Tuple, Optional
from enum import Enum, auto
import moderngl
import numpy as np
from .smaa_renderer import SMAARenderer


class AAMode(Enum):
    """Anti-aliasing modes"""
    OFF = auto()
    MSAA_2X = auto()
    MSAA_4X = auto() 
    MSAA_8X = auto()
    FXAA = auto()
    SMAA = auto()
    MSAA_2X_FXAA = auto()
    MSAA_4X_FXAA = auto()
    MSAA_2X_SMAA = auto()
    MSAA_4X_SMAA = auto()


MSAA_MODES = {
    AAMode.MSAA_2X,
    AAMode.MSAA_4X,
    AAMode.MSAA_8X,
    AAMode.MSAA_2X_FXAA,
    AAMode.MSAA_4X_FXAA,
    AAMode.MSAA_2X_SMAA,
    AAMode.MSAA_4X_SMAA,
}


class AntiAliasingRenderer:
    """
    Handles MSAA and FXAA anti-aliasing.
    
    Features:
    - MSAA 2x, 4x, 8x support
    - FXAA post-processing
    - Combined MSAA + FXAA modes
    - Runtime switching between modes
    """
    
    def __init__(
        self, 
        ctx: moderngl.Context, 
        size: Tuple[int, int], 
        fxaa_program: moderngl.Program,
        smaa_edge_program: Optional[moderngl.Program] = None,
        smaa_blend_program: Optional[moderngl.Program] = None,
        smaa_neighborhood_program: Optional[moderngl.Program] = None
    ):
        """
        Initialize anti-aliasing renderer.
        
        Args:
            ctx: ModernGL context
            size: Screen size (width, height)
            fxaa_program: FXAA shader program
            smaa_edge_program: SMAA edge detection shader program (optional)
            smaa_blend_program: SMAA blending weight shader program (optional)
            smaa_neighborhood_program: SMAA neighborhood blending shader program (optional)
        """
        self.ctx = ctx
        self.size = size
        self.fxaa_program = fxaa_program
        self.hdr_mode = False
        
        # Current AA settings
        self.aa_mode = AAMode.OFF
        self.msaa_samples = 0
        self.fxaa_enabled = False
        self.smaa_enabled = False
        
        # SMAA renderer (optional)
        self.smaa_renderer: Optional[SMAARenderer] = None
        if smaa_edge_program and smaa_blend_program and smaa_neighborhood_program:
            self.smaa_renderer = SMAARenderer(
                ctx, size, smaa_edge_program, smaa_blend_program, smaa_neighborhood_program
            )
        
        # Framebuffers
        self.msaa_fbo: Optional[moderngl.Framebuffer] = None
        self.resolve_fbo: Optional[moderngl.Framebuffer] = None
        self.fxaa_fbo: Optional[moderngl.Framebuffer] = None
        self.smaa_fbo: Optional[moderngl.Framebuffer] = None
        
        # Textures
        self.msaa_color: Optional[moderngl.Texture] = None
        self.msaa_depth: Optional[moderngl.Texture] = None
        self.resolve_color: Optional[moderngl.Texture] = None
        self.resolve_depth: Optional[moderngl.Texture] = None
        self.fxaa_color: Optional[moderngl.Texture] = None
        self.smaa_color: Optional[moderngl.Texture] = None
        
        # Full-screen quad for FXAA
        self._create_fullscreen_quad()
        
        # Initialize with default mode
        self.set_aa_mode(AAMode.OFF)
        
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
        
        # Create VAO
        self.quad_vao = self.ctx.vertex_array(
            self.fxaa_program,
            [(self.quad_vbo, '2f 2f', 'in_position', 'in_texcoord')],
            self.quad_ibo
        )
    
    def _create_framebuffers(self):
        """Create framebuffers for current AA mode"""
        self._cleanup_framebuffers()
        
        w, h = self.size
        
        # Always create resolve framebuffer (single-sampled)
        self.resolve_color = self.ctx.texture((w, h), 4)
        self.resolve_depth = self.ctx.depth_texture((w, h))
        self.resolve_fbo = self.ctx.framebuffer(
            color_attachments=[self.resolve_color],
            depth_attachment=self.resolve_depth
        )
        
        # Create MSAA framebuffer if needed
        if self.msaa_samples > 0:
            self.msaa_color = self.ctx.texture((w, h), 4, samples=self.msaa_samples)
            self.msaa_depth = self.ctx.depth_texture((w, h), samples=self.msaa_samples)
            self.msaa_fbo = self.ctx.framebuffer(
                color_attachments=[self.msaa_color],
                depth_attachment=self.msaa_depth
            )
        
        # Create FXAA framebuffer if needed
        if self.fxaa_enabled:
            self.fxaa_color = self.ctx.texture((w, h), 4)
            self.fxaa_fbo = self.ctx.framebuffer(
                color_attachments=[self.fxaa_color]
            )
        
        # Create SMAA framebuffer if needed
        if self.smaa_enabled and self.smaa_renderer:
            self.smaa_color = self.ctx.texture((w, h), 4)
            self.smaa_fbo = self.ctx.framebuffer(
                color_attachments=[self.smaa_color]
            )
            # Resize SMAA renderer
            self.smaa_renderer.resize((w, h))
    
    def _cleanup_framebuffers(self):
        """Clean up existing framebuffers"""
        if self.msaa_fbo:
            self.msaa_fbo.release()
            self.msaa_fbo = None
        if self.resolve_fbo:
            self.resolve_fbo.release() 
            self.resolve_fbo = None
        if self.fxaa_fbo:
            self.fxaa_fbo.release()
            self.fxaa_fbo = None
        if self.smaa_fbo:
            self.smaa_fbo.release()
            self.smaa_fbo = None
            
        if self.msaa_color:
            self.msaa_color.release()
            self.msaa_color = None
        if self.msaa_depth:
            self.msaa_depth.release()
            self.msaa_depth = None
        if self.resolve_color:
            self.resolve_color.release()
            self.resolve_color = None
        if self.resolve_depth:
            self.resolve_depth.release()
            self.resolve_depth = None
        if self.fxaa_color:
            self.fxaa_color.release()
            self.fxaa_color = None
        if self.smaa_color:
            self.smaa_color.release()
            self.smaa_color = None
    
    def set_aa_mode(self, mode: AAMode):
        """
        Set anti-aliasing mode.
        
        Args:
            mode: AA mode to set
        """
        if self.hdr_mode and mode in MSAA_MODES:
            fallback = AAMode.FXAA if self.fxaa_program else AAMode.OFF
            print("HDR pipeline disables MSAA-based AA modes. Falling back to", fallback.name)
            mode = fallback
        self.aa_mode = mode
        
        # Configure settings based on mode
        if mode == AAMode.OFF:
            self.msaa_samples = 0
            self.fxaa_enabled = False
            self.smaa_enabled = False
        elif mode == AAMode.MSAA_2X:
            self.msaa_samples = 2
            self.fxaa_enabled = False
            self.smaa_enabled = False
        elif mode == AAMode.MSAA_4X:
            self.msaa_samples = 4
            self.fxaa_enabled = False
            self.smaa_enabled = False
        elif mode == AAMode.MSAA_8X:
            self.msaa_samples = 8
            self.fxaa_enabled = False
            self.smaa_enabled = False
        elif mode == AAMode.FXAA:
            self.msaa_samples = 0
            self.fxaa_enabled = True
            self.smaa_enabled = False
        elif mode == AAMode.SMAA:
            self.msaa_samples = 0
            self.fxaa_enabled = False
            self.smaa_enabled = True
        elif mode == AAMode.MSAA_2X_FXAA:
            self.msaa_samples = 2
            self.fxaa_enabled = True
            self.smaa_enabled = False
        elif mode == AAMode.MSAA_4X_FXAA:
            self.msaa_samples = 4
            self.fxaa_enabled = True
            self.smaa_enabled = False
        elif mode == AAMode.MSAA_2X_SMAA:
            self.msaa_samples = 2
            self.fxaa_enabled = False
            self.smaa_enabled = True
        elif mode == AAMode.MSAA_4X_SMAA:
            self.msaa_samples = 4
            self.fxaa_enabled = False
            self.smaa_enabled = True
            
        # Recreate framebuffers
        self._create_framebuffers()
    
    def get_render_target(self) -> moderngl.Framebuffer:
        """
        Get the framebuffer to render into.
        
        Returns:
            Framebuffer for scene rendering
        """
        if self.msaa_samples > 0:
            return self.msaa_fbo
        if self.fxaa_enabled or self.smaa_enabled:
            return self.resolve_fbo
        if self.hdr_mode:
            return self.ctx.screen
        return self.ctx.screen
    
    def resolve_and_present(self):
        """
        Resolve MSAA, apply post-processing (FXAA/SMAA), and present to screen.
        Call this after rendering the scene.
        """
        # Step 1: Resolve MSAA if enabled
        if self.msaa_samples > 0:
            self.ctx.copy_framebuffer(self.resolve_fbo, self.msaa_fbo)
        
        # Step 2: Apply post-processing
        if self.smaa_enabled and self.smaa_renderer:
            self._apply_smaa()
            self._present_to_screen(self.smaa_color)
        elif self.fxaa_enabled:
            self._apply_fxaa()
            self._present_to_screen(self.fxaa_color)
        else:
            # Present resolve buffer to screen
            self._present_to_screen(self.resolve_color)

    def set_hdr_mode(self, enabled: bool):
        """Enable or disable HDR pipeline compatibility (disables MSAA paths)."""
        if self.hdr_mode == enabled:
            return

        self.hdr_mode = enabled
        if self.hdr_mode and self.aa_mode in MSAA_MODES:
            fallback = AAMode.FXAA if self.fxaa_program else AAMode.OFF
            print("HDR pipeline disables MSAA-based AA modes. Falling back to", fallback.name)
            self.set_aa_mode(fallback)
        else:
            self._create_framebuffers()
    
    def _apply_fxaa(self):
        """Apply FXAA post-processing"""
        # Render FXAA to fxaa_fbo
        self.fxaa_fbo.use()
        self.fxaa_fbo.clear()
        
        # Set FXAA uniforms
        w, h = self.size
        self.fxaa_program['u_texel_size'].value = (1.0 / w, 1.0 / h)
        self.fxaa_program['u_fxaa_enabled'].value = True
        
        # Bind input texture
        self.resolve_color.use(0)
        self.fxaa_program['u_texture'] = 0
        
        # Render full-screen quad
        self.quad_vao.render()
    
    def _apply_smaa(self):
        """Apply SMAA post-processing"""
        if self.smaa_renderer:
            self.smaa_renderer.apply_smaa(self.resolve_color, self.smaa_fbo)
    
    def _present_to_screen(self, texture: moderngl.Texture):
        """
        Present a texture to the screen.
        
        Args:
            texture: Texture to present
        """
        # Use screen framebuffer
        self.ctx.screen.use()
        
        # Set up FXAA program for simple blit (FXAA disabled)
        self.fxaa_program['u_fxaa_enabled'].value = False
        
        # Bind texture
        texture.use(0)
        self.fxaa_program['u_texture'] = 0
        
        # Render full-screen quad
        self.quad_vao.render()
    
    def cycle_aa_mode(self) -> AAMode:
        """
        Cycle to the next AA mode.
        
        Returns:
            New AA mode
        """
        if self.smaa_renderer:
            modes = [AAMode.OFF, AAMode.FXAA, AAMode.SMAA, AAMode.MSAA_2X, AAMode.MSAA_4X, AAMode.MSAA_4X_SMAA]
        else:
            modes = [AAMode.OFF, AAMode.FXAA, AAMode.MSAA_2X, AAMode.MSAA_4X, AAMode.MSAA_4X_FXAA]

        if self.hdr_mode:
            modes = [mode for mode in modes if mode not in MSAA_MODES]
            if not modes:
                modes = [AAMode.OFF, AAMode.FXAA]
        
        try:
            current_index = modes.index(self.aa_mode)
            next_index = (current_index + 1) % len(modes)
            next_mode = modes[next_index]
        except ValueError:
            # Current mode not in cycle list, start from beginning
            next_mode = modes[0]
        
        self.set_aa_mode(next_mode)
        return next_mode
    
    def toggle_msaa(self) -> bool:
        """
        Toggle MSAA on/off.
        
        Returns:
            True if MSAA is now enabled
        """
        if self.hdr_mode:
            print("MSAA is disabled while HDR pipeline is active.")
            return False
        if self.msaa_samples > 0:
            # Turn off MSAA
            if self.fxaa_enabled:
                self.set_aa_mode(AAMode.FXAA)
            else:
                self.set_aa_mode(AAMode.OFF)
        else:
            # Turn on MSAA 4x
            if self.fxaa_enabled:
                self.set_aa_mode(AAMode.MSAA_4X_FXAA)
            else:
                self.set_aa_mode(AAMode.MSAA_4X)
        
        return self.msaa_samples > 0
    
    def toggle_fxaa(self) -> bool:
        """
        Toggle FXAA on/off.
        
        Returns:
            True if FXAA is now enabled
        """
        if self.fxaa_enabled:
            # Turn off FXAA
            if self.msaa_samples > 0:
                if self.msaa_samples == 2:
                    self.set_aa_mode(AAMode.MSAA_2X)
                elif self.msaa_samples == 4:
                    self.set_aa_mode(AAMode.MSAA_4X)
                else:
                    self.set_aa_mode(AAMode.MSAA_8X)
            else:
                self.set_aa_mode(AAMode.OFF)
        else:
            # Turn on FXAA
            if self.msaa_samples > 0:
                if self.msaa_samples == 2:
                    self.set_aa_mode(AAMode.MSAA_2X_FXAA)
                elif self.msaa_samples == 4:
                    self.set_aa_mode(AAMode.MSAA_4X_FXAA)
                else:
                    # 8x MSAA + FXAA not in enum, fall back to 4x
                    self.set_aa_mode(AAMode.MSAA_4X_FXAA)
            else:
                self.set_aa_mode(AAMode.FXAA)
        
        return self.fxaa_enabled
    
    def toggle_smaa(self) -> bool:
        """
        Toggle SMAA on/off.
        
        Returns:
            True if SMAA is now enabled
        """
        if not self.smaa_renderer:
            return False  # SMAA not available
            
        if self.smaa_enabled:
            # Turn off SMAA
            if self.msaa_samples > 0:
                if self.msaa_samples == 2:
                    self.set_aa_mode(AAMode.MSAA_2X)
                elif self.msaa_samples == 4:
                    self.set_aa_mode(AAMode.MSAA_4X)
                else:
                    self.set_aa_mode(AAMode.MSAA_8X)
            else:
                self.set_aa_mode(AAMode.OFF)
        else:
            # Turn on SMAA
            if self.msaa_samples > 0:
                if self.msaa_samples == 2:
                    self.set_aa_mode(AAMode.MSAA_2X_SMAA)
                elif self.msaa_samples == 4:
                    self.set_aa_mode(AAMode.MSAA_4X_SMAA)
                else:
                    # 8x MSAA + SMAA not in enum, fall back to 4x
                    self.set_aa_mode(AAMode.MSAA_4X_SMAA)
            else:
                self.set_aa_mode(AAMode.SMAA)
        
        return self.smaa_enabled
    
    def get_aa_mode_name(self) -> str:
        """
        Get human-readable name for current AA mode.
        
        Returns:
            AA mode name
        """
        names = {
            AAMode.OFF: "Off",
            AAMode.MSAA_2X: "MSAA 2x",
            AAMode.MSAA_4X: "MSAA 4x",
            AAMode.MSAA_8X: "MSAA 8x",
            AAMode.FXAA: "FXAA",
            AAMode.SMAA: "SMAA",
            AAMode.MSAA_2X_FXAA: "MSAA 2x + FXAA",
            AAMode.MSAA_4X_FXAA: "MSAA 4x + FXAA",
            AAMode.MSAA_2X_SMAA: "MSAA 2x + SMAA",
            AAMode.MSAA_4X_SMAA: "MSAA 4x + SMAA"
        }
        return names.get(self.aa_mode, "Unknown")
    
    def resize(self, size: Tuple[int, int]):
        """
        Resize framebuffers for new screen size.
        
        Args:
            size: New screen size (width, height)
        """
        if size != self.size:
            self.size = size
            self._create_framebuffers()
    
    def cleanup(self):
        """Clean up resources"""
        self._cleanup_framebuffers()
        
        if self.smaa_renderer:
            self.smaa_renderer.cleanup()
        
        if hasattr(self, 'quad_vao'):
            self.quad_vao.release()
        if hasattr(self, 'quad_vbo'):
            self.quad_vbo.release()
        if hasattr(self, 'quad_ibo'):
            self.quad_ibo.release()
