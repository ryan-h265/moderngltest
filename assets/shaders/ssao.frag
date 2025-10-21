#version 410

// SSAO Fragment Shader
// Implements screen-space ambient occlusion using hemisphere sampling

in vec2 texCoord;
out float fragOcclusion;

// G-buffer inputs
uniform sampler2D gPosition;  // View-space position
uniform sampler2D gNormal;    // View-space normal
uniform sampler2D texNoise;   // Random rotation vectors

// SSAO parameters
uniform vec3 samples[64];     // Sample kernel
uniform int kernelSize;
uniform float radius;
uniform float bias;
uniform mat4 projection;
uniform vec2 noiseScale;

void main() {
    // Get view-space position and normal
    vec3 fragPos = texture(gPosition, texCoord).xyz;
    vec3 normal = normalize(texture(gNormal, texCoord).xyz);

    // Get random rotation vector from noise texture
    vec3 randomVec = normalize(texture(texNoise, texCoord * noiseScale).xyz);

    // Create TBN matrix to transform samples from tangent to view space
    // Gramm-Schmidt process to create orthonormal basis
    vec3 tangent = normalize(randomVec - normal * dot(randomVec, normal));
    vec3 bitangent = cross(normal, tangent);
    mat3 TBN = mat3(tangent, bitangent, normal);

    // Sample occlusion
    float occlusion = 0.0;
    for(int i = 0; i < kernelSize; ++i) {
        // Transform sample from tangent to view space
        vec3 samplePos = TBN * samples[i];
        samplePos = fragPos + samplePos * radius;

        // Project sample position to screen space
        vec4 offset = vec4(samplePos, 1.0);
        offset = projection * offset;        // View to clip space
        offset.xyz /= offset.w;              // Perspective divide
        offset.xyz = offset.xyz * 0.5 + 0.5; // Transform to [0,1] range

        // Get sample depth from G-buffer
        float sampleDepth = texture(gPosition, offset.xy).z;

        // Range check to prevent occlusion from distant geometry
        // Also add bias to prevent self-occlusion
        float rangeCheck = smoothstep(0.0, 1.0, radius / abs(fragPos.z - sampleDepth));
        occlusion += (sampleDepth >= samplePos.z + bias ? 1.0 : 0.0) * rangeCheck;
    }

    // Normalize and invert occlusion (1.0 = no occlusion, 0.0 = full occlusion)
    occlusion = 1.0 - (occlusion / float(kernelSize));

    fragOcclusion = occlusion;
}
