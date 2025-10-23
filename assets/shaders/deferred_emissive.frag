#version 410

// Deferred Rendering - Emissive Pass Fragment Shader
// Outputs emissive contribution (self-illumination, independent of lighting)

// G-Buffer emissive texture
uniform sampler2D gEmissive;

// Input from vertex shader
in vec2 v_texcoord;

// Output
out vec4 f_color;

void main() {
    // Sample emissive contribution from G-Buffer
    vec3 emissive = texture(gEmissive, v_texcoord).rgb;

    // Output emissive color (will be additively blended onto accumulated lighting)
    f_color = vec4(emissive, 1.0);
}
