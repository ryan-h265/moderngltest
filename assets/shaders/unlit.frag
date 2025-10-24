#version 410

// Unlit Fragment Shader (KHR_materials_unlit)
// Outputs base color only, bypasses all lighting calculations

// Texture samplers
uniform sampler2D baseColorTexture;

// Texture flags
uniform bool hasBaseColorTexture;

// Texture transforms (KHR_texture_transform) - 3x3 matrices
uniform mat3 baseColorTransform;

// Material properties
uniform vec4 baseColorFactor;

// Alpha transparency
uniform int alphaMode;      // 0=OPAQUE, 1=MASK, 2=BLEND
uniform float alphaCutoff;  // Threshold for MASK mode

// Inputs from vertex shader
in vec3 v_view_position;
in vec3 v_view_normal;
in vec2 v_texcoord;
in vec3 v_color;  // Vertex color

// G-Buffer outputs (Multiple Render Targets)
layout(location = 0) out vec3 gPosition;  // View space position (for SSAO)
layout(location = 1) out vec3 gNormal;    // View space normal (for SSAO)
layout(location = 2) out vec4 gAlbedo;    // Base color (RGB) + AO (A)
layout(location = 3) out vec2 gMaterial;  // Metallic (R) + Roughness (G)
layout(location = 4) out vec3 gEmissive;  // Emissive color (self-illumination)

void main() {
    // Sample base color
    vec4 albedo;
    if (hasBaseColorTexture) {
        // Apply texture transform to UV coordinates
        vec2 transformed_uv = (baseColorTransform * vec3(v_texcoord, 1.0)).xy;
        albedo = texture(baseColorTexture, transformed_uv);
        albedo *= baseColorFactor;
    } else {
        albedo = baseColorFactor;
    }

    // Multiply by vertex color (GLTF COLOR_0 attribute)
    albedo.rgb *= v_color;

    // Alpha testing for MASK mode
    if (alphaMode == 1) {  // MASK mode
        if (albedo.a < alphaCutoff) {
            discard;
        }
    }

    // Store position and normal for depth/SSAO
    gPosition = v_view_position;
    gNormal = normalize(v_view_normal);

    // For unlit: output color as emissive (bypasses all lighting)
    // This makes the material self-lit at full brightness
    gAlbedo = vec4(0.0, 0.0, 0.0, 1.0);  // Black albedo (receives no lighting)
    gMaterial = vec2(0.0, 1.0);  // Non-metallic, full roughness (irrelevant for unlit)
    gEmissive = albedo.rgb;  // Full color as emissive (100% brightness, unaffected by lights)
}
