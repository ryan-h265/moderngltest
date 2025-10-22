#version 410

// Deferred Rendering - Geometry Pass Fragment Shader (Textured Models)
// Writes textured geometric properties to G-Buffer

// Texture samplers
uniform sampler2D baseColorTexture;
uniform sampler2D normalTexture;
uniform sampler2D metallicRoughnessTexture;

// Texture flags
uniform bool hasBaseColorTexture;
uniform bool hasNormalTexture;
uniform bool hasMetallicRoughnessTexture;

// Material fallback properties
uniform vec4 baseColorFactor;

// Inputs from vertex shader
in vec3 v_world_position;  // World space position
in vec3 v_view_position;   // View space position
in vec3 v_world_normal;    // World space normal
in vec3 v_view_normal;     // View space normal
in vec2 v_texcoord;        // Texture coordinates

// G-Buffer outputs (Multiple Render Targets)
layout(location = 0) out vec3 gPosition;  // View space position (for SSAO)
layout(location = 1) out vec3 gNormal;    // View space normal (for SSAO)
layout(location = 2) out vec4 gAlbedo;    // Base color + specular

void main() {
    // Store view space position (required for SSAO)
    gPosition = v_view_position;

    // Calculate normal (with optional normal mapping)
    vec3 normal;
    if (hasNormalTexture) {
        // Sample normal map (tangent space)
        vec3 normal_sample = texture(normalTexture, v_texcoord).rgb * 2.0 - 1.0;

        // For now, just use the geometric normal
        // TODO: Implement proper tangent-space normal mapping with TBN matrix
        normal = normalize(v_view_normal);
    } else {
        // Use geometric normal
        normal = normalize(v_view_normal);
    }

    gNormal = normal;

    // Sample base color
    vec4 albedo;
    if (hasBaseColorTexture) {
        albedo = texture(baseColorTexture, v_texcoord);
        // Apply color factor
        albedo *= baseColorFactor;
    } else {
        // Use solid color from factor
        albedo = baseColorFactor;
    }

    // Sample metallic/roughness if available (for specular calculation)
    float specular = 0.3;  // Default specular
    if (hasMetallicRoughnessTexture) {
        // Metallic-roughness texture: R=unused, G=roughness, B=metallic
        vec3 mr = texture(metallicRoughnessTexture, v_texcoord).rgb;
        float metallic = mr.b;
        float roughness = mr.g;

        // Convert roughness to specular (inverse relationship)
        specular = 1.0 - roughness;

        // Metallic surfaces get higher specular
        specular = mix(specular * 0.5, specular, metallic);
    }

    // Store albedo and specular
    gAlbedo = vec4(albedo.rgb, specular);
}
