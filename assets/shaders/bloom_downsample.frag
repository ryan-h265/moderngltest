#version 410

// Bloom downsample pass. Extracts bright pixels using a soft threshold and
// downsamples the emissive buffer to progressively smaller mip levels.

uniform sampler2D sourceTexture;
uniform float threshold;
uniform float softKnee;
uniform bool useThreshold;

in vec2 v_texcoord;
out vec3 fragColor;

vec3 sampleBox(vec2 uv, vec2 texelSize)
{
    vec3 c = texture(sourceTexture, uv).rgb * 4.0;
    c += texture(sourceTexture, uv + vec2(texelSize.x, 0.0)).rgb;
    c += texture(sourceTexture, uv - vec2(texelSize.x, 0.0)).rgb;
    c += texture(sourceTexture, uv + vec2(0.0, texelSize.y)).rgb;
    c += texture(sourceTexture, uv - vec2(0.0, texelSize.y)).rgb;
    return c * 0.125; // Normalise (total weight = 8)
}

vec3 applyThreshold(vec3 color)
{
    float brightness = max(max(color.r, color.g), color.b);
    if (brightness <= 0.0)
    {
        return vec3(0.0);
    }

    float knee = threshold * softKnee + 1e-5;
    float soft = brightness - threshold + knee;
    soft = clamp(soft, 0.0, 2.0 * knee);
    soft = soft * soft / (4.0 * knee + 1e-5);
    float contribution = max(brightness - threshold, soft);

    return max(color * (contribution / max(brightness, 1e-5)), 0.0);
}

void main()
{
    vec2 texelSize = 1.0 / vec2(textureSize(sourceTexture, 0));
    vec3 color = sampleBox(v_texcoord, texelSize);

    if (useThreshold)
    {
        color = applyThreshold(color);
    }

    fragColor = color;
}

