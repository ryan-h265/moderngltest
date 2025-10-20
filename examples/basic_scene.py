#!/usr/bin/env python3
"""
Basic Scene Example

Demonstrates the default scene with 18 cubes and 2 shadow-casting lights.
This is the same as running main.py.
"""

import sys
sys.path.insert(0, '..')

from main import Game

if __name__ == '__main__':
    print("Running basic scene example...")
    print("Controls:")
    print("  WASD - Move camera")
    print("  QE - Move camera up/down")
    print("  Mouse - Look around")
    print("  ESC - Release mouse cursor")
    print()
    Game.run()
