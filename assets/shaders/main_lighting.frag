#version 410

// Main Lighting Fragment Shader
// Multi-light with shadow mapping and PCF soft shadows

#define MAX_LIGHTS 3

// Light properties
uniform vec3 light_positions[MAX_LIGHTS];
uniform vec3 light_colors[MAX_LIGHTS];
uniform float light_intensities[MAX_LIGHTS];

// Camera and object
uniform vec3 camera_pos;
uniform vec3 object_color;

// Shadow maps
uniform sampler2D shadow_maps[MAX_LIGHTS];

// Fog parameters
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

// Inputs from vertex shader
in vec3 v_position;
in vec3 v_normal;
in vec4 v_light_space_pos[MAX_LIGHTS];

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
    trig_noise = trig_noise / 3.0; // [-1,1]
    float noise_normalized = trig_noise * 0.5 + 0.5; // [0,1]
    float variation = mix(1.0 - fog_noise_strength, 1.0 + fog_noise_strength, noise_normalized);

    float density = fog_density * variation * height_factor;
    float fog_amount = 1.0 - exp(-distance_to_camera * density);
    return clamp(fog_amount * distance_factor, 0.0, 1.0);
}

/**
 * Calculate shadow factor for a given light
 * Returns: 0.0 = no shadow, 1.0 = full shadow
 */
float calculate_shadow(int light_index, vec4 light_space_pos, sampler2D shadow_map) {
    // Perspective divide to get normalized device coordinates
    vec3 proj_coords = light_space_pos.xyz / light_space_pos.w;

    // Transform from [-1,1] to [0,1] range for texture coordinates
    proj_coords = proj_coords * 0.5 + 0.5;

    // Outside shadow map bounds = no shadow
    if (proj_coords.z > 1.0 || proj_coords.x < 0.0 || proj_coords.x > 1.0
        || proj_coords.y < 0.0 || proj_coords.y > 1.0) {
        return 0.0;
    }

    // Get depth from shadow map
    float closest_depth = texture(shadow_map, proj_coords.xy).r;
    float current_depth = proj_coords.z;

    // Bias to prevent shadow acne (self-shadowing artifacts)
    float bias = 0.005;

    // PCF (Percentage Closer Filtering) for soft shadows
    // Sample 3x3 grid around the fragment
    float shadow = 0.0;
    vec2 texel_size = 1.0 / textureSize(shadow_map, 0);
    for(int x = -1; x <= 1; ++x) {
        for(int y = -1; y <= 1; ++y) {
            float pcf_depth = texture(shadow_map, proj_coords.xy + vec2(x, y) * texel_size).r;
            shadow += current_depth - bias > pcf_depth ? 1.0 : 0.0;
        }
    }
    shadow /= 9.0;  // Average of 9 samples

    return shadow;
}

void main() {
    vec3 normal = normalize(v_normal);
    vec3 view_dir = normalize(camera_pos - v_position);

    // Ambient lighting - base illumination not affected by shadows
    float ambient_strength = 0.2;
    vec3 ambient = ambient_strength * object_color;

    // Accumulate lighting from all lights
    vec3 total_lighting = vec3(0.0);

    for (int i = 0; i < MAX_LIGHTS; i++) {
        vec3 light_dir = normalize(light_positions[i] - v_position);

        // Diffuse lighting (Lambert)
        float diff = max(dot(normal, light_dir), 0.0);
        vec3 diffuse = diff * object_color * light_colors[i];

        // Specular lighting (Blinn-Phong)
        vec3 halfway_dir = normalize(light_dir + view_dir);
        float spec = pow(max(dot(normal, halfway_dir), 0.0), 32.0);
        vec3 specular = vec3(0.3) * spec * light_colors[i];

        // Calculate shadow for this light
        float shadow = calculate_shadow(i, v_light_space_pos[i], shadow_maps[i]);

        // Add this light's contribution (attenuated by intensity and shadow)
        // Shadow factor reduces diffuse and specular (but not ambient)
        total_lighting += light_intensities[i] * (1.0 - shadow) * (diffuse + specular);
    }

    // Combine ambient + all light contributions
    vec3 final_color = ambient + total_lighting;

    float fog_factor = compute_fog_factor(v_position);
    final_color = mix(final_color, fog_color, fog_factor);

    f_color = vec4(final_color, 1.0);
}
