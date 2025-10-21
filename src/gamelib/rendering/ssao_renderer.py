"""
SSAO Renderer

Implements Screen Space Ambient Occlusion for enhanced depth perception.
Uses hemisphere sampling in view space to approximate ambient occlusion.
"""

import numpy as np
import moderngl
from typing import Tuple


class SSAORenderer:
    """
    Screen Space Ambient Occlusion renderer.

    SSAO estimates ambient occlusion by sampling the depth buffer around
    each fragment to determine how occluded it is by nearby geometry.

    Pipeline:
    1. Generate random kernel samples in hemisphere
    2. Generate noise texture for sample rotation
    3. Render SSAO texture using G-buffer position/normal
    4. Apply bilateral blur to reduce noise
    """

    def __init__(self, ctx: moderngl.Context, size: Tuple[int, int],
                 ssao_program: moderngl.Program, blur_program: moderngl.Program):
        """
        Initialize SSAO renderer.

        Args:
            ctx: ModernGL context
            size: Screen size (width, height)
            ssao_program: Compiled SSAO shader program
            blur_program: Compiled blur shader program
        """
        self.ctx = ctx
        self.size = size
        self.width, self.height = size
        self.ssao_program = ssao_program
        self.blur_program = blur_program

        # Create textures and framebuffers
        self._create_textures()
        self._create_framebuffers()

        # Generate sample kernel and noise texture
        self._generate_kernel()
        self._generate_noise_texture()

        # Create fullscreen quad for post-processing
        self._create_fullscreen_quad()

    def _create_textures(self):
        """Create SSAO textures."""
        # SSAO texture (raw occlusion values)
        self.ssao_texture = self.ctx.texture(
            self.size,
            components=1,
            dtype='f4'
        )
        self.ssao_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

        # Blurred SSAO texture (final result)
        self.ssao_blur_texture = self.ctx.texture(
            self.size,
            components=1,
            dtype='f4'
        )
        self.ssao_blur_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

    def _create_framebuffers(self):
        """Create framebuffers for SSAO passes."""
        # FBO for raw SSAO pass
        self.ssao_fbo = self.ctx.framebuffer(
            color_attachments=[self.ssao_texture]
        )

        # FBO for blur pass
        self.blur_fbo = self.ctx.framebuffer(
            color_attachments=[self.ssao_blur_texture]
        )

    def _generate_kernel(self, kernel_size: int = 64):
        """
        Generate sample kernel for SSAO.

        Creates random samples in hemisphere oriented along +Z axis.
        Samples are weighted toward the center for better occlusion detection.

        Args:
            kernel_size: Number of samples (default 64)
        """
        self.kernel_size = kernel_size
        kernel = []

        for i in range(kernel_size):
            # Random sample in hemisphere
            sample = np.array([
                np.random.uniform(-1.0, 1.0),  # x
                np.random.uniform(-1.0, 1.0),  # y
                np.random.uniform(0.0, 1.0)    # z (hemisphere)
            ], dtype='f4')

            # Normalize
            sample = sample / np.linalg.norm(sample)

            # Random length between 0 and 1
            scale = np.random.uniform(0.0, 1.0)

            # Weight samples toward center (more samples close to fragment)
            # Use accelerating interpolation: lerp(0.1, 1.0, scale^2)
            scale = 0.1 + 0.9 * (scale * scale)

            sample *= scale
            kernel.extend(sample.tolist())

        self.kernel = np.array(kernel, dtype='f4')

    def _generate_noise_texture(self, noise_size: int = 4):
        """
        Generate random rotation noise texture.

        This small tiled texture is used to randomly rotate the sample kernel
        at each pixel, reducing banding artifacts.

        Args:
            noise_size: Size of noise texture (default 4x4)
        """
        noise = []
        for _ in range(noise_size * noise_size):
            # Random rotation vectors in tangent space (xy plane)
            noise.extend([
                np.random.uniform(-1.0, 1.0),  # x
                np.random.uniform(-1.0, 1.0),  # y
                0.0                            # z
            ])

        noise_data = np.array(noise, dtype='f4')

        self.noise_texture = self.ctx.texture(
            (noise_size, noise_size),
            components=3,
            data=noise_data.tobytes(),
            dtype='f4'
        )
        # Repeat tiling for screen-space coverage
        self.noise_texture.repeat_x = True
        self.noise_texture.repeat_y = True
        self.noise_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

    def _create_fullscreen_quad(self):
        """Create a fullscreen quad for post-processing passes."""
        # NDC coordinates for fullscreen quad
        vertices = np.array([
            -1.0, -1.0,  # bottom-left
             1.0, -1.0,  # bottom-right
            -1.0,  1.0,  # top-left
             1.0,  1.0,  # top-right
        ], dtype='f4')

        self.quad_vbo = self.ctx.buffer(vertices.tobytes())
        self.quad_vao = self.ctx.vertex_array(
            self.ssao_program,
            [(self.quad_vbo, '2f', 'in_position')]
        )

        # Also create VAO for blur pass
        self.blur_vao = self.ctx.vertex_array(
            self.blur_program,
            [(self.quad_vbo, '2f', 'in_position')]
        )

    def render(self, position_texture: moderngl.Texture,
               normal_texture: moderngl.Texture,
               projection_matrix: np.ndarray,
               radius: float = 0.5,
               bias: float = 0.025,
               intensity: float = 1.5):
        """
        Render SSAO effect.

        Args:
            position_texture: G-buffer position texture (view space)
            normal_texture: G-buffer normal texture (view space)
            projection_matrix: Camera projection matrix
            radius: Sample radius in view space (default 0.5)
            bias: Depth bias to prevent self-occlusion (default 0.025)
            intensity: Occlusion intensity multiplier (default 1.5)
        """
        # Pass 1: Generate raw SSAO
        self.ssao_fbo.use()
        self.ssao_fbo.clear(1.0, 1.0, 1.0, 1.0)  # Start with no occlusion

        # Bind G-buffer textures
        position_texture.use(location=0)
        normal_texture.use(location=1)
        self.noise_texture.use(location=2)

        # Set uniforms
        self.ssao_program['gPosition'].value = 0
        self.ssao_program['gNormal'].value = 1
        self.ssao_program['texNoise'].value = 2

        # Upload kernel samples (upload as a single contiguous array)
        if 'samples' in self.ssao_program:
            self.ssao_program['samples'].write(self.kernel.tobytes())

        if 'projection' in self.ssao_program:
            # Ensure projection matrix is float32
            proj_matrix_f32 = np.array(projection_matrix, dtype='f4')
            self.ssao_program['projection'].write(proj_matrix_f32.tobytes())
        if 'radius' in self.ssao_program:
            self.ssao_program['radius'].value = radius
        if 'bias' in self.ssao_program:
            self.ssao_program['bias'].value = bias
        if 'kernelSize' in self.ssao_program:
            self.ssao_program['kernelSize'].value = self.kernel_size

        # Noise texture tiling
        noise_scale = (self.width / 4.0, self.height / 4.0)
        self.ssao_program['noiseScale'].value = noise_scale

        # Render fullscreen quad
        self.quad_vao.render(moderngl.TRIANGLE_STRIP)

        # Pass 2: Blur SSAO to reduce noise
        self.blur_fbo.use()
        self.blur_fbo.clear(1.0, 1.0, 1.0, 1.0)

        # Bind raw SSAO texture
        self.ssao_texture.use(location=0)
        self.blur_program['ssaoInput'].value = 0

        # Render fullscreen quad with blur
        self.blur_vao.render(moderngl.TRIANGLE_STRIP)

    def resize(self, size: Tuple[int, int]):
        """
        Resize SSAO buffers.

        Args:
            size: New screen size (width, height)
        """
        if size == self.size:
            return

        self.size = size
        self.width, self.height = size

        # Release old resources
        self.ssao_fbo.release()
        self.blur_fbo.release()
        self.ssao_texture.release()
        self.ssao_blur_texture.release()

        # Recreate with new size
        self._create_textures()
        self._create_framebuffers()

    def get_ssao_texture(self) -> moderngl.Texture:
        """
        Get final blurred SSAO texture.

        Returns:
            Blurred SSAO texture (1 component, float)
        """
        return self.ssao_blur_texture

    def release(self):
        """Release all SSAO resources."""
        self.ssao_fbo.release()
        self.blur_fbo.release()
        self.ssao_texture.release()
        self.ssao_blur_texture.release()
        self.noise_texture.release()
        self.quad_vbo.release()
        self.quad_vao.release()
        self.blur_vao.release()
