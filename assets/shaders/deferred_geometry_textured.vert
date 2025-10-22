#version 410

// Deferred Rendering - Geometry Pass Vertex Shader (Textured Models)
// Supports UV coordinates for texture mapping

// Camera matrices
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;

// Vertex attributes
in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord;

// Outputs to fragment shader
out vec3 v_world_position;  // World space position
out vec3 v_view_position;   // View space position
out vec3 v_world_normal;    // World space normal
out vec3 v_view_normal;     // View space normal
out vec2 v_texcoord;        // Texture coordinates

void main() {
    // Transform to world space
    vec4 world_pos = model * vec4(in_position, 1.0);
    v_world_position = world_pos.xyz;

    // Transform to view space
    vec4 view_pos = view * world_pos;
    v_view_position = view_pos.xyz;

    // Transform normal to world space (simplified - assumes uniform scaling)
    v_world_normal = mat3(model) * in_normal;

    // Transform normal to view space
    v_view_normal = mat3(view) * v_world_normal;

    // Pass through texture coordinates
    v_texcoord = in_texcoord;

    // Transform to clip space for rendering
    gl_Position = projection * view_pos;
}
