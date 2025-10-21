#version 410

// Main Lighting Vertex Shader
// Multi-light shadow mapping with PCF

#define MAX_LIGHTS 3

// Camera matrices
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;

// Light matrices (one per light)
uniform mat4 light_matrices[MAX_LIGHTS];

// Vertex attributes
in vec3 in_position;
in vec3 in_normal;

// Outputs to fragment shader
out vec3 v_position;                    // World space position
out vec3 v_normal;                      // World space normal
out vec4 v_light_space_pos[MAX_LIGHTS]; // Position in each light's space

void main() {
    // Transform to world space
    vec4 world_pos = model * vec4(in_position, 1.0);
    v_position = world_pos.xyz;
    v_normal = mat3(model) * in_normal;  // Normal matrix (simplified)

    // Transform to each light's clip space for shadow mapping
    for (int i = 0; i < MAX_LIGHTS; i++) {
        v_light_space_pos[i] = light_matrices[i] * world_pos;
    }

    // Transform to camera's clip space for rendering
    gl_Position = projection * view * world_pos;
}
