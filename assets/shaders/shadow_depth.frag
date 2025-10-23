#version 410

// Shadow Map Fragment Shader
// Depth is automatically written to the depth buffer
// Alpha testing is handled in geometry pass, not needed here for primitives

void main() {
    // No color output needed - depth buffer is written automatically
    // This creates the shadow map used in main rendering pass

    // Note: Alpha testing for MASK mode is handled by a separate shader
    // for textured models to avoid attribute mismatches with primitives
}
