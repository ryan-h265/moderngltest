#version 410

// Deferred Rendering - Geometry Pass Fragment Shader
// Writes geometric properties to G-Buffer (Multiple Render Targets)

// Material properties
uniform vec3 object_color;
uniform vec4 previewTint = vec4(0.0, 0.0, 0.0, 0.0);  // Preview tint (RGB) + blend factor (A)

// Inputs from vertex shader
in vec3 v_world_position;  // World space position
in vec3 v_view_position;   // View space position
in vec3 v_world_normal;    // World space normal
in vec3 v_view_normal;     // View space normal

// G-Buffer outputs (Multiple Render Targets)
// NOTE: Position and Normal are in VIEW SPACE for SSAO compatibility
layout(location = 0) out vec3 gPosition;  // View space position (for SSAO)
layout(location = 1) out vec3 gNormal;    // View space normal (for SSAO)
layout(location = 2) out vec4 gAlbedo;    // Base color (RGB) + AO (A, unused = 1.0)
layout(location = 3) out vec2 gMaterial;  // Metallic (R) + Roughness (G)
layout(location = 4) out vec3 gEmissive;  // Emissive color (self-illumination)

void main() {
    // Store view space position (required for SSAO)
    gPosition = v_view_position;

    // Store view space normalized normal (required for SSAO)
    gNormal = normalize(v_view_normal);

    // Store albedo (base color) + ambient occlusion (unused = 1.0)
    // Apply preview tint if active (previewTint.a > 0)
    vec3 final_color = object_color;
    if (previewTint.a > 0.0) {
        final_color = mix(object_color, previewTint.rgb, previewTint.a);
    }
    gAlbedo = vec4(final_color, 1.0);

    // Primitives use default PBR values (non-metallic, medium roughness)
    gMaterial = vec2(0.0, 0.5);  // metallic = 0, roughness = 0.5

    // Primitives have no emissive component
    gEmissive = vec3(0.0, 0.0, 0.0);
}
