"""
Shader Manager

Loads and manages shader programs from files.
"""

from pathlib import Path
from typing import Dict
import moderngl

from ..config.settings import SHADERS_DIR


class ShaderManager:
    """
    Loads and manages shader programs.

    Shaders are loaded from .vert and .frag files in the shaders directory.
    """

    def __init__(self, ctx: moderngl.Context, shader_dir: Path = SHADERS_DIR):
        """
        Initialize shader manager.

        Args:
            ctx: ModernGL context
            shader_dir: Directory containing shader files
        """
        self.ctx = ctx
        self.shader_dir = Path(shader_dir)
        self.programs: Dict[str, moderngl.Program] = {}

        # Verify shader directory exists
        if not self.shader_dir.exists():
            raise FileNotFoundError(f"Shader directory not found: {self.shader_dir}")

    def load_program(self, name: str, vert_file: str, frag_file: str) -> moderngl.Program:
        """
        Load a shader program from vertex and fragment shader files.

        Args:
            name: Name to register program under
            vert_file: Vertex shader filename (e.g., "shadow_depth.vert")
            frag_file: Fragment shader filename (e.g., "shadow_depth.frag")

        Returns:
            Compiled shader program

        Raises:
            FileNotFoundError: If shader files don't exist
            moderngl.Error: If shader compilation fails
        """
        vert_path = self.shader_dir / vert_file
        frag_path = self.shader_dir / frag_file

        # Check files exist
        if not vert_path.exists():
            raise FileNotFoundError(f"Vertex shader not found: {vert_path}")
        if not frag_path.exists():
            raise FileNotFoundError(f"Fragment shader not found: {frag_path}")

        # Load shader source
        with open(vert_path, 'r') as f:
            vert_shader = f.read()
        with open(frag_path, 'r') as f:
            frag_shader = f.read()

        # Compile program
        try:
            program = self.ctx.program(
                vertex_shader=vert_shader,
                fragment_shader=frag_shader
            )
            self.programs[name] = program
            return program
        except moderngl.Error as e:
            raise moderngl.Error(f"Failed to compile shader program '{name}': {e}")

    def get(self, name: str) -> moderngl.Program:
        """
        Get a loaded shader program by name.

        Args:
            name: Program name

        Returns:
            Shader program

        Raises:
            KeyError: If program not loaded
        """
        if name not in self.programs:
            raise KeyError(f"Shader program '{name}' not loaded. Available: {list(self.programs.keys())}")
        return self.programs[name]

    def has(self, name: str) -> bool:
        """Check if a program is loaded"""
        return name in self.programs

    def reload(self, name: str) -> moderngl.Program:
        """
        Reload a shader program (useful for hot-reloading during development).

        Args:
            name: Program name to reload

        Returns:
            Recompiled shader program

        Raises:
            KeyError: If program was never loaded
        """
        # This would require storing the file paths, which we could add if needed
        raise NotImplementedError("Shader hot-reloading not yet implemented")

    def __contains__(self, name: str) -> bool:
        """Support 'in' operator"""
        return self.has(name)

    def __getitem__(self, name: str) -> moderngl.Program:
        """Support subscript access: shader_manager['shadow']"""
        return self.get(name)
