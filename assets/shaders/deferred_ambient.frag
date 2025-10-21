#version 410

// Deferred Rendering - Ambient Lighting Fragment Shader
// Adds base ambient lighting (not affected by shadows)

// G-Buffer textures
uniform sampler2D gPosition;
uniform sampler2D gNormal;
uniform sampler2D gAlbedo;

// Ambient strength
uniform float ambient_strength;

// Input from vertex shader
in vec2 v_texcoord;

// Output
out vec4 f_color;

void main() {
    // Sample albedo from G-Buffer
    vec3 base_color = texture(gAlbedo, v_texcoord).rgb;
    vec3 normal = texture(gNormal, v_texcoord).rgb;

    // Early exit for background pixels (no geometry)
    if (length(normal) < 0.1) {
        // Background color (dark blue)
        f_color = vec4(0.1, 0.1, 0.15, 1.0);
        return;
    }

    // Ambient lighting (constant base illumination)
    vec3 ambient = ambient_strength * base_color;

    f_color = vec4(ambient, 1.0);
}
