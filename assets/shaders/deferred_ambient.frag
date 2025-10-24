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

// Skybox uniforms
uniform bool skybox_enabled;
uniform samplerCube skybox_texture;
uniform mat4 inverse_view;
uniform mat4 inverse_projection;
uniform float skybox_intensity;
uniform mat4 skybox_rotation;

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
        if (skybox_enabled) {
            vec2 ndc = v_texcoord * 2.0 - 1.0;
            vec4 clip = vec4(ndc, 1.0, 1.0);
            vec4 view_dir = inverse_projection * clip;
            vec3 dir = normalize(view_dir.xyz / view_dir.w);
            vec3 world_dir = mat3(inverse_view) * dir;
            vec3 rotated_dir = mat3(skybox_rotation) * world_dir;
            vec3 sky_color = texture(skybox_texture, rotated_dir).rgb * skybox_intensity;
            f_color = vec4(sky_color, 1.0);
        } else {
            f_color = vec4(0.1, 0.1, 0.15, 1.0);
        }
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
