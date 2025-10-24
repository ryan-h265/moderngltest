#version 410

// Bloom composite pass. Adds the blurred emissive light back onto the lighting
// buffer with optional intensity and tint controls.

uniform sampler2D bloomTexture;
uniform float intensity;
uniform vec3 tint;

in vec2 v_texcoord;
out vec4 fragColor;

void main()
{
    vec3 bloom = texture(bloomTexture, v_texcoord).rgb * intensity * tint;
    fragColor = vec4(bloom, 1.0);
}

