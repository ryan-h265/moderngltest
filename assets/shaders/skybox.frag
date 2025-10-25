#version 410

in vec3 v_texcoord;

uniform samplerCube skybox_texture;
uniform float intensity;

out vec4 f_color;

void main() {
    // DEBUG: Rainbow skybox based on direction
    vec3 dir = normalize(v_texcoord);

    // Create rainbow colors based on direction
    // Map x, y, z from [-1, 1] to [0, 1] for RGB
    vec3 rainbow = vec3(
        dir.x * 0.5 + 0.5,  // Red channel
        dir.y * 0.5 + 0.5,  // Green channel
        dir.z * 0.5 + 0.5   // Blue channel
    );

    f_color = vec4(rainbow * intensity, 1.0);

    // Original skybox texture sampling (commented out for debugging):
    // vec3 color = texture(skybox_texture, dir).rgb * intensity;
    // f_color = vec4(color, 1.0);
}
