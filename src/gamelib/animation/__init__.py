"""
Animation System

Provides skeletal animation support for GLTF models.
"""

from .skeleton import Joint, Skeleton
from .skin import Skin
from .animation import Keyframe, AnimationChannel, Animation, AnimationTarget, InterpolationType
from .animation_controller import AnimationController

__all__ = [
    'Joint',
    'Skeleton',
    'Skin',
    'Keyframe',
    'AnimationChannel',
    'Animation',
    'AnimationTarget',
    'InterpolationType',
    'AnimationController',
]
