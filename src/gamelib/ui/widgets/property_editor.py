"""
Generic Property Editors

Reusable ImGui widgets for editing common property types.
"""

from typing import Optional, Tuple, Any

import imgui
from pyrr import Vector3


def edit_float(
    label: str,
    value: float,
    min_val: float = -1000.0,
    max_val: float = 1000.0,
    step: float = 0.1,
) -> Tuple[bool, float]:
    """
    Edit a float value with a slider and input field.

    Args:
        label: Widget label
        value: Current value
        min_val: Minimum value
        max_val: Maximum value
        step: Step size for slider

    Returns:
        Tuple of (changed, new_value)
    """
    changed, new_value = imgui.slider_float(
        f"##{label}_slider",
        value,
        min_val,
        max_val,
        step,
    )
    imgui.same_line()
    imgui.text(label)
    return changed, new_value


def edit_vector3(
    label: str,
    value: Vector3,
    min_val: float = -1000.0,
    max_val: float = 1000.0,
    step: float = 0.1,
) -> Tuple[bool, Vector3]:
    """
    Edit a Vector3 with three sliders (X, Y, Z).

    Args:
        label: Widget label
        value: Current Vector3
        min_val: Minimum value per component
        max_val: Maximum value per component
        step: Step size

    Returns:
        Tuple of (changed, new_vector)
    """
    changed_x, x = imgui.slider_float(
        f"##{label}_x",
        float(value.x),
        min_val,
        max_val,
        step,
    )
    imgui.same_line()
    imgui.text(f"{label} X")

    changed_y, y = imgui.slider_float(
        f"##{label}_y",
        float(value.y),
        min_val,
        max_val,
        step,
    )
    imgui.same_line()
    imgui.text(f"{label} Y")

    changed_z, z = imgui.slider_float(
        f"##{label}_z",
        float(value.z),
        min_val,
        max_val,
        step,
    )
    imgui.same_line()
    imgui.text(f"{label} Z")

    changed = changed_x or changed_y or changed_z
    new_vector = Vector3([x, y, z]) if changed else value
    return changed, new_vector


def edit_color(
    label: str,
    value: Tuple[float, float, float, float],
) -> Tuple[bool, Tuple[float, float, float, float]]:
    """
    Edit a color (RGBA).

    Args:
        label: Widget label
        value: Current color as (r, g, b, a) tuple

    Returns:
        Tuple of (changed, new_color)
    """
    # Convert to RGBA if needed
    if len(value) == 3:
        value = (*value, 1.0)

    changed, new_color = imgui.color_edit4(
        f"##{label}_color",
        value[0],
        value[1],
        value[2],
        value[3],
    )
    imgui.same_line()
    imgui.text(label)

    if changed:
        return True, new_color[:4]
    return False, value


def edit_enum(
    label: str,
    value: Any,
    enum_class: type,
) -> Tuple[bool, Any]:
    """
    Edit an enum value with radio buttons.

    Args:
        label: Widget label
        value: Current enum value
        enum_class: Enum class

    Returns:
        Tuple of (changed, new_value)
    """
    imgui.text(label)
    changed = False
    new_value = value

    for enum_member in enum_class:
        is_selected = imgui.radio_button(
            enum_member.name,
            value == enum_member,
        )
        if is_selected:
            changed = True
            new_value = enum_member

    return changed, new_value


def edit_text(
    label: str,
    value: str,
    max_length: int = 256,
) -> Tuple[bool, str]:
    """
    Edit a text field.

    Args:
        label: Widget label
        value: Current text
        max_length: Maximum text length

    Returns:
        Tuple of (changed, new_text)
    """
    changed, new_text = imgui.input_text(
        f"##{label}_text",
        value,
        max_length,
    )
    imgui.same_line()
    imgui.text(label)
    return changed, new_text
