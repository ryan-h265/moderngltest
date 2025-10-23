"""
Material

Handles PBR material properties and textures.
"""

from typing import Optional
import moderngl


class Material:
    """
    Represents a PBR material with textures.

    Supports the standard PBR workflow:
    - Base Color (albedo)
    - Metallic/Roughness (packed in single texture)
    - Normal Map
    - Emissive
    """

    def __init__(self, name: str = "Material"):
        """
        Initialize material.

        Args:
            name: Material name for debugging
        """
        self.name = name

        # Texture references (ModernGL texture objects)
        self.base_color_texture: Optional[moderngl.Texture] = None
        self.metallic_roughness_texture: Optional[moderngl.Texture] = None
        self.normal_texture: Optional[moderngl.Texture] = None
        self.emissive_factor: Optional[tuple] = (0.0, 0.0, 0.0)
        self.emissive_texture: Optional[moderngl.Texture] = None

        # Base color factor (used if no texture)
        self.base_color_factor = (1.0, 1.0, 1.0, 1.0)

        # PBR factors
        self.metallic_factor = 1.0
        self.roughness_factor = 1.0

    def has_base_color(self) -> bool:
        """Check if material has base color texture"""
        return self.base_color_texture is not None

    def has_normal_map(self) -> bool:
        """Check if material has normal map"""
        return self.normal_texture is not None

    def has_metallic_roughness(self) -> bool:
        """Check if material has metallic/roughness texture"""
        return self.metallic_roughness_texture is not None

    def bind_textures(self, program: moderngl.Program):
        """
        Bind all material textures to shader.

        Args:
            program: Shader program to bind textures to
        """
        # Bind base color texture to texture unit 0
        if self.base_color_texture:
            self.base_color_texture.use(location=0)
            if 'baseColorTexture' in program:
                program['baseColorTexture'].value = 0
            if 'hasBaseColorTexture' in program:
                program['hasBaseColorTexture'].value = True
        else:
            if 'hasBaseColorTexture' in program:
                program['hasBaseColorTexture'].value = False

        # Bind normal map to texture unit 1
        if self.normal_texture:
            self.normal_texture.use(location=1)
            if 'normalTexture' in program:
                program['normalTexture'].value = 1
            if 'hasNormalTexture' in program:
                program['hasNormalTexture'].value = True
        else:
            if 'hasNormalTexture' in program:
                program['hasNormalTexture'].value = False

        # Bind metallic/roughness to texture unit 2
        if self.metallic_roughness_texture:
            self.metallic_roughness_texture.use(location=2)
            if 'metallicRoughnessTexture' in program:
                program['metallicRoughnessTexture'].value = 2
            if 'hasMetallicRoughnessTexture' in program:
                program['hasMetallicRoughnessTexture'].value = True
        else:
            if 'hasMetallicRoughnessTexture' in program:
                program['hasMetallicRoughnessTexture'].value = False

        # Bind emissive texture to texture unit 3
        if self.emissive_texture:
            self.emissive_texture.use(location=3)
            if 'emissiveTexture' in program:
                program['emissiveTexture'].value = 3
            if 'hasEmissiveTexture' in program:
                program['hasEmissiveTexture'].value = True
        else:
            if 'hasEmissiveTexture' in program:
                program['hasEmissiveTexture'].value = False

        # Set emissive factor
        if 'emissiveFactor' in program:
            program['emissiveFactor'].value = self.emissive_factor

    def release(self):
        """Release GPU resources"""
        if self.base_color_texture:
            self.base_color_texture.release()
        if self.metallic_roughness_texture:
            self.metallic_roughness_texture.release()
        if self.normal_texture:
            self.normal_texture.release()
        if self.emissive_texture:
            self.emissive_texture.release()
