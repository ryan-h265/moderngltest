#version 410

// UI Sprite Fragment Shader
// Samples HUD icon textures with optional tinting.

in vec2 v_uv;
in vec4 v_color;

out vec4 fragColor;

uniform sampler2D sprite_texture;

void main(){
    vec4 texColor = texture(sprite_texture, v_uv);
    fragColor = texColor * v_color;
    if(fragColor.a <= 0.0){
        discard;
    }
}
