"""
Texture Pool

Reference-counted texture management system to prevent duplicate texture loading
and premature GPU memory deallocation.

Enables texture sharing across multiple model instances while automatically
freeing GPU memory when no models reference a texture.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
import moderngl


class TexturePool:
    """
    Reference-counted texture management system.

    Prevents duplicate texture loading and manages GPU memory by:
    - Deduplicating identical texture files
    - Reference counting to track usage
    - Automatic GPU deallocation when no longer referenced
    - Optional texture caching for pre-loaded assets

    Industry pattern used by most game engines for texture management.
    """

    # Class-level shared pool
    _instance: Optional['TexturePool'] = None
    _textures: Dict[str, Tuple[moderngl.Texture, int]] = {}  # filepath -> (texture, ref_count)

    def __init__(self, ctx: moderngl.Context = None):
        """
        Initialize texture pool.

        Args:
            ctx: ModernGL context (optional, for texture creation)
        """
        self.ctx = ctx

    @classmethod
    def get_instance(cls, ctx: moderngl.Context = None) -> 'TexturePool':
        """
        Get or create singleton instance.

        Args:
            ctx: ModernGL context (only used on first initialization)

        Returns:
            Global TexturePool instance
        """
        if cls._instance is None:
            cls._instance = cls(ctx=ctx)
        return cls._instance

    def add_texture_reference(self, filepath: str, texture: moderngl.Texture) -> None:
        """
        Register a texture in the pool and increment its reference count.

        Args:
            filepath: Path to the texture file (used as cache key)
            texture: ModernGL Texture object
        """
        cache_key = str(Path(filepath).resolve())

        if cache_key in self._textures:
            # Already exists, increment ref count
            cached_texture, ref_count = self._textures[cache_key]
            self._textures[cache_key] = (cached_texture, ref_count + 1)
        else:
            # New texture
            self._textures[cache_key] = (texture, 1)

    def release_texture_reference(self, filepath: str) -> bool:
        """
        Release a reference to a texture.

        If reference count reaches 0, GPU texture is deleted.

        Args:
            filepath: Path to the texture file

        Returns:
            True if texture was released from GPU, False if still in use
        """
        cache_key = str(Path(filepath).resolve())

        if cache_key not in self._textures:
            return False

        texture, ref_count = self._textures[cache_key]
        ref_count -= 1

        if ref_count <= 0:
            # Delete from GPU
            texture.release()
            del self._textures[cache_key]
            return True
        else:
            # Still referenced, keep in pool
            self._textures[cache_key] = (texture, ref_count)
            return False

    def get_texture_ref_count(self, filepath: str) -> int:
        """
        Get the current reference count for a texture.

        Args:
            filepath: Path to the texture file

        Returns:
            Reference count (0 if not in pool)
        """
        cache_key = str(Path(filepath).resolve())
        if cache_key in self._textures:
            _, ref_count = self._textures[cache_key]
            return ref_count
        return 0

    def clear_pool(self) -> None:
        """Clear entire texture pool (for testing/cleanup)."""
        for texture, _ in self._textures.values():
            texture.release()
        self._textures.clear()

    def get_pool_stats(self) -> Dict:
        """
        Get texture pool statistics.

        Returns:
            Dictionary with pool metrics
        """
        total_refs = sum(ref_count for _, ref_count in self._textures.values())
        return {
            'num_textures': len(self._textures),
            'total_references': total_refs,
        }
