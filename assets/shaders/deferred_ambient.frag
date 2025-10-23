#version 410

// Deferred Rendering - Ambient Lighting Fragment Shader
// Adds base ambient lighting with optional SSAO

// G-Buffer textures
uniform sampler2D gPosition;
uniform sampler2D gNormal;
uniform sampler2D gAlbedo;

// SSAO texture (optional)
uniform sampler2D ssaoTexture;
uniform bool ssaoEnabled;
uniform float ssaoIntensity;

// Ambient strength
uniform float ambient_strength;

// Input from vertex shader
in vec2 v_texcoord;

// Output
out vec4 f_color;

void main() {
    // Sample albedo + baked AO from G-Buffer
    vec4 albedo_ao = texture(gAlbedo, v_texcoord);
    vec3 base_color = albedo_ao.rgb;
    float baked_ao = albedo_ao.a;  // Baked occlusion from GLTF texture (1.0 if none)
    vec3 normal = texture(gNormal, v_texcoord).rgb;

    // Early exit for background pixels (no geometry)
    if (length(normal) < 0.1) {
        // Background color (dark blue)
        f_color = vec4(0.1, 0.1, 0.15, 1.0);
        return;
    }

    // Get SSAO occlusion factor (screen-space, dynamic)
    float ssao = 1.0;
    if (ssaoEnabled) {
        float ssao_sample = texture(ssaoTexture, v_texcoord).r;
        // Mix between full occlusion and no occlusion
        ssao = mix(1.0 - ssaoIntensity, 1.0, ssao_sample);
    }

    // Combine baked AO and SSAO (multiply for best results)
    // - Baked AO: High-quality, fine detail (crevices, seams)
    // - SSAO: Dynamic, large-scale occlusion (nearby geometry)
    float combined_ao = baked_ao * ssao;

    // Ambient lighting modulated by combined AO
    vec3 ambient = ambient_strength * base_color * combined_ao;

    f_color = vec4(ambient, 1.0);
}
