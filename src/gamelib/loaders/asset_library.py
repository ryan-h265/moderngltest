"""
Asset Library - Manages Available Assets

Scans asset directories and provides thumbnail menu data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import json


class Asset:
    """Represents a single asset in the library."""

    def __init__(
        self,
        asset_id: str,
        name: str,
        category: str,
        path: str,
        icon_path: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Initialize asset.

        Args:
            asset_id: Unique identifier for asset
            name: Display name
            category: Asset category (Models, Lights, Objects, Materials)
            path: Path to asset file
            icon_path: Path to icon/thumbnail image
            metadata: Additional metadata dict
        """
        self.id = asset_id
        self.name = name
        self.category = category
        self.path = path
        self.icon_path = icon_path
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Convert to dictionary for inspector."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "path": self.path,
            "icon_path": self.icon_path,
            **self.metadata,
        }


class AssetLibrary:
    """Manages all available assets in the project."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize asset library.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path.cwd()
        self.assets: Dict[str, List[Asset]] = {
            "Models": [],
            "Lights": [],
            "Objects": [],
            "Materials": [],
        }
        self.assets_by_id: Dict[str, Asset] = {}

    def scan_assets(self) -> None:
        """Scan project directories for assets."""
        # Scan model directory
        self._scan_models()

        # Scan materials (if any)
        self._scan_materials()

    def _scan_models(self) -> None:
        """Scan assets/models/ directory for GLTF/GLB files."""
        models_dir = self.project_root / "assets" / "models"

        if not models_dir.exists():
            return

        # Recursively find all GLTF/GLB files
        for gltf_file in models_dir.glob("**/*.gltf"):
            asset_id = str(gltf_file.relative_to(models_dir)).replace("/", "_").replace("\\", "_")
            asset_name = gltf_file.stem
            asset_path = str(gltf_file)

            # Look for associated PNG thumbnail
            icon_path = None
            icon_candidates = [
                gltf_file.parent / f"{gltf_file.stem}.png",
                gltf_file.parent / "thumbnail.png",
            ]
            for candidate in icon_candidates:
                if candidate.exists():
                    icon_path = str(candidate)
                    break

            asset = Asset(
                asset_id=asset_id,
                name=asset_name,
                category="Models",
                path=asset_path,
                icon_path=icon_path,
                metadata={
                    "is_model": True,
                    "description": f"Model: {asset_name}",
                }
            )
            self.add_asset(asset)

        # Also check for GLB files
        for glb_file in models_dir.glob("**/*.glb"):
            asset_id = str(glb_file.relative_to(models_dir)).replace("/", "_").replace("\\", "_")
            asset_name = glb_file.stem
            asset_path = str(glb_file)

            # Look for associated PNG thumbnail
            icon_path = None
            icon_candidates = [
                glb_file.parent / f"{glb_file.stem}.png",
                glb_file.parent / "thumbnail.png",
            ]
            for candidate in icon_candidates:
                if candidate.exists():
                    icon_path = str(candidate)
                    break

            asset = Asset(
                asset_id=asset_id,
                name=asset_name,
                category="Models",
                path=asset_path,
                icon_path=icon_path,
                metadata={
                    "is_model": True,
                    "description": f"Model: {asset_name}",
                }
            )
            self.add_asset(asset)

    def _scan_materials(self) -> None:
        """Scan assets/materials/ directory for material definitions."""
        materials_dir = self.project_root / "assets" / "materials"

        if not materials_dir.exists():
            return

        # Look for material JSON files
        for mat_file in materials_dir.glob("*.json"):
            try:
                with open(mat_file, 'r') as f:
                    mat_data = json.load(f)

                asset_id = mat_file.stem
                asset_name = mat_data.get("name", mat_file.stem)

                asset = Asset(
                    asset_id=asset_id,
                    name=asset_name,
                    category="Materials",
                    path=str(mat_file),
                    metadata=mat_data,
                )
                self.add_asset(asset)
            except Exception as e:
                print(f"Warning: Failed to load material {mat_file}: {e}")

    def add_asset(self, asset: Asset) -> None:
        """
        Add asset to library.

        Args:
            asset: Asset to add
        """
        if asset.category not in self.assets:
            self.assets[asset.category] = []

        self.assets[asset.category].append(asset)
        self.assets_by_id[asset.id] = asset

    def get_assets_by_category(self, category: str) -> List[Asset]:
        """
        Get all assets in a category.

        Args:
            category: Category name

        Returns:
            List of assets in category
        """
        return self.assets.get(category, [])

    def get_asset_by_id(self, asset_id: str) -> Optional[Asset]:
        """
        Get asset by ID.

        Args:
            asset_id: Asset ID

        Returns:
            Asset or None if not found
        """
        return self.assets_by_id.get(asset_id)

    def get_all_categories(self) -> List[str]:
        """
        Get all available categories.

        Returns:
            List of category names
        """
        return [cat for cat in self.assets.keys() if self.assets[cat]]

    def to_thumbnail_items(self) -> Dict[str, List[dict]]:
        """
        Convert to format suitable for ThumbnailMenu.

        Returns:
            Dict mapping category to list of item dicts
        """
        result = {}
        for category, assets in self.assets.items():
            result[category] = [asset.to_dict() for asset in assets]
        return result
