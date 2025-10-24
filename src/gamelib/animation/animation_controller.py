"""
Animation Controller

Manages animation playback, blending, and state.
"""

from typing import Optional
from pyrr import Matrix44, Vector3, Quaternion
from .animation import Animation, AnimationTarget
from .skeleton import Skeleton


class AnimationController:
    """
    Controls animation playback for a skeleton.

    Manages:
    - Current animation and playback time
    - Play/pause/loop states
    - Applying animation data to skeleton
    """

    def __init__(self, skeleton: Skeleton):
        """
        Initialize animation controller.

        Args:
            skeleton: Skeleton to animate
        """
        self.skeleton = skeleton
        self.current_animation: Optional[Animation] = None
        self.current_time: float = 0.0
        self.is_playing: bool = False
        self.loop: bool = True
        self.playback_speed: float = 1.0

    def play(self, animation: Animation, loop: bool = True):
        """
        Start playing an animation.

        Args:
            animation: Animation to play
            loop: Whether to loop the animation
        """
        self.current_animation = animation
        self.current_time = 0.0
        self.is_playing = True
        self.loop = loop

    def pause(self):
        """Pause animation playback."""
        self.is_playing = False

    def resume(self):
        """Resume animation playback."""
        self.is_playing = True

    def stop(self):
        """Stop animation and reset to bind pose."""
        self.is_playing = False
        self.current_time = 0.0
        self.skeleton.reset_animation()

    def update(self, delta_time: float):
        """
        Update animation playback.

        Args:
            delta_time: Time elapsed since last frame (seconds)
        """
        if not self.is_playing or not self.current_animation:
            return

        # Advance time
        self.current_time += delta_time * self.playback_speed

        # Handle looping
        if self.current_time >= self.current_animation.duration:
            if self.loop:
                self.current_time = self.current_time % self.current_animation.duration
            else:
                self.current_time = self.current_animation.duration
                self.is_playing = False

        # Sample animation at current time
        sampled_data = self.current_animation.sample_all(self.current_time)

        # Apply to skeleton joints
        self._apply_animation_to_skeleton(sampled_data)

    def _apply_animation_to_skeleton(self, sampled_data: dict):
        """
        Apply sampled animation data to skeleton joints.

        Args:
            sampled_data: Dictionary mapping (node_name, property) -> value
        """
        # Group by node name
        node_transforms = {}

        for (node_name, property_type), value in sampled_data.items():
            if node_name not in node_transforms:
                node_transforms[node_name] = {
                    'translation': None,
                    'rotation': None,
                    'scale': None,
                }

            if property_type == AnimationTarget.TRANSLATION:
                node_transforms[node_name]['translation'] = value
            elif property_type == AnimationTarget.ROTATION:
                node_transforms[node_name]['rotation'] = value
            elif property_type == AnimationTarget.SCALE:
                node_transforms[node_name]['scale'] = value

        # Apply transforms to joints
        for node_name, transforms in node_transforms.items():
            joint = self.skeleton.get_joint(node_name)
            if joint is None:
                continue

            # Build transformation matrix from T/R/S
            translation = transforms['translation'] if transforms['translation'] is not None else joint.base_translation
            rotation = transforms['rotation'] if transforms['rotation'] is not None else joint.base_rotation
            scale = transforms['scale'] if transforms['scale'] is not None else joint.base_scale

            # Start with local transform as base
            mat = Matrix44.identity()

            # Apply scale first (match loader order)
            if scale is not None:
                scale_vec = scale if isinstance(scale, Vector3) else Vector3(scale)
                mat = mat @ Matrix44.from_scale(scale_vec)

            # Apply rotation
            if rotation is not None:
                if isinstance(rotation, (list, tuple)):
                    rot_quat = Quaternion(rotation)
                elif isinstance(rotation, Quaternion):
                    rot_quat = rotation
                else:
                    rot_quat = Quaternion(rotation)
                mat = mat @ rot_quat.matrix44

            # Apply translation last
            if translation is not None:
                trans_vec = translation if isinstance(translation, Vector3) else Vector3(translation)
                mat = mat @ Matrix44.from_translation(trans_vec)

            # Set animated transform
            joint.animated_transform = mat

        # Update world transforms after applying animation
        self.skeleton.update_world_transforms()

    def __repr__(self):
        anim_name = self.current_animation.name if self.current_animation else "None"
        return f"AnimationController(animation='{anim_name}', time={self.current_time:.2f}s, playing={self.is_playing})"
