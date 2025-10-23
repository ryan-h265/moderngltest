#version 410

// Deferred Rendering - Geometry Pass Fragment Shader (Textured Models)
// Writes textured geometric properties to G-Buffer

// Texture samplers
uniform sampler2D baseColorTexture;
uniform sampler2D normalTexture;
uniform sampler2D metallicRoughnessTexture;
uniform sampler2D emissiveTexture;
uniform sampler2D occlusionTexture;

// Texture flags
uniform bool hasBaseColorTexture;
uniform bool hasNormalTexture;
uniform bool hasMetallicRoughnessTexture;
uniform bool hasEmissiveTexture;
uniform bool hasOcclusionTexture;

// Texture transforms (KHR_texture_transform) - 3x3 matrices
uniform mat3 baseColorTransform;
uniform mat3 normalTransform;
uniform mat3 metallicRoughnessTransform;
uniform mat3 emissiveTransform;
uniform mat3 occlusionTransform;

// Material fallback properties
uniform vec4 baseColorFactor;
uniform vec3 emissiveFactor;
uniform float occlusionStrength;  // Strength of baked AO (0.0 = none, 1.0 = full)
uniform float normalScale;        // Normal map intensity

// Alpha transparency
uniform int alphaMode;      // 0=OPAQUE, 1=MASK, 2=BLEND
uniform float alphaCutoff;  // Threshold for MASK mode (default 0.5)

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
        // Apply texture transform to UV coordinates
        vec2 transformed_uv = (normalTransform * vec3(v_texcoord, 1.0)).xy;
        // Sample normal map (tangent space, stored as [0,1])
        vec3 normal_sample = texture(normalTexture, transformed_uv).rgb;
        // Convert from [0,1] to [-1,1]
        normal_sample = normal_sample * 2.0 - 1.0;

        // Apply normal scale to XY components (tangent-space perturbation)
        normal_sample.xy *= normalScale;

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
        // Apply texture transform to UV coordinates
        vec2 transformed_uv = (baseColorTransform * vec3(v_texcoord, 1.0)).xy;
        albedo = texture(baseColorTexture, transformed_uv);
        // Apply color factor
        albedo *= baseColorFactor;
    } else {
        // Use solid color from factor
        albedo = baseColorFactor;
    }

    // Alpha testing for MASK mode (cutout transparency)
    if (alphaMode == 1) {  // MASK mode
        if (albedo.a < alphaCutoff) {
            discard;  // Discard fragment, creates cutout effect (for vegetation, fences, etc.)
        }
    }

    // Sample emissive contribution (stored separately, not affected by lighting)
    vec3 emissive = emissiveFactor;
    if (hasEmissiveTexture) {
        // Apply texture transform to UV coordinates
        vec2 transformed_uv = (emissiveTransform * vec3(v_texcoord, 1.0)).xy;
        emissive *= texture(emissiveTexture, transformed_uv).rgb;
    }

    // Sample occlusion (baked AO from GLTF, stored in RED channel per spec)
    float occlusion = 1.0;
    if (hasOcclusionTexture) {
        // Apply texture transform to UV coordinates
        vec2 transformed_uv = (occlusionTransform * vec3(v_texcoord, 1.0)).xy;
        float ao_sample = texture(occlusionTexture, transformed_uv).r;
        // Apply strength: lerp between no occlusion (1.0) and full occlusion
        occlusion = mix(1.0, ao_sample, occlusionStrength);
    }

    // Sample metallic/roughness for PBR
    float metallic = 0.0;   // Default: non-metallic (dielectric)
    float roughness = 0.5;  // Default: medium roughness
    if (hasMetallicRoughnessTexture) {
        // Apply texture transform to UV coordinates
        vec2 transformed_uv = (metallicRoughnessTransform * vec3(v_texcoord, 1.0)).xy;
        // Metallic-roughness texture: R=unused, G=roughness, B=metallic (glTF 2.0 standard)
        vec3 mr = texture(metallicRoughnessTexture, transformed_uv).rgb;
        metallic = mr.b;
        roughness = mr.g;
    }

    // Store albedo (base color) + baked ambient occlusion (A channel)
    gAlbedo = vec4(albedo.rgb, occlusion);

    // Store PBR material properties
    gMaterial = vec2(metallic, roughness);

    // Store emissive separately (will be added after lighting to create glow effect)
    gEmissive = emissive;
}
