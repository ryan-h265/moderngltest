#version 410

in vec3 v_texcoord;

uniform samplerCube skybox_texture;
uniform float intensity;

uniform float u_time;
uniform vec2 u_resolution;
uniform vec3 u_auroraDir;
uniform float u_transitionAlpha;
uniform int u_useProceduralSky;

uniform int fogEnabled;
uniform vec3 fogColor;
uniform float fogStart;
uniform float fogEnd;
uniform float fogStrength;

out vec4 f_color;

mat2 mm2(float a) {
    float c = cos(a), s = sin(a);
    return mat2(c, s, -s, c);
}

mat2 m2 = mat2(0.95534, 0.29552, -0.29552, 0.95534);

float tri(float x) { return clamp(abs(fract(x) - 0.5), 0.01, 0.49); }

vec2 tri2(vec2 p) { return vec2(tri(p.x) + tri(p.y), tri(p.y + tri(p.x))); }

float triNoise2d(vec2 p, float spd, float time) {
    float z = 1.8;
    float z2 = 2.5;
    float rz = 0.0;
    p *= mm2(p.x * 0.06);
    vec2 bp = p;
    for (float i = 0.0; i < 5.0; i++) {
        vec2 dg = tri2(bp * 1.85) * 0.75;
        dg *= mm2(time * spd);
        p -= dg / z2;
        bp *= 1.3;
        z2 *= 0.45;
        z *= 0.42;
        p *= 1.21 + (rz - 1.0) * 0.02;
        rz += tri(p.x + tri(p.y)) * z;
        p *= -m2;
    }
    return clamp(1.0 / pow(rz * 29.0, 1.3), 0.0, 0.55);
}

vec3 nmzHash33(vec3 q) {
    uvec3 p = uvec3(ivec3(q));
    p = p * uvec3(374761393U, 1103515245U, 668265263U) + p.zxy + p.yzx;
    p = p.yzx * (p.zxy ^ (p >> 3U));
    return vec3(p ^ (p >> 16U)) * (1.0 / 4294967295.0);
}

vec4 aurora(vec3 ro, vec3 rd, float time) {
    vec4 col = vec4(0.0);
    vec4 avgCol = vec4(0.0);
    for (float i = 0.0; i < 50.0; i++) {
        float pt = ((0.8 + pow(i, 1.4) * 0.002) - ro.y) / (rd.y * 2.0 + 0.4);
        vec3 bpos = ro + pt * rd;
        vec2 p = bpos.zx;
        float rzt = triNoise2d(p, 0.06, time);
        vec4 col2 = vec4(0.0);
        col2.a = rzt;
        col2.rgb = (sin(1.0 - vec3(2.15, -0.5, 1.2) + i * 0.043) * 0.5 + 0.5) * rzt;
        avgCol = mix(avgCol, col2, 0.5);
        col += avgCol * exp2(-i * 0.065 - 2.5) * smoothstep(0.0, 5.0, i);
    }
    col *= clamp(rd.y * 15.0 + 0.4, 0.0, 1.0);
    return col * 1.8;
}

vec3 stars(vec3 p) {
    vec3 c = vec3(0.0);
    float res = max(u_resolution.x, 1.0);
    for (float i = 0.0; i < 4.0; i++) {
        vec3 q = fract(p * (0.15 * res)) - 0.5;
        vec3 id = floor(p * (0.15 * res));
        vec2 rn = nmzHash33(id).xy;
        float c2 = 1.0 - smoothstep(0.0, 0.6, length(q));
        c2 *= step(rn.x, 0.0005 + i * i * 0.001);
        c += c2 * (mix(vec3(1.0, 0.49, 0.1), vec3(0.75, 0.9, 1.0), rn.y) * 0.1 + 0.9);
        p *= 1.3;
    }
    return c * c * 0.8;
}

vec3 background_color(vec3 rd) {
    float sd = dot(normalize(u_auroraDir), rd) * 0.5 + 0.5;
    sd = pow(sd, 5.0);
    vec3 col = mix(vec3(0.05, 0.1, 0.2), vec3(0.1, 0.05, 0.2), sd);
    return col * 0.63;
}

vec3 compute_aurora_sky(vec3 dir) {
    vec3 rd = dir.xzy;  // align with original Shadertoy axes
    rd = vec3(rd.x, rd.z, -rd.y);  // rotate +90° around the X axis so sky is above and ground below
    vec3 ro = vec3(0.0);  // keep procedural sky anchored while camera moves

    float fade = smoothstep(0.0, 0.01, abs(rd.y)) * 0.1 + 0.9;
    vec3 col = background_color(rd) * fade;

    if (rd.y > 0.0) {
        vec4 aur = smoothstep(0.0, 1.5, aurora(ro, rd, u_time)) * fade;
        col += stars(rd);
        col = col * (1.0 - aur.a) + aur.rgb;
    } else {
        rd.y = abs(rd.y);
        col = background_color(rd) * fade * 0.6;
        vec4 aur = smoothstep(0.0, 2.5, aurora(ro, rd, u_time));
        col += stars(rd) * 0.1;
        col = col * (1.0 - aur.a) + aur.rgb;
        vec3 pos = ro + ((0.5 - ro.y) / rd.y) * rd;
        float nz2 = triNoise2d(pos.xz * vec2(0.5, 0.7), 0.0, u_time);
        col += mix(vec3(0.2, 0.25, 0.5) * 0.08, vec3(0.3, 0.3, 0.5) * 0.7, nz2 * 0.4);
    }

    if (fogEnabled == 1) {
        float horizonFog = pow(clamp(1.0 - abs(rd.y), 0.0, 1.0), 1.2);
        float fogFactor = clamp(horizonFog * fogStrength, 0.0, 1.0);
        col = mix(col, fogColor, fogFactor);
    }

    return col;
}

void main() {
    vec3 dir = normalize(v_texcoord);
    vec3 color = texture(skybox_texture, dir).rgb;

    if (u_useProceduralSky == 1) {
        color = compute_aurora_sky(dir);
    }

    color *= intensity;
    f_color = vec4(color, u_transitionAlpha);
}
