#version 410

// UI Text Fragment Shader
// Samples font atlas and applies color tinting

// Inputs from vertex shader
in vec2 v_uv;
in vec4 v_color;

// Output
out vec4 fragColor;

// Uniforms
uniform sampler2D fontAtlas;

void main() {
    // Sample font atlas - flip V coordinate to match PIL image orientation
    vec2 flipped_uv = vec2(v_uv.x, 1.0 - v_uv.y);
    vec4 texColor = texture(fontAtlas, flipped_uv);

    // Font atlas has white glyphs (RGB=1.0, A=1.0 for glyph pixels)
    // Multiply vertex color by texture to get final colored text
    fragColor = v_color * texColor;

    // Discard fully transparent fragments
    if (fragColor.a < 0.01) {
        discard;
    }
}
