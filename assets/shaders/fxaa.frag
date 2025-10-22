#version 330 core

in vec2 uv;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec2 u_texel_size;  // 1.0 / screen_size
uniform bool u_fxaa_enabled;

// FXAA Quality Settings
#define FXAA_QUALITY_PRESET 12
#define FXAA_EDGE_THRESHOLD (1.0/3.0)
#define FXAA_EDGE_THRESHOLD_MIN (1.0/12.0)

float FxaaLuma(vec3 rgb) {
    return rgb.y * (0.587/0.299) + rgb.x;
}

vec3 FxaaPixelShader(
    vec2 pos,
    sampler2D tex,
    vec2 fxaaQualityRcpFrame
) {
    vec3 rgbN = texture(tex, pos + vec2(0.0, -fxaaQualityRcpFrame.y)).rgb;
    vec3 rgbW = texture(tex, pos + vec2(-fxaaQualityRcpFrame.x, 0.0)).rgb;
    vec3 rgbM = texture(tex, pos).rgb;
    vec3 rgbE = texture(tex, pos + vec2(fxaaQualityRcpFrame.x, 0.0)).rgb;
    vec3 rgbS = texture(tex, pos + vec2(0.0, fxaaQualityRcpFrame.y)).rgb;
    
    float lumaN = FxaaLuma(rgbN);
    float lumaW = FxaaLuma(rgbW);
    float lumaM = FxaaLuma(rgbM);
    float lumaE = FxaaLuma(rgbE);
    float lumaS = FxaaLuma(rgbS);
    
    float rangeMin = min(lumaM, min(min(lumaN, lumaW), min(lumaS, lumaE)));
    float rangeMax = max(lumaM, max(max(lumaN, lumaW), max(lumaS, lumaE)));
    
    float range = rangeMax - rangeMin;
    
    if(range < max(FXAA_EDGE_THRESHOLD_MIN, rangeMax * FXAA_EDGE_THRESHOLD)) {
        return rgbM;
    }
    
    vec3 rgbL = rgbN + rgbW + rgbM + rgbE + rgbS;
    
    float lumaL = (lumaN + lumaW + lumaE + lumaS) * 0.25;
    float rangeL = abs(lumaL - lumaM);
    float blendL = max(0.0, (rangeL / range) - FXAA_EDGE_THRESHOLD_MIN) / (1.0 - FXAA_EDGE_THRESHOLD_MIN);
    blendL = min(0.75, blendL);
    
    vec3 rgbNW = texture(tex, pos + vec2(-fxaaQualityRcpFrame.x, -fxaaQualityRcpFrame.y)).rgb;
    vec3 rgbNE = texture(tex, pos + vec2(fxaaQualityRcpFrame.x, -fxaaQualityRcpFrame.y)).rgb;
    vec3 rgbSW = texture(tex, pos + vec2(-fxaaQualityRcpFrame.x, fxaaQualityRcpFrame.y)).rgb;
    vec3 rgbSE = texture(tex, pos + vec2(fxaaQualityRcpFrame.x, fxaaQualityRcpFrame.y)).rgb;
    
    rgbL += (rgbNW + rgbNE + rgbSW + rgbSE);
    rgbL *= (1.0 / 9.0);
    
    float lumaNW = FxaaLuma(rgbNW);
    float lumaNE = FxaaLuma(rgbNE);
    float lumaSW = FxaaLuma(rgbSW);
    float lumaSE = FxaaLuma(rgbSE);
    
    float edgeVert = abs((0.25 * lumaNW) + (-0.5 * lumaN) + (0.25 * lumaNE)) +
                     abs((0.50 * lumaW ) + (-1.0 * lumaM) + (0.50 * lumaE )) +
                     abs((0.25 * lumaSW) + (-0.5 * lumaS) + (0.25 * lumaSE));
                     
    float edgeHorz = abs((0.25 * lumaNW) + (-0.5 * lumaW) + (0.25 * lumaSW)) +
                     abs((0.50 * lumaN ) + (-1.0 * lumaM) + (0.50 * lumaS )) +
                     abs((0.25 * lumaNE) + (-0.5 * lumaE) + (0.25 * lumaSE));
    
    bool horzSpan = edgeHorz >= edgeVert;
    
    float lengthSign = horzSpan ? -fxaaQualityRcpFrame.y : -fxaaQualityRcpFrame.x;
    
    if(!horzSpan) {
        lumaN = lumaW;
        lumaS = lumaE;
    }
    
    float gradientN = abs(lumaN - lumaM);
    float gradientS = abs(lumaS - lumaM);
    lumaN = (lumaN + lumaM) * 0.5;
    lumaS = (lumaS + lumaM) * 0.5;
    
    if (gradientN < gradientS) {
        lumaN = lumaS;
        gradientN = gradientS;
        lengthSign *= -1.0;
    }
    
    vec2 posN;
    posN.x = pos.x + (horzSpan ? 0.0 : lengthSign * 0.5);
    posN.y = pos.y + (horzSpan ? lengthSign * 0.5 : 0.0);
    
    gradientN *= FXAA_EDGE_THRESHOLD;
    
    vec2 posP = posN;
    vec2 offNP = horzSpan ? vec2(fxaaQualityRcpFrame.x, 0.0) : vec2(0.0, fxaaQualityRcpFrame.y);
    
    float lumaEndN = FxaaLuma(texture(tex, posN).rgb);
    float lumaEndP = FxaaLuma(texture(tex, posP).rgb);
    
    if(!horzSpan) lumaEndN -= lumaM * 0.5;
    if(!horzSpan) lumaEndP -= lumaM * 0.5;
    if( horzSpan) lumaEndN -= lumaM * 0.5;
    if( horzSpan) lumaEndP -= lumaM * 0.5;
    
    bool doneN = abs(lumaEndN) >= gradientN;
    bool doneP = abs(lumaEndP) >= gradientN;
    
    if(!doneN) posN -= offNP;
    if(!doneP) posP += offNP;
    
    if(!(doneN && doneP)) {
        for(int i = 0; i < 8; i++) {
            if(!doneN) lumaEndN = FxaaLuma(texture(tex, posN.xy).rgb);
            if(!doneP) lumaEndP = FxaaLuma(texture(tex, posP.xy).rgb);
            if(!horzSpan) lumaEndN -= lumaM * 0.5;
            if(!horzSpan) lumaEndP -= lumaM * 0.5;
            if( horzSpan) lumaEndN -= lumaM * 0.5;
            if( horzSpan) lumaEndP -= lumaM * 0.5;
            doneN = abs(lumaEndN) >= gradientN;
            doneP = abs(lumaEndP) >= gradientN;
            if(doneN && doneP) break;
            if(!doneN) posN -= offNP;
            if(!doneP) posP += offNP;
        }
    }
    
    float dstN = pos.x - posN.x;
    float dstP = posP.x - pos.x;
    if(!horzSpan) dstN = pos.y - posN.y;
    if(!horzSpan) dstP = posP.y - pos.y;
    
    bool directionN = dstN < dstP;
    lumaEndN = directionN ? lumaEndN : lumaEndP;
    
    if(((lumaM - lumaN) < 0.0) == ((lumaEndN - lumaN) < 0.0)) lengthSign = 0.0;
    
    float spanLength = (dstP + dstN);
    dstN = directionN ? dstN : dstP;
    float subPixelOffset = (0.5 + (dstN * (-1.0/spanLength))) * lengthSign;
    
    vec3 rgbF = texture(tex, vec2(
        pos.x + (horzSpan ? 0.0 : subPixelOffset),
        pos.y + (horzSpan ? subPixelOffset : 0.0))).rgb;
    
    return mix(rgbL, rgbF, blendL);
}

void main() {
    if (!u_fxaa_enabled) {
        fragColor = vec4(texture(u_texture, uv).rgb, 1.0);
        return;
    }
    
    vec3 color = FxaaPixelShader(uv, u_texture, u_texel_size);
    fragColor = vec4(color, 1.0);
}