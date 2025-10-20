#version 410

// Shadow Map Vertex Shader
// Transforms geometry to light's clip space for depth rendering

uniform mat4 light_matrix;  // Light projection * view matrix
uniform mat4 model;          // Object model matrix

in vec3 in_position;         // Vertex position

void main() {
    // Transform vertex to light's clip space
    gl_Position = light_matrix * model * vec4(in_position, 1.0);
}
