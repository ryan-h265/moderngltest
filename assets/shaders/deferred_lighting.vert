#version 410

// Deferred Rendering - Lighting Pass Vertex Shader
// Renders a full-screen quad for lighting calculations

// Vertex attributes (full-screen quad: -1 to 1)
in vec2 in_position;

// Output texture coordinates
out vec2 v_texcoord;

void main() {
    // Pass through position (already in NDC space: -1 to 1)
    gl_Position = vec4(in_position, 0.0, 1.0);

    // Convert from NDC [-1, 1] to texture coordinates [0, 1]
    v_texcoord = in_position * 0.5 + 0.5;
}
