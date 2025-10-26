#version 410

uniform vec3 color;
uniform float alpha;

out vec4 fragColor;

void main() {
    fragColor = vec4(color, alpha);
}
