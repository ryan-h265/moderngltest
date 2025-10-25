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

// Camera + fog uniforms
uniform mat4 inverse_view;
uniform vec3 camera_pos;
uniform bool fog_enabled;
uniform vec3 fog_color;
uniform float fog_density;
uniform float fog_start_distance;
uniform float fog_end_distance;
uniform float fog_base_height;
uniform float fog_height_falloff;
uniform float fog_noise_scale;
uniform float fog_noise_strength;
uniform float fog_noise_speed;
uniform vec3 fog_wind_direction;
uniform float fog_time;

// Input from vertex shader
in vec2 v_texcoord;

// Output
out vec4 f_color;

float compute_fog_factor(vec3 world_pos) {
    if (!fog_enabled) {
        return 0.0;
    }

    float distance_to_camera = length(camera_pos - world_pos);
    float range = max(fog_end_distance - fog_start_distance, 0.001);
    float distance_factor = clamp((distance_to_camera - fog_start_distance) / range, 0.0, 1.0);

    float height_offset = max(world_pos.y - fog_base_height, 0.0);
    float height_factor = exp(-height_offset * fog_height_falloff);

    vec3 animated_pos = world_pos * fog_noise_scale + fog_wind_direction * (fog_time * fog_noise_speed);
    float trig_noise = sin(animated_pos.x) + sin(animated_pos.y * 1.3 + animated_pos.z * 0.7) + sin(animated_pos.z * 1.7 - animated_pos.x * 0.5);
    trig_noise = trig_noise / 3.0;
    float noise_normalized = trig_noise * 0.5 + 0.5;
    float variation = mix(1.0 - fog_noise_strength, 1.0 + fog_noise_strength, noise_normalized);

    float density = fog_density * variation * height_factor;
    float fog_amount = 1.0 - exp(-distance_to_camera * density);
    return clamp(fog_amount * distance_factor, 0.0, 1.0);
}

void main() {
    // Sample albedo + baked AO from G-Buffer
    vec3 view_position = texture(gPosition, v_texcoord).rgb;
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

    vec3 world_position = (inverse_view * vec4(view_position, 1.0)).xyz;
    float fog_factor = compute_fog_factor(world_position);
    vec3 final_color = mix(ambient, fog_color, fog_factor);

    f_color = vec4(final_color, 1.0);
}
