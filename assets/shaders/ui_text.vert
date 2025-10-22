#version 410

// UI Text Vertex Shader
// Orthographic projection for screen-space text rendering

// Inputs
in vec2 in_position;  // Screen-space position (pixels)
in vec2 in_uv;        // Texture coordinates
in vec4 in_color;     // Vertex color (RGBA)

// Outputs
out vec2 v_uv;
out vec4 v_color;

// Uniforms
uniform mat4 projection;  // Orthographic projection matrix

void main() {
    // Transform to clip space using orthographic projection
    gl_Position = projection * vec4(in_position, 0.0, 1.0);

    // Pass through UV and color
    v_uv = in_uv;
    v_color = in_color;
}
