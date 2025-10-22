#version 330 core

in vec2 uv;
in vec2 pixcoord;
in vec4 offset[3];

out vec4 fragColor;

uniform sampler2D edgesTex;
uniform sampler2D areaTex;
uniform sampler2D searchTex;

// SMAA Settings
#define SMAA_MAX_SEARCH_STEPS 16
#define SMAA_AREATEX_MAX_DISTANCE 16
#define SMAA_AREATEX_PIXEL_SIZE (1.0 / vec2(160.0, 560.0))
#define SMAA_AREATEX_SUBTEX_SIZE (1.0 / 7.0)
#define SMAA_SEARCHTEX_SIZE vec2(64.0, 16.0)
#define SMAA_SEARCHTEX_PACKED_SIZE vec2(64.0, 16.0)

// SMAA_RT_METRICS is passed via vertex shader as pixcoord and offsets

/**
 * Search for pattern length using search texture
 */
float SMAASearchLength(sampler2D searchTex, vec2 e, float offset) {
    // The texture is flipped vertically, with left and right cases taking half
    // of the space horizontally:
    vec2 scale = SMAA_SEARCHTEX_SIZE * vec2(0.5, -1.0);
    vec2 bias = SMAA_SEARCHTEX_SIZE * vec2(offset, 1.0);

    // Scale and bias to access texel centers:
    scale += vec2(-1.0,  1.0);
    bias  += vec2( 0.5, -0.5);

    // Convert from pixel coordinates to texcoords:
    scale *= 1.0 / SMAA_SEARCHTEX_PACKED_SIZE;
    bias *= 1.0 / SMAA_SEARCHTEX_PACKED_SIZE;

    return texture(searchTex, scale * e + bias).r;
}

/**
 * Search left for horizontal edge end
 */
float SMAASearchXLeft(sampler2D edgesTex, sampler2D searchTex, vec2 texcoord, float end) {
    vec2 e = vec2(0.0, 1.0);

    for (int i = 0; i < SMAA_MAX_SEARCH_STEPS; i++) {
        e = textureLod(edgesTex, texcoord, 0.0).rg;
        texcoord -= vec2(2.0, 0.0) * SMAA_AREATEX_PIXEL_SIZE * vec2(160.0 / 64.0, 1.0);
        if (!(texcoord.x > end && e.g > 0.8281 && e.r == 0.0)) break;
    }

    float offset = -(255.0 / 127.0) * SMAASearchLength(searchTex, e, 0.0) + 3.25;
    return texcoord.x + offset * SMAA_AREATEX_PIXEL_SIZE.x * (160.0 / 64.0);
}

/**
 * Search right for horizontal edge end
 */
float SMAASearchXRight(sampler2D edgesTex, sampler2D searchTex, vec2 texcoord, float end) {
    vec2 e = vec2(0.0, 1.0);

    for (int i = 0; i < SMAA_MAX_SEARCH_STEPS; i++) {
        e = textureLod(edgesTex, texcoord, 0.0).rg;
        texcoord += vec2(2.0, 0.0) * SMAA_AREATEX_PIXEL_SIZE * vec2(160.0 / 64.0, 1.0);
        if (!(texcoord.x < end && e.g > 0.8281 && e.r == 0.0)) break;
    }

    float offset = -(255.0 / 127.0) * SMAASearchLength(searchTex, e, 0.5) + 3.25;
    return texcoord.x - offset * SMAA_AREATEX_PIXEL_SIZE.x * (160.0 / 64.0);
}

/**
 * Search up for vertical edge end
 */
float SMAASearchYUp(sampler2D edgesTex, sampler2D searchTex, vec2 texcoord, float end) {
    vec2 e = vec2(1.0, 0.0);

    for (int i = 0; i < SMAA_MAX_SEARCH_STEPS; i++) {
        e = textureLod(edgesTex, texcoord, 0.0).rg;
        texcoord -= vec2(0.0, 2.0) * SMAA_AREATEX_PIXEL_SIZE * vec2(1.0, 560.0 / 16.0);
        if (!(texcoord.y > end && e.r > 0.8281 && e.g == 0.0)) break;
    }

    float offset = -(255.0 / 127.0) * SMAASearchLength(searchTex, e.gr, 0.0) + 3.25;
    return texcoord.y + offset * SMAA_AREATEX_PIXEL_SIZE.y * (560.0 / 16.0);
}

/**
 * Search down for vertical edge end
 */
float SMAASearchYDown(sampler2D edgesTex, sampler2D searchTex, vec2 texcoord, float end) {
    vec2 e = vec2(1.0, 0.0);

    for (int i = 0; i < SMAA_MAX_SEARCH_STEPS; i++) {
        e = textureLod(edgesTex, texcoord, 0.0).rg;
        texcoord += vec2(0.0, 2.0) * SMAA_AREATEX_PIXEL_SIZE * vec2(1.0, 560.0 / 16.0);
        if (!(texcoord.y < end && e.r > 0.8281 && e.g == 0.0)) break;
    }

    float offset = -(255.0 / 127.0) * SMAASearchLength(searchTex, e.gr, 0.5) + 3.25;
    return texcoord.y - offset * SMAA_AREATEX_PIXEL_SIZE.y * (560.0 / 16.0);
}

/**
 * Area lookup with square root decompression
 */
vec2 SMAAArea(sampler2D areaTex, vec2 dist, float e1, float e2, float offset) {
    // Remap the distanced to proper range:
    vec2 texcoord = float(SMAA_AREATEX_MAX_DISTANCE) * round(4.0 * vec2(e1, e2)) + dist;

    // Transform to proper texcoords:
    texcoord = SMAA_AREATEX_PIXEL_SIZE * texcoord + 0.5 * SMAA_AREATEX_PIXEL_SIZE;

    // Move to proper place according to the subpixel offset:
    texcoord.y = SMAA_AREATEX_SUBTEX_SIZE * offset + texcoord.y;

    // Lookup and return:
    return texture(areaTex, texcoord).rg;
}

/**
 * Full SMAA blending weight calculation
 */
vec4 SMAABlendingWeightCalculation(vec2 texcoord, vec2 pixcoord, vec4 offset[3],
                                   sampler2D edgesTex, sampler2D areaTex, sampler2D searchTex) {
    vec4 weights = vec4(0.0);

    vec2 e = texture(edgesTex, texcoord).rg;

    // Process horizontal edges (north edge)
    if (e.g > 0.0) {
        vec2 d;
        vec3 coords;

        // Find distance to the left
        coords.x = SMAASearchXLeft(edgesTex, searchTex, offset[0].xy, offset[2].x);
        coords.y = offset[1].y; // Crossing offset
        d.x = coords.x;

        // Fetch left crossing edges
        float e1 = textureLod(edgesTex, coords.xy, 0.0).r;

        // Find distance to the right
        coords.z = SMAASearchXRight(edgesTex, searchTex, offset[0].zw, offset[2].y);
        d.y = coords.z;

        // Convert distances to pixel units
        d = abs(round(d * pixcoord.x) - pixcoord.x);

        // Area texture is compressed quadratically, needs sqrt
        vec2 sqrt_d = sqrt(d);

        // Fetch right crossing edges
        float e2 = textureLodOffset(edgesTex, coords.zy, 0.0, ivec2(1, 0)).r;

        // Get the area for this pattern
        weights.rg = SMAAArea(areaTex, sqrt_d, e1, e2, 0.0);
    }

    // Process vertical edges (west edge)
    if (e.r > 0.0) {
        vec2 d;
        vec3 coords;

        // Find distance to the top
        coords.y = SMAASearchYUp(edgesTex, searchTex, offset[1].xy, offset[2].z);
        coords.x = offset[0].x; // Crossing offset
        d.x = coords.y;

        // Fetch top crossing edges
        float e1 = textureLod(edgesTex, coords.xy, 0.0).g;

        // Find distance to the bottom
        coords.z = SMAASearchYDown(edgesTex, searchTex, offset[1].zw, offset[2].w);
        d.y = coords.z;

        // Convert distances to pixel units
        d = abs(round(d * pixcoord.y) - pixcoord.y);

        // Area texture is compressed quadratically, needs sqrt
        vec2 sqrt_d = sqrt(d);

        // Fetch bottom crossing edges
        float e2 = textureLodOffset(edgesTex, coords.xz, 0.0, ivec2(0, 1)).g;

        // Get the area for this pattern
        weights.ba = SMAAArea(areaTex, sqrt_d, e1, e2, 0.0);
    }

    return weights;
}

void main() {
    fragColor = SMAABlendingWeightCalculation(uv, pixcoord, offset, edgesTex, areaTex, searchTex);
}
