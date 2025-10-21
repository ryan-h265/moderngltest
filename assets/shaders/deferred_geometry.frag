#version 410

// Deferred Rendering - Geometry Pass Fragment Shader
// Writes geometric properties to G-Buffer (Multiple Render Targets)

// Material properties
uniform vec3 object_color;

// Inputs from vertex shader
in vec3 v_position;  // World space position
in vec3 v_normal;    // World space normal

// G-Buffer outputs (Multiple Render Targets)
layout(location = 0) out vec3 gPosition;  // World position
layout(location = 1) out vec3 gNormal;    // World normal
layout(location = 2) out vec4 gAlbedo;    // Base color + specular

void main() {
    // Store world space position
    gPosition = v_position;

    // Store normalized normal
    gNormal = normalize(v_normal);

    // Store albedo (base color) and specular intensity
    // RGB = object color, A = specular intensity (currently hardcoded to 0.3)
    gAlbedo = vec4(object_color, 0.3);
}
