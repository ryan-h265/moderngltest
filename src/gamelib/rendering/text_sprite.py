"""
Text Sprite Utilities

Provides a helper for rendering text strings into standalone textures.
The generated sprite keeps track of alignment offsets so callers can
position quads using baseline coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import moderngl
from PIL import Image, ImageDraw, ImageFont


@dataclass
class TextSprite:
    """Texture-backed representation of a text string."""

    texture: Optional[moderngl.Texture]
    size: Tuple[int, int]
    offset: Tuple[float, float]

    def release(self) -> None:
        """Release the GPU texture associated with this sprite."""
        if self.texture:
            self.texture.release()
            self.texture = None


def create_text_sprite(
    ctx: moderngl.Context,
    font: ImageFont.FreeTypeFont,
    text: str,
    line_spacing: int,
) -> TextSprite:
    """Render text into an RGBA texture and return a sprite wrapper."""
    # Handle empty strings gracefully by providing a minimal texture.
    measure_text = text if text else " "

    # Measure the multiline text bounds relative to the baseline origin.
    dummy = Image.new("L", (1, 1), 0)
    draw = ImageDraw.Draw(dummy)
    bbox = draw.multiline_textbbox((0, 0), measure_text, font=font, spacing=line_spacing)

    width = max(1, bbox[2] - bbox[0])
    height = max(1, bbox[3] - bbox[1])

    # Offset maps baseline coordinates to sprite top-left.
    offset_x = -float(bbox[0])
    offset_y = -float(bbox[1])

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if text:
        draw.multiline_text(
            (offset_x, offset_y),
            text,
            font=font,
            fill=(255, 255, 255, 255),
            spacing=line_spacing,
        )

    # Flip vertically so that UV (0, 0) corresponds to the bottom-left in OpenGL.
    flipped = image.transpose(Image.FLIP_TOP_BOTTOM)
    texture = ctx.texture(
        image.size,
        components=4,
        data=flipped.tobytes(),
        dtype="u1",
    )
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    texture.repeat_x = False
    texture.repeat_y = False

    return TextSprite(texture=texture, size=image.size, offset=(offset_x, offset_y))
