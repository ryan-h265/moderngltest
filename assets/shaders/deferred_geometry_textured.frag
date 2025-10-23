#version 410

// Deferred Rendering - Geometry Pass Fragment Shader (Textured Models)
// Writes textured geometric properties to G-Buffer

// Texture samplers
uniform sampler2D baseColorTexture;
uniform sampler2D normalTexture;
uniform sampler2D metallicRoughnessTexture;
uniform sampler2D emissiveTexture;

// Texture flags
uniform bool hasBaseColorTexture;
uniform bool hasNormalTexture;
uniform bool hasMetallicRoughnessTexture;
uniform bool hasEmissiveTexture;

// Material fallback properties
uniform vec4 baseColorFactor;
uniform vec3 emissiveFactor;

// Inputs from vertex shader
in vec3 v_world_position;  // World space position
in vec3 v_view_position;   // View space position
in vec3 v_world_normal;    // World space normal
in vec3 v_view_normal;     // View space normal
in vec2 v_texcoord;        // Texture coordinates
in mat3 v_TBN;             // Tangent-Bitangent-Normal matrix (view space)

// G-Buffer outputs (Multiple Render Targets)
layout(location = 0) out vec3 gPosition;  // View space position (for SSAO)
layout(location = 1) out vec3 gNormal;    // View space normal (for SSAO)
layout(location = 2) out vec4 gAlbedo;    // Base color (RGB) + AO (A, unused = 1.0)
layout(location = 3) out vec2 gMaterial;  // Metallic (R) + Roughness (G)
layout(location = 4) out vec3 gEmissive;  // Emissive color (self-illumination)

void main() {
    // Store view space position (required for SSAO)
    gPosition = v_view_position;

    // Calculate normal (with optional normal mapping)
    vec3 normal;
    if (hasNormalTexture) {
        // Sample normal map (tangent space, stored as [0,1])
        vec3 normal_sample = texture(normalTexture, v_texcoord).rgb;
        // Convert from [0,1] to [-1,1]
        normal_sample = normal_sample * 2.0 - 1.0;

        // Transform from tangent space to view space using TBN matrix
        normal = normalize(v_TBN * normal_sample);
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

    // Sample emissive contribution (stored separately, not affected by lighting)
    vec3 emissive = emissiveFactor;
    if (hasEmissiveTexture) {
        emissive *= texture(emissiveTexture, v_texcoord).rgb;
    }

    // Sample metallic/roughness for PBR
    float metallic = 0.0;   // Default: non-metallic (dielectric)
    float roughness = 0.5;  // Default: medium roughness
    if (hasMetallicRoughnessTexture) {
        // Metallic-roughness texture: R=unused, G=roughness, B=metallic (glTF 2.0 standard)
        vec3 mr = texture(metallicRoughnessTexture, v_texcoord).rgb;
        metallic = mr.b;
        roughness = mr.g;
    }

    // Store albedo (base color only, no emissive) + ambient occlusion (A, currently unused = 1.0)
    gAlbedo = vec4(albedo.rgb, 1.0);

    // Store PBR material properties
    gMaterial = vec2(metallic, roughness);

    // Store emissive separately (will be added after lighting to create glow effect)
    gEmissive = emissive;
}
