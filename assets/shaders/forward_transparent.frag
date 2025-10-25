#version 410

// Forward Rendering - Transparent Objects Fragment Shader
// Computes PBR lighting directly for alpha-blended materials

// Texture samplers
uniform sampler2D baseColorTexture;
uniform sampler2D normalTexture;
uniform sampler2D metallicRoughnessTexture;
uniform sampler2D emissiveTexture;
uniform sampler2D occlusionTexture;

// Shadow maps (one per light, max 4 lights)
uniform sampler2D shadowMap0;
uniform sampler2D shadowMap1;
uniform sampler2D shadowMap2;
uniform sampler2D shadowMap3;

// Texture flags
uniform bool hasBaseColorTexture;
uniform bool hasNormalTexture;
uniform bool hasMetallicRoughnessTexture;
uniform bool hasEmissiveTexture;
uniform bool hasOcclusionTexture;

// Texture transforms (KHR_texture_transform)
uniform mat3 baseColorTransform;
uniform mat3 normalTransform;
uniform mat3 metallicRoughnessTransform;
uniform mat3 emissiveTransform;
uniform mat3 occlusionTransform;

// Material properties
uniform vec4 baseColorFactor;
uniform vec3 emissiveFactor;
uniform float emissiveStrength;// KHR_materials_emissive_strength
uniform float occlusionStrength;
uniform float normalScale;

// Camera position (world space)
uniform vec3 cameraPos;

// Lighting uniforms (max 4 lights)
uniform int numLights;
uniform vec3 lightPositions[4];// World space
uniform vec3 lightColors[4];
uniform float lightIntensities[4];
uniform mat4 lightMatrices[4];// Light view-projection matrices for shadow mapping

// Shadow parameters
uniform float shadowBias;

// Ambient lighting
uniform float ambientStrength;

// Fog configuration
uniform bool fog_enabled;
uniform vec3 fog_color;
uniform float fog_density;
uniform float fog_start_distance;
uniform float fog_end_distance;
uniform float fog_base_height;
uniform float fog_height_falloff;
uniform float fog_noise_scale;
uniform float fog_noise_strength;
uniform float fog_noise_speed;
uniform vec3 fog_wind_direction;
uniform float fog_time;

// Inputs from vertex shader
in vec3 v_world_position;
in vec3 v_world_normal;
in vec2 v_texcoord;
in mat3 v_TBN;
in vec3 v_color;// Vertex color

// Output color (with alpha)
out vec4 fragColor;

const float PI=3.14159265359;

// PBR Functions

float DistributionGGX(vec3 N,vec3 H,float roughness){
    float a=roughness*roughness;
    float a2=a*a;
    float NdotH=max(dot(N,H),0.);
    float NdotH2=NdotH*NdotH;
    
    float denom=(NdotH2*(a2-1.)+1.);
    denom=PI*denom*denom;
    
    return a2/max(denom,.0001);
}

float GeometrySchlickGGX(float NdotV,float roughness){
    float r=(roughness+1.);
    float k=(r*r)/8.;
    
    float denom=NdotV*(1.-k)+k;
    
    return NdotV/max(denom,.0001);
}

float GeometrySmith(vec3 N,vec3 V,vec3 L,float roughness){
    float NdotV=max(dot(N,V),0.);
    float NdotL=max(dot(N,L),0.);
    float ggx2=GeometrySchlickGGX(NdotV,roughness);
    float ggx1=GeometrySchlickGGX(NdotL,roughness);
    
    return ggx1*ggx2;
}

vec3 fresnelSchlick(float cosTheta,vec3 F0){
    return F0+(1.-F0)*pow(max(1.-cosTheta,0.),5.);
}

float computeFogFactor(vec3 world_pos){
    if(!fog_enabled){
        return 0.;
    }
    
    float distance_to_camera=length(cameraPos-world_pos);
    float range=max(fog_end_distance-fog_start_distance,.001);
    float distance_factor=clamp((distance_to_camera-fog_start_distance)/range,0.,1.);
    
    float height_offset=max(world_pos.y-fog_base_height,0.);
    float height_factor=exp(-height_offset*fog_height_falloff);
    
    // Improved 3D noise for natural fog variation
    vec3 animated_pos=world_pos*fog_noise_scale+fog_wind_direction*(fog_time*fog_noise_speed);
    
    // Multiple octaves of noise for natural turbulence
    vec3 p1=animated_pos;
    vec3 p2=animated_pos*2.3+vec3(1.7,4.2,2.9);
    vec3 p3=animated_pos*4.7+vec3(8.1,2.3,5.7);
    
    float noise1=sin(p1.x)*cos(p1.y)+sin(p1.y+p1.z)*cos(p1.z)+sin(p1.z+p1.x);
    float noise2=sin(p2.x)*cos(p2.y)+sin(p2.y+p2.z)*cos(p2.z)+sin(p2.z+p2.x);
    float noise3=sin(p3.x)*cos(p3.y)+sin(p3.y+p3.z)*cos(p3.z)+sin(p3.z+p3.x);
    
    // Combine octaves with decreasing amplitude
    float combined_noise=(noise1+noise2*.5+noise3*.25)/1.75;
    float noise_normalized=combined_noise*.5+.5;
    
    // Apply smoothstep for softer transitions (reduces harsh edges)
    noise_normalized=smoothstep(.2,.8,noise_normalized);
    
    float variation=mix(1.-fog_noise_strength,1.+fog_noise_strength,noise_normalized);
    
    float density=fog_density*variation*height_factor;
    float fog_amount=1.-exp(-distance_to_camera*density);
    return clamp(fog_amount*distance_factor,0.,1.);
}

// PCF Shadow calculation (same as deferred lighting)
float calculateShadow(sampler2D shadowMap,vec4 fragPosLightSpace,float bias){
    // Perspective divide
    vec3 projCoords=fragPosLightSpace.xyz/fragPosLightSpace.w;
    
    // Transform to [0,1] range
    projCoords=projCoords*.5+.5;
    
    // Outside shadow map bounds = no shadow
    if(projCoords.z>1.||projCoords.x<0.||projCoords.x>1.||
    projCoords.y<0.||projCoords.y>1.){
        return 0.;
    }
    
    // PCF (Percentage Closer Filtering) for soft shadows
    float shadow=0.;
    vec2 texelSize=1./textureSize(shadowMap,0);
    for(int x=-1;x<=1;++x){
        for(int y=-1;y<=1;++y){
            float pcfDepth=texture(shadowMap,projCoords.xy+vec2(x,y)*texelSize).r;
            shadow+=(projCoords.z-bias)>pcfDepth?1.:0.;
        }
    }
    shadow/=9.;
    
    return shadow;
}

void main(){
    // Sample base color with transform
    vec4 albedo;
    if(hasBaseColorTexture){
        vec2 transformed_uv=(baseColorTransform*vec3(v_texcoord,1.)).xy;
        albedo=texture(baseColorTexture,transformed_uv)*baseColorFactor;
    }else{
        albedo=baseColorFactor;
    }
    
    // Multiply by vertex color (GLTF COLOR_0 attribute)
    albedo.rgb*=v_color;
    
    // Early discard for fully transparent pixels (optimization)
    if(albedo.a<.01){
        discard;
    }
    
    // Calculate normal with optional normal mapping
    vec3 N;
    if(hasNormalTexture){
        vec2 transformed_uv=(normalTransform*vec3(v_texcoord,1.)).xy;
        vec3 normal_sample=texture(normalTexture,transformed_uv).rgb;
        normal_sample=normal_sample*2.-1.;
        normal_sample.xy*=normalScale;
        N=normalize(v_TBN*normal_sample);
    }else{
        N=normalize(v_world_normal);
    }
    
    // Sample metallic/roughness with transform
    float metallic=0.;
    float roughness=.5;
    if(hasMetallicRoughnessTexture){
        vec2 transformed_uv=(metallicRoughnessTransform*vec3(v_texcoord,1.)).xy;
        vec3 mr=texture(metallicRoughnessTexture,transformed_uv).rgb;
        metallic=mr.b;
        roughness=mr.g;
    }
    
    // Sample occlusion with transform
    float occlusion=1.;
    if(hasOcclusionTexture){
        vec2 transformed_uv=(occlusionTransform*vec3(v_texcoord,1.)).xy;
        float ao_sample=texture(occlusionTexture,transformed_uv).r;
        occlusion=mix(1.,ao_sample,occlusionStrength);
    }
    
    // Sample emissive with transform
    vec3 emissive=emissiveFactor;
    if(hasEmissiveTexture){
        vec2 transformed_uv=(emissiveTransform*vec3(v_texcoord,1.)).xy;
        emissive*=texture(emissiveTexture,transformed_uv).rgb;
    }
    // Apply emissive strength (KHR_materials_emissive_strength)
    emissive*=emissiveStrength;
    
    // PBR Lighting calculation
    vec3 V=normalize(cameraPos-v_world_position);
    
    // Calculate F0 (surface reflection at zero incidence)
    vec3 F0=vec3(.04);// Dielectric base reflectivity
    F0=mix(F0,albedo.rgb,metallic);
    
    // Accumulate lighting from all lights
    vec3 Lo=vec3(0.);
    
    for(int i=0;i<numLights&&i<4;++i){
        // Light direction and distance
        vec3 L=normalize(lightPositions[i]-v_world_position);
        vec3 H=normalize(V+L);
        float distance=length(lightPositions[i]-v_world_position);
        float attenuation=1./(distance*distance);
        vec3 radiance=lightColors[i]*lightIntensities[i]*attenuation;
        
        // Cook-Torrance BRDF
        float NDF=DistributionGGX(N,H,roughness);
        float G=GeometrySmith(N,V,L,roughness);
        vec3 F=fresnelSchlick(max(dot(H,V),0.),F0);
        
        vec3 kS=F;
        vec3 kD=vec3(1.)-kS;
        kD*=1.-metallic;
        
        vec3 numerator=NDF*G*F;
        float denominator=4.*max(dot(N,V),0.)*max(dot(N,L),0.);
        vec3 specular=numerator/max(denominator,.001);
        
        float NdotL=max(dot(N,L),0.);
        
        // Shadow calculation
        float shadow=0.;
        vec4 fragPosLightSpace=lightMatrices[i]*vec4(v_world_position,1.);
        
        if(i==0)shadow=calculateShadow(shadowMap0,fragPosLightSpace,shadowBias);
        else if(i==1)shadow=calculateShadow(shadowMap1,fragPosLightSpace,shadowBias);
        else if(i==2)shadow=calculateShadow(shadowMap2,fragPosLightSpace,shadowBias);
        else if(i==3)shadow=calculateShadow(shadowMap3,fragPosLightSpace,shadowBias);
        
        // Add to outgoing radiance
        Lo+=(kD*albedo.rgb/PI+specular)*radiance*NdotL*(1.-shadow)*occlusion;
    }
    
    // Ambient lighting (simple approximation)
    vec3 ambient=ambientStrength*albedo.rgb*occlusion;
    
    // Final color
    vec3 color=ambient+Lo+emissive;
    
    float fog_factor=computeFogFactor(v_world_position);
    color=mix(color,fog_color,fog_factor);
    
    // Output with alpha for blending
    fragColor=vec4(color,albedo.a);
}
