#version 410

in vec3 in_position;

uniform mat4 projection;
uniform mat4 view;
uniform mat4 rotation;

out vec3 v_texcoord;

void main() {
    vec4 local_position = rotation * vec4(in_position, 1.0);
    v_texcoord = local_position.xyz;

    vec4 clip_position = projection * view * local_position;
    gl_Position = vec4(clip_position.xy, clip_position.w, clip_position.w);
}
