#version 410

// Deferred Rendering - Geometry Pass Vertex Shader
// Transforms vertices and passes data to fragment shader

// Camera matrices
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;

// Vertex attributes
in vec3 in_position;
in vec3 in_normal;

// Outputs to fragment shader
out vec3 v_position;  // World space position
out vec3 v_normal;    // World space normal

void main() {
    // Transform to world space
    vec4 world_pos = model * vec4(in_position, 1.0);
    v_position = world_pos.xyz;

    // Transform normal to world space (simplified - assumes uniform scaling)
    v_normal = mat3(model) * in_normal;

    // Transform to clip space for rendering
    gl_Position = projection * view * world_pos;
}
