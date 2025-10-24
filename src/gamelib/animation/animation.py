"""
Animation

Keyframe animation data and playback.
"""

from typing import List, Tuple
from enum import Enum
from pyrr import Matrix44, Vector3, Quaternion
import numpy as np


class InterpolationType(Enum):
    """Animation interpolation types."""
    LINEAR = "LINEAR"
    STEP = "STEP"
    CUBICSPLINE = "CUBICSPLINE"


class AnimationTarget(Enum):
    """Animation target properties."""
    TRANSLATION = "translation"
    ROTATION = "rotation"
    SCALE = "scale"
    WEIGHTS = "weights"  # Morph target weights


class Keyframe:
    """
    Single keyframe in an animation.

    Stores time and value for a specific property.
    """

    def __init__(self, time: float, value):
        """
        Initialize keyframe.

        Args:
            time: Time in seconds
            value: Value at this time (Vector3 for T/S, Quaternion for R)
        """
        self.time = time
        self.value = value

    def __repr__(self):
        return f"Keyframe(t={self.time:.3f}, v={self.value})"


class AnimationChannel:
    """
    Animation channel targets a specific joint property.

    Contains keyframes for translation, rotation, or scale.
    """

    def __init__(
        self,
        target_node_name: str,
        target_property: AnimationTarget,
        interpolation: InterpolationType = InterpolationType.LINEAR
    ):
        """
        Initialize animation channel.

        Args:
            target_node_name: Name of the joint/node to animate
            target_property: Property to animate (translation/rotation/scale)
            interpolation: Interpolation method
        """
        self.target_node_name = target_node_name
        self.target_property = target_property
        self.interpolation = interpolation
        self.keyframes: List[Keyframe] = []

    def add_keyframe(self, time: float, value):
        """Add a keyframe to this channel."""
        self.keyframes.append(Keyframe(time, value))

    def sample(self, time: float):
        """
        Sample the animation at a given time.

        Args:
            time: Time in seconds

        Returns:
            Interpolated value at this time
        """
        if not self.keyframes:
            return None

        # Clamp time to animation range
        if time <= self.keyframes[0].time:
            return self.keyframes[0].value
        if time >= self.keyframes[-1].time:
            return self.keyframes[-1].value

        # Find surrounding keyframes
        for i in range(len(self.keyframes) - 1):
            k0 = self.keyframes[i]
            k1 = self.keyframes[i + 1]

            if k0.time <= time <= k1.time:
                # Interpolate between k0 and k1
                if self.interpolation == InterpolationType.STEP:
                    return k0.value
                elif self.interpolation == InterpolationType.LINEAR:
                    return self._interpolate_linear(k0, k1, time)
                elif self.interpolation == InterpolationType.CUBICSPLINE:
                    # Simplified cubic (treat as linear for now)
                    return self._interpolate_linear(k0, k1, time)

        return self.keyframes[-1].value

    def _interpolate_linear(self, k0: Keyframe, k1: Keyframe, time: float):
        """Linear interpolation between two keyframes."""
        # Calculate interpolation factor
        t = (time - k0.time) / (k1.time - k0.time) if k1.time > k0.time else 0.0

        # Interpolate based on value type
        v0 = k0.value
        v1 = k1.value

        # Quaternion rotation (use SLERP)
        if self.target_property == AnimationTarget.ROTATION:
            # Ensure we have quaternions
            if isinstance(v0, (list, tuple, np.ndarray)):
                v0 = Quaternion(v0)
            if isinstance(v1, (list, tuple, np.ndarray)):
                v1 = Quaternion(v1)

            return Quaternion.slerp(v0, v1, t)

        # Vector3 translation/scale (linear interpolation)
        else:
            if isinstance(v0, (list, tuple)):
                v0 = np.array(v0, dtype='f4')
            if isinstance(v1, (list, tuple)):
                v1 = np.array(v1, dtype='f4')

            return v0 * (1.0 - t) + v1 * t

    def __repr__(self):
        return f"AnimationChannel(node='{self.target_node_name}', property={self.target_property.value}, keyframes={len(self.keyframes)})"


class Animation:
    """
    Complete animation with multiple channels.

    An animation consists of multiple channels, each targeting
    a specific joint property (translation/rotation/scale).
    """

    def __init__(self, name: str):
        """
        Initialize animation.

        Args:
            name: Animation name
        """
        self.name = name
        self.channels: List[AnimationChannel] = []
        self.duration: float = 0.0  # Computed from keyframes

    def add_channel(self, channel: AnimationChannel):
        """Add an animation channel."""
        self.channels.append(channel)

        # Update duration
        if channel.keyframes:
            max_time = max(kf.time for kf in channel.keyframes)
            self.duration = max(self.duration, max_time)

    def sample_all(self, time: float) -> dict:
        """
        Sample all channels at a given time.

        Args:
            time: Time in seconds

        Returns:
            Dictionary mapping (node_name, property) -> value
        """
        results = {}
        for channel in self.channels:
            key = (channel.target_node_name, channel.target_property)
            results[key] = channel.sample(time)
        return results

    def __repr__(self):
        return f"Animation(name='{self.name}', duration={self.duration:.2f}s, channels={len(self.channels)})"
