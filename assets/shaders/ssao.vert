#version 410

// SSAO Vertex Shader
// Simple fullscreen quad pass-through

in vec2 in_position;
out vec2 texCoord;

void main() {
    // Convert from NDC [-1,1] to texture coords [0,1]
    texCoord = in_position * 0.5 + 0.5;
    gl_Position = vec4(in_position, 0.0, 1.0);
}
