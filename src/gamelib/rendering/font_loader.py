"""
Font Loader

Loads TrueType fonts and generates texture atlases for text rendering.
Uses PIL/Pillow to render glyphs and extract metrics.
"""

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Dict, Tuple


class GlyphMetrics:
    """Metrics for a single glyph."""

    def __init__(self, uv_min: Tuple[float, float], uv_max: Tuple[float, float],
                 width: int, height: int, bearing_x: int, bearing_y: int, advance: int):
        """
        Initialize glyph metrics.

        Args:
            uv_min: Bottom-left UV coordinate (u, v)
            uv_max: Top-right UV coordinate (u, v)
            width: Glyph width in pixels
            height: Glyph height in pixels
            bearing_x: Horizontal bearing (offset from cursor)
            bearing_y: Vertical bearing (offset from baseline)
            advance: Horizontal advance to next character
        """
        self.uv_min = uv_min
        self.uv_max = uv_max
        self.width = width
        self.height = height
        self.bearing_x = bearing_x
        self.bearing_y = bearing_y
        self.advance = advance


class FontLoader:
    """
    Loads TrueType fonts and generates texture atlases.

    Pipeline:
    1. Load TTF font using PIL
    2. Render each glyph to individual image
    3. Pack glyphs into texture atlas
    4. Calculate UV coordinates for each glyph
    5. Upload atlas to GPU
    """

    def __init__(self, ctx: moderngl.Context, font_path: str, font_size: int, atlas_size: int = 512):
        """
        Initialize font loader.

        Args:
            ctx: ModernGL context
            font_path: Path to TTF font file
            font_size: Font size in pixels
            atlas_size: Texture atlas resolution (square)
        """
        self.ctx = ctx
        self.font_path = Path(font_path)
        self.font_size = font_size
        self.atlas_size = atlas_size

        # Load font
        self.font = ImageFont.truetype(str(self.font_path), font_size)

        # Character set to render (ASCII printable + extended)
        self.charset = ''.join(chr(i) for i in range(32, 127))  # ASCII 32-126

        # Glyph metrics dictionary (char -> GlyphMetrics)
        self.glyphs: Dict[str, GlyphMetrics] = {}

        # Generate atlas
        self.atlas_texture = self._generate_atlas()

    def _generate_atlas(self) -> moderngl.Texture:
        """
        Generate texture atlas from font.

        Returns:
            OpenGL texture containing all glyphs
        """
        # Create atlas image (RGBA)
        atlas = Image.new('RGBA', (self.atlas_size, self.atlas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(atlas)

        # Calculate grid layout
        # Estimate max glyph size (for most monospace fonts, this works well)
        max_glyph_width = self.font_size
        max_glyph_height = self.font_size * 2  # Extra height for descenders

        padding = 2  # Padding between glyphs
        cols = (self.atlas_size - padding) // (max_glyph_width + padding)

        x, y = padding, padding
        current_row_height = 0

        # Render each character
        for char in self.charset:
            # Get bounding box using textbbox (PIL 8.0+)
            bbox = draw.textbbox((0, 0), char, font=self.font)
            glyph_width = bbox[2] - bbox[0]
            glyph_height = bbox[3] - bbox[1]

            # Move to next row if needed
            if x + glyph_width + padding > self.atlas_size:
                x = padding
                y += current_row_height + padding
                current_row_height = 0

            # Check if we've run out of vertical space
            if y + glyph_height + padding > self.atlas_size:
                print(f"Warning: Atlas size ({self.atlas_size}x{self.atlas_size}) too small for charset")
                break

            # Draw glyph
            # Offset by bearing to align properly
            draw.text((x - bbox[0], y - bbox[1]), char, font=self.font, fill=(255, 255, 255, 255))

            # Calculate UV coordinates (normalized 0-1)
            # Don't flip here - will flip in shader instead
            uv_min = (x / self.atlas_size, y / self.atlas_size)
            uv_max = ((x + glyph_width) / self.atlas_size, (y + glyph_height) / self.atlas_size)

            # Get advance width (for cursor positioning)
            # Use getlength for accurate advance width
            advance = int(draw.textlength(char, font=self.font))

            # Store glyph metrics
            self.glyphs[char] = GlyphMetrics(
                uv_min=uv_min,
                uv_max=uv_max,
                width=glyph_width,
                height=glyph_height,
                bearing_x=-bbox[0],  # Horizontal bearing
                bearing_y=-bbox[1],  # Vertical bearing (from top)
                advance=advance
            )

            # Update position
            x += glyph_width + padding
            current_row_height = max(current_row_height, glyph_height)

        # Convert to numpy array and upload to GPU
        atlas_data = np.array(atlas, dtype='uint8')

        # Create OpenGL texture
        texture = self.ctx.texture(
            (self.atlas_size, self.atlas_size),
            components=4,
            data=atlas_data.tobytes(),
            dtype='u1'
        )

        # Set texture parameters
        # Use LINEAR filtering (works better with some font rendering)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        texture.repeat_x = False
        texture.repeat_y = False

        # Save atlas for debugging (disabled for performance)
        # atlas.save('/tmp/debug_atlas.png')
        # print(f"Font atlas saved to /tmp/debug_atlas.png")

        return texture

    def get_texture(self) -> moderngl.Texture:
        """
        Get the texture atlas.

        Returns:
            OpenGL texture containing all glyphs
        """
        return self.atlas_texture

    def get_glyph(self, char: str) -> GlyphMetrics:
        """
        Get metrics for a specific character.

        Args:
            char: Character to look up

        Returns:
            Glyph metrics, or None if character not in atlas
        """
        return self.glyphs.get(char, self.glyphs.get(' ', None))  # Fallback to space

    def has_glyph(self, char: str) -> bool:
        """
        Check if character is available in atlas.

        Args:
            char: Character to check

        Returns:
            True if character is available
        """
        return char in self.glyphs

    def get_line_height(self) -> int:
        """
        Get recommended line height (spacing between lines).

        Returns:
            Line height in pixels
        """
        return self.font_size

    def release(self):
        """Release GPU resources."""
        if self.atlas_texture:
            self.atlas_texture.release()
