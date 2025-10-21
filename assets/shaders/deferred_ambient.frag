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
    // Sample albedo from G-Buffer
    vec3 base_color = texture(gAlbedo, v_texcoord).rgb;
    vec3 normal = texture(gNormal, v_texcoord).rgb;

    // Early exit for background pixels (no geometry)
    if (length(normal) < 0.1) {
        // Background color (dark blue)
        f_color = vec4(0.1, 0.1, 0.15, 1.0);
        return;
    }

    // Get SSAO occlusion factor
    float occlusion = 1.0;
    if (ssaoEnabled) {
        float ao = texture(ssaoTexture, v_texcoord).r;
        // Mix between full occlusion (0.0) and no occlusion (1.0)
        occlusion = mix(1.0 - ssaoIntensity, 1.0, ao);
    }

    // Ambient lighting (modulated by SSAO)
    vec3 ambient = ambient_strength * base_color * occlusion;

    f_color = vec4(ambient, 1.0);
}
