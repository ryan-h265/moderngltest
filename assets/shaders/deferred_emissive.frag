#version 410

// Deferred Rendering - Emissive Pass Fragment Shader
// Outputs emissive contribution (self-illumination, independent of lighting)

// G-Buffer textures
uniform sampler2D gEmissive;
uniform sampler2D gPosition;

// Camera and fog
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

void main() {
    // Sample emissive contribution from G-Buffer
    vec3 emissive = texture(gEmissive, v_texcoord).rgb;

    // Early out if nothing to emit
    if (length(emissive) < 1e-4) {
        f_color = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    vec3 view_position = texture(gPosition, v_texcoord).rgb;
    vec3 world_position = (inverse_view * vec4(view_position, 1.0)).xyz;

    float fog_factor = 0.0;
    if (fog_enabled) {
        float fog_range = max(fog_end_distance - fog_start_distance, 0.001);
        float distance_to_camera = length(camera_pos - world_position);
        float distance_factor = clamp((distance_to_camera - fog_start_distance) / fog_range, 0.0, 1.0);

        float height_offset = max(world_position.y - fog_base_height, 0.0);
        float height_factor = exp(-height_offset * fog_height_falloff);

        vec3 animated_pos = world_position * fog_noise_scale + fog_wind_direction * (fog_time * fog_noise_speed);
        float trig_noise = sin(animated_pos.x) + sin(animated_pos.y * 1.3 + animated_pos.z * 0.7) + sin(animated_pos.z * 1.7 - animated_pos.x * 0.5);
        trig_noise = trig_noise / 3.0;
        float noise_normalized = trig_noise * 0.5 + 0.5;
        float variation = mix(1.0 - fog_noise_strength, 1.0 + fog_noise_strength, noise_normalized);

        float fog_density_world = fog_density * variation * height_factor;
        fog_factor = clamp((1.0 - exp(-distance_to_camera * fog_density_world)) * distance_factor, 0.0, 1.0);
    }

    vec3 final_emissive = emissive * (1.0 - fog_factor);

    // Output emissive color (will be additively blended onto accumulated lighting)
    f_color = vec4(final_emissive, 1.0);
}
