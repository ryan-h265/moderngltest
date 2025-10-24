#version 410

uniform vec3 override_color;

out vec4 f_color;

void main() {
    f_color = vec4(override_color, 1.0);
}
