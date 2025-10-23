"""
G-Buffer (Geometry Buffer)

Manages Multiple Render Targets (MRT) for deferred rendering.
The G-Buffer stores geometric and material properties of the scene,
which are later used in the lighting pass.
"""

from typing import Tuple
import moderngl


class GBuffer:
    """
    G-Buffer for deferred rendering.

    Stores scene geometry properties in multiple textures:
    - Position (RGB32F): View-space position (for SSAO)
    - Normal (RGB16F): View-space normal vectors (for SSAO)
    - Albedo (RGBA8): Base color (RGB) + AO (A, currently unused)
    - Material (RG16F): Metallic (R) + Roughness (G) for PBR
    - Depth (DEPTH24_STENCIL8): Depth and stencil information

    These textures are written in the geometry pass and read in the lighting pass.
    """

    def __init__(self, ctx: moderngl.Context, size: Tuple[int, int]):
        """
        Initialize G-Buffer.

        Args:
            ctx: ModernGL context
            size: Buffer size (width, height)
        """
        self.ctx = ctx
        self.size = size
        self.width, self.height = size

        # Create textures for geometry data
        self._create_textures()

        # Create framebuffer with multiple render targets
        self._create_framebuffer()

    def _create_textures(self):
        """Create all G-Buffer textures."""
        # Position texture (RGB32F - high precision for world positions)
        self.position_texture = self.ctx.texture(
            self.size,
            components=3,
            dtype='f4'  # 32-bit float
        )
        self.position_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # Normal texture (RGB16F - sufficient precision for normals)
        self.normal_texture = self.ctx.texture(
            self.size,
            components=3,
            dtype='f2'  # 16-bit float
        )
        self.normal_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # Albedo texture (RGBA8)
        # RGB = base color, A = ambient occlusion (currently unused, set to 1.0)
        self.albedo_texture = self.ctx.texture(
            self.size,
            components=4,
            dtype='f1'  # 8-bit per channel
        )
        self.albedo_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # Material properties texture (RG16F)
        # R = metallic, G = roughness (for PBR)
        self.material_texture = self.ctx.texture(
            self.size,
            components=2,
            dtype='f2'  # 16-bit float
        )
        self.material_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # Depth buffer (required for depth testing)
        self.depth_texture = self.ctx.depth_texture(self.size)
        self.depth_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

    def _create_framebuffer(self):
        """Create framebuffer with multiple color attachments (MRT)."""
        self.fbo = self.ctx.framebuffer(
            color_attachments=[
                self.position_texture,  # location = 0
                self.normal_texture,    # location = 1
                self.albedo_texture,    # location = 2
                self.material_texture,  # location = 3 (metallic + roughness)
            ],
            depth_attachment=self.depth_texture
        )

    def resize(self, size: Tuple[int, int]):
        """
        Resize G-Buffer (called on window resize).

        Args:
            size: New buffer size (width, height)
        """
        if size == self.size:
            return

        self.size = size
        self.width, self.height = size

        # Release old resources
        self.fbo.release()
        self.position_texture.release()
        self.normal_texture.release()
        self.albedo_texture.release()
        self.material_texture.release()
        self.depth_texture.release()

        # Recreate with new size
        self._create_textures()
        self._create_framebuffer()

    def clear(self, color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)):
        """
        Clear G-Buffer.

        Args:
            color: Clear color (R, G, B, A)
        """
        self.fbo.clear(*color)

    def use(self):
        """Bind G-Buffer framebuffer for rendering (geometry pass)."""
        self.fbo.use()

    def bind_textures(self, start_location: int = 0):
        """
        Bind all G-Buffer textures for reading (lighting pass).

        Args:
            start_location: Starting texture unit (default: 0)
                           position=0, normal=1, albedo=2, material=3, depth=4
        """
        self.position_texture.use(location=start_location + 0)
        self.normal_texture.use(location=start_location + 1)
        self.albedo_texture.use(location=start_location + 2)
        self.material_texture.use(location=start_location + 3)
        self.depth_texture.use(location=start_location + 4)

    def release(self):
        """Release all G-Buffer resources."""
        self.fbo.release()
        self.position_texture.release()
        self.normal_texture.release()
        self.albedo_texture.release()
        self.material_texture.release()
        self.depth_texture.release()

    @property
    def viewport(self) -> Tuple[int, int, int, int]:
        """Get viewport tuple for this buffer."""
        return (0, 0, self.width, self.height)
