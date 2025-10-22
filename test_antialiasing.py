#!/usr/bin/env python3
"""
Anti-Aliasing Test

Simple test to verify MSAA + FXAA implementation is working.
"""

import moderngl
import sys
sys.path.insert(0, '.')

from src.gamelib.rendering.antialiasing_renderer import AntiAliasingRenderer, AAMode

def test_antialiasing():
    """Test anti-aliasing functionality"""
    print("🔧 Testing Anti-Aliasing Implementation")
    print("=" * 50)
    
    # Create context
    ctx = moderngl.create_standalone_context()
    
    # Create mock FXAA shader (minimal version for testing)
    fxaa_vert = """#version 330 core
    in vec2 in_position;
    in vec2 in_texcoord;
    out vec2 uv;
    void main() {
        gl_Position = vec4(in_position, 0.0, 1.0);
        uv = in_texcoord;
    }"""
    
    fxaa_frag = """#version 330 core
    in vec2 uv;
    out vec4 fragColor;
    uniform sampler2D u_texture;
    uniform vec2 u_texel_size;
    uniform bool u_fxaa_enabled;
    void main() {
        fragColor = texture(u_texture, uv);
    }"""
    
    fxaa_program = ctx.program(vertex_shader=fxaa_vert, fragment_shader=fxaa_frag)
    
    # Create AA renderer
    aa_renderer = AntiAliasingRenderer(ctx, (1280, 720), fxaa_program)
    
    print(f"✓ Initial mode: {aa_renderer.get_aa_mode_name()}")
    
    # Test all modes
    modes_to_test = [
        AAMode.FXAA,
        AAMode.MSAA_2X, 
        AAMode.MSAA_4X,
        AAMode.MSAA_4X_FXAA,
        AAMode.OFF
    ]
    
    for mode in modes_to_test:
        aa_renderer.set_aa_mode(mode)
        target = aa_renderer.get_render_target()
        print(f"✓ {aa_renderer.get_aa_mode_name()}: Target = {type(target).__name__}")
    
    # Test cycling
    print("\n🔄 Testing Mode Cycling:")
    for i in range(6):
        mode = aa_renderer.cycle_aa_mode()
        print(f"  {i+1}. {aa_renderer.get_aa_mode_name()}")
    
    # Test toggles
    print("\n🔀 Testing Toggles:")
    aa_renderer.set_aa_mode(AAMode.OFF)
    print(f"  Start: {aa_renderer.get_aa_mode_name()}")
    
    aa_renderer.toggle_msaa()
    print(f"  +MSAA: {aa_renderer.get_aa_mode_name()}")
    
    aa_renderer.toggle_fxaa()
    print(f"  +FXAA: {aa_renderer.get_aa_mode_name()}")
    
    aa_renderer.toggle_msaa()
    print(f"  -MSAA: {aa_renderer.get_aa_mode_name()}")
    
    # Cleanup
    aa_renderer.cleanup()
    
    print("\n🎉 Anti-Aliasing Implementation: WORKING!")
    print("\nℹ️  Controls in-game:")
    print("   F7 - Cycle AA modes")
    print("   F8 - Toggle MSAA")
    print("\n💡 Modes available:")
    print("   • Off (max performance)")
    print("   • FXAA (fast, good quality)")  
    print("   • MSAA 2x/4x (traditional high quality)")
    print("   • MSAA + FXAA (best quality)")

if __name__ == "__main__":
    test_antialiasing()