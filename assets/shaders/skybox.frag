#version 410

in vec3 v_texcoord;

uniform samplerCube skybox_texture;
uniform float intensity;

out vec4 f_color;

void main() {
    vec3 color = texture(skybox_texture, normalize(v_texcoord)).rgb * intensity;
    f_color = vec4(color, 1.0);
}
