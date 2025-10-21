#version 410

// Deferred Rendering - Geometry Pass Fragment Shader
// Writes geometric properties to G-Buffer (Multiple Render Targets)

// Material properties
uniform vec3 object_color;

// Inputs from vertex shader
in vec3 v_world_position;  // World space position
in vec3 v_view_position;   // View space position
in vec3 v_world_normal;    // World space normal
in vec3 v_view_normal;     // View space normal

// G-Buffer outputs (Multiple Render Targets)
// NOTE: Position and Normal are in VIEW SPACE for SSAO compatibility
// World-space can be reconstructed if needed using inverse view matrix
layout(location = 0) out vec3 gPosition;  // View space position (for SSAO)
layout(location = 1) out vec3 gNormal;    // View space normal (for SSAO)
layout(location = 2) out vec4 gAlbedo;    // Base color + specular

void main() {
    // Store view space position (required for SSAO)
    gPosition = v_view_position;

    // Store view space normalized normal (required for SSAO)
    gNormal = normalize(v_view_normal);

    // Store albedo (base color) and specular intensity
    // RGB = object color, A = specular intensity (currently hardcoded to 0.3)
    gAlbedo = vec4(object_color, 0.3);
}
