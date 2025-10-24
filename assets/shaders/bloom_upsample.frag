#version 410

// Bloom upsample pass. Reconstructs the blurred glow by combining the current
// mip level with the next smaller level using a small tent filter.

uniform sampler2D baseTexture;
uniform sampler2D bloomTexture;
uniform float filterRadius;
uniform bool hasBloomTexture;

in vec2 v_texcoord;
out vec3 fragColor;

vec3 sampleTent(sampler2D tex, vec2 uv, float radius)
{
    vec2 texelSize = 1.0 / vec2(textureSize(tex, 0));
    vec2 offset = texelSize * radius;

    vec3 result = texture(tex, uv).rgb * 0.5;
    result += texture(tex, uv + vec2(offset.x, 0.0)).rgb * 0.125;
    result += texture(tex, uv - vec2(offset.x, 0.0)).rgb * 0.125;
    result += texture(tex, uv + vec2(0.0, offset.y)).rgb * 0.125;
    result += texture(tex, uv - vec2(0.0, offset.y)).rgb * 0.125;
    return result;
}

void main()
{
    vec3 base = texture(baseTexture, v_texcoord).rgb;
    vec3 bloom = vec3(0.0);

    if (hasBloomTexture)
    {
        bloom = sampleTent(bloomTexture, v_texcoord, filterRadius);
    }

    fragColor = base + bloom;
}

