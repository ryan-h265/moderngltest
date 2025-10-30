#version 410

/**
 * Simple Cubemap Skybox Shader
 *
 * Renders a static cubemap texture for traditional skybox rendering.
 */

in vec3 v_texcoord;
out vec4 fragColor;

uniform samplerCube skybox_texture;
uniform float intensity;

void main() {
    vec3 color = texture(skybox_texture, v_texcoord).rgb;
    color *= intensity;

    // Gamma correction
    color = pow(color, vec3(1.0 / 2.2));

    fragColor = vec4(color, 1.0);
}
