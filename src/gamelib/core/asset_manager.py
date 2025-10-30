"""
Asset Manager

Centralized caching system for GLTF models with reference counting and memory management.
Implements industry-standard asset lifecycle management (Unity/Godot pattern).
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
import sys
from collections import OrderedDict
from dataclasses import dataclass
import moderngl


@dataclass
class CachedAsset:
    """Represents a cached asset with reference count and metadata."""
    model: 'Model'  # The cached model
    ref_count: int = 1  # Number of active references
    memory_bytes: int = 0  # Estimated GPU memory usage
    access_count: int = 0  # For LRU eviction



class AssetManager:
    """
    Centralized asset caching system for game engine.

    Manages model asset lifecycle with:
    - Automatic caching of loaded models
    - Reference counting for proper cleanup
    - Memory budget enforcement with LRU eviction
    - Debug statistics and monitoring

    Industry-standard pattern matching Unity's Resource system and Godot's ResourceLoader.
    """

    # Class-level cache (shared by all instances)
    _instance: Optional['AssetManager'] = None
    _cache: Dict[str, CachedAsset] = {}
    _access_order: OrderedDict[str, str] = OrderedDict()  # For LRU eviction

    # Configuration
    DEFAULT_MEMORY_BUDGET = 500 * 1024 * 1024  # 500 MB default
    MIN_MEMORY_BUDGET = 50 * 1024 * 1024  # 50 MB minimum
    MAX_MEMORY_BUDGET = 4 * 1024 * 1024 * 1024  # 4 GB maximum

    def __init__(self, ctx: moderngl.Context = None, memory_budget_mb: int = 500):
        """
        Initialize asset manager.

        Args:
            ctx: ModernGL context (optional, for texture pool creation)
            memory_budget_mb: Maximum memory to keep in cache (default 500 MB)
        """
        self.ctx = ctx
        self.memory_budget = memory_budget_mb * 1024 * 1024

        # Clamp memory budget to reasonable values
        self.memory_budget = max(self.MIN_MEMORY_BUDGET,
                                  min(self.memory_budget, self.MAX_MEMORY_BUDGET))

        # Statistics
        self._stats = {
            'total_loads': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'evictions': 0,
        }

    @classmethod
    def get_instance(cls, ctx: moderngl.Context = None, memory_budget_mb: int = 500) -> 'AssetManager':
        """
        Get or create singleton instance.

        Args:
            ctx: ModernGL context (only used on first initialization)
            memory_budget_mb: Memory budget in MB (only used on first initialization)

        Returns:
            Global AssetManager instance
        """
        if cls._instance is None:
            cls._instance = cls(ctx=ctx, memory_budget_mb=memory_budget_mb)
        return cls._instance

    def cache_model(self, filepath: str, model: 'Model') -> None:
        """
        Cache a loaded model.

        Args:
            filepath: Path to the model file (used as cache key)
            model: Model object to cache
        """
        cache_key = str(Path(filepath).resolve())

        # If already cached, increment ref count
        if cache_key in self._cache:
            self._cache[cache_key].ref_count += 1
            self._access_order.move_to_end(cache_key)
            return

        # Estimate memory usage (very rough estimate)
        memory_bytes = self._estimate_model_memory(model)

        # Create cache entry
        cached_asset = CachedAsset(
            model=model,
            ref_count=1,
            memory_bytes=memory_bytes,
            access_count=0
        )

        self._cache[cache_key] = cached_asset
        self._access_order[cache_key] = cache_key

        # Evict if needed
        self._evict_if_needed()

    def get_cached_model(self, filepath: str) -> Optional['Model']:
        """
        Retrieve a cached model.

        Args:
            filepath: Path to the model file

        Returns:
            Cached Model if found, None otherwise
        """
        cache_key = str(Path(filepath).resolve())

        if cache_key in self._cache:
            cached_asset = self._cache[cache_key]
            cached_asset.access_count += 1
            self._access_order.move_to_end(cache_key)
            self._stats['cache_hits'] += 1
            return cached_asset.model

        self._stats['cache_misses'] += 1
        return None

    def is_cached(self, filepath: str) -> bool:
        """Check if a model is cached."""
        cache_key = str(Path(filepath).resolve())
        return cache_key in self._cache

    def release_model(self, filepath: str) -> None:
        """
        Release a reference to a cached model.

        When ref count reaches 0, model is removed from cache.

        Args:
            filepath: Path to the model file
        """
        cache_key = str(Path(filepath).resolve())

        if cache_key not in self._cache:
            return

        cached_asset = self._cache[cache_key]
        cached_asset.ref_count -= 1

        # Remove from cache if no more references
        if cached_asset.ref_count <= 0:
            self._remove_from_cache(cache_key)

    def preload_models(self, filepaths: list) -> None:
        """
        Preload multiple models into cache.

        Useful for warming up cache at startup before gameplay.
        Requires GltfLoader to be passed in.

        Args:
            filepaths: List of model file paths to preload
        """
        # This will be called by the loader after loading
        # We just prepare the cache here
        pass

    def clear_cache(self) -> None:
        """Clear entire cache (for testing/cleanup)."""
        for cache_key in list(self._cache.keys()):
            self._remove_from_cache(cache_key)
        self._reset_stats()

    def release_unused(self) -> int:
        """
        Release all cached models with ref_count <= 0.

        Returns:
            Number of models released
        """
        released = 0
        for cache_key in list(self._cache.keys()):
            if self._cache[cache_key].ref_count <= 0:
                self._remove_from_cache(cache_key)
                released += 1
        return released

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        total_memory = sum(a.memory_bytes for a in self._cache.values())
        hit_rate = (self._stats['cache_hits'] /
                   (self._stats['cache_hits'] + self._stats['cache_misses'])
                   if (self._stats['cache_hits'] + self._stats['cache_misses']) > 0
                   else 0.0)

        return {
            'num_cached_models': len(self._cache),
            'total_memory_mb': total_memory / (1024 * 1024),
            'memory_budget_mb': self.memory_budget / (1024 * 1024),
            'memory_used_percent': (total_memory / self.memory_budget * 100) if self.memory_budget > 0 else 0,
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'hit_rate': hit_rate,
            'evictions': self._stats['evictions'],
            'total_loads': self._stats['total_loads'],
        }

    def print_cache_status(self) -> None:
        """Print human-readable cache statistics."""
        stats = self.get_cache_stats()
        print("\n=== Asset Manager Cache Status ===")
        print(f"Cached Models: {stats['num_cached_models']}")
        print(f"Memory Usage: {stats['total_memory_mb']:.1f} MB / {stats['memory_budget_mb']:.0f} MB ({stats['memory_used_percent']:.1f}%)")
        print(f"Cache Hit Rate: {stats['hit_rate']:.1%} ({stats['cache_hits']} hits, {stats['cache_misses']} misses)")
        print(f"Total Loads: {stats['total_loads']}, Evictions: {stats['evictions']}")
        print(f"\nCached assets:")
        for cache_key, cached_asset in self._cache.items():
            print(f"  {Path(cache_key).name}: {cached_asset.memory_bytes / (1024 * 1024):.1f} MB (refs: {cached_asset.ref_count})")
        print()

    def _estimate_model_memory(self, model: 'Model') -> int:
        """
        Estimate GPU memory usage of a model.

        Args:
            model: Model to estimate

        Returns:
            Estimated memory in bytes
        """
        memory = 0

        # Estimate per mesh
        for mesh in model.meshes:
            # VAO memory (very rough estimate: assume ~50KB per mesh for vertices)
            memory += 50 * 1024

            # Texture memory (very rough estimate)
            material = mesh.material
            if material:
                # Assume 4 bytes per pixel (RGBA)
                # Typical texture: 2048x2048 = 16 MB
                texture_size = 2048 * 2048 * 4

                if material.base_color_texture:
                    memory += texture_size
                if material.normal_texture:
                    memory += texture_size
                if material.metallic_roughness_texture:
                    memory += texture_size // 4  # Usually packed format
                if material.emissive_texture:
                    memory += texture_size // 4

        return memory

    def _evict_if_needed(self) -> None:
        """Evict LRU cached models if memory budget exceeded."""
        total_memory = sum(a.memory_bytes for a in self._cache.values())

        while total_memory > self.memory_budget and len(self._cache) > 1:
            # Get LRU (first item in OrderedDict)
            lru_key = next(iter(self._access_order))

            # Only evict if it has no active references
            if self._cache[lru_key].ref_count <= 0:
                memory_freed = self._cache[lru_key].memory_bytes
                self._remove_from_cache(lru_key)
                total_memory -= memory_freed
                self._stats['evictions'] += 1
            else:
                # Can't evict models with active references
                break

    def _remove_from_cache(self, cache_key: str) -> None:
        """
        Remove a model from cache.

        Args:
            cache_key: Key of model to remove
        """
        if cache_key in self._cache:
            del self._cache[cache_key]
        if cache_key in self._access_order:
            del self._access_order[cache_key]

    def _reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            'total_loads': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'evictions': 0,
        }

    def get_formatted_status(self, verbose: bool = False) -> str:
        """
        Get formatted cache status as a string suitable for debug UI or console.

        Args:
            verbose: If True, include detailed asset list

        Returns:
            Formatted status string
        """
        stats = self.get_cache_stats()

        lines = [
            "═══════════════════════════════════════",
            "        Asset Manager Cache Status     ",
            "═══════════════════════════════════════",
            f"Cached Models: {stats['num_cached_models']}",
            f"Memory: {stats['total_memory_mb']:.1f} MB / {stats['memory_budget_mb']:.0f} MB ({stats['memory_used_percent']:.1f}%)",
            f"Hit Rate: {stats['hit_rate']:.1%} ({stats['cache_hits']} hits, {stats['cache_misses']} misses)",
            f"Evictions: {stats['evictions']} | Total Loads: {stats['total_loads']}",
        ]

        if verbose and self._cache:
            lines.append("───────────────────────────────────────")
            lines.append("Cached Assets:")
            for cache_key, cached_asset in sorted(self._cache.items()):
                name = Path(cache_key).name
                size = cached_asset.memory_bytes / (1024 * 1024)
                lines.append(f"  {name:30} {size:6.1f} MB (refs: {cached_asset.ref_count})")

        lines.append("═══════════════════════════════════════\n")
        return "\n".join(lines)
