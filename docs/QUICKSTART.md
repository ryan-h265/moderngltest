# 🎮 Quick Start Guide

Get your shadow-mapped 3D game running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Make sure you're using ARM Python (not Rosetta)
python3 --version  # Should show arm64

# manual install (option B)
pip install -r requirements.txt
```

## Step 2: Run the Game

```bash
python3 game.py
```

You should see a window with:
- A green ground plane
- Three colored cubes (red, blue, yellow)
- Shadows cast by the cubes

## Step 3: Test the Controls

**Move the camera:**
- Press `W` `A` `S` `D` to move around
- Press `Q` and `E` to move up/down

**Move the light:**
- Use **Arrow Keys** to move the light horizontally
- Press `Z` and `X` to move the light up/down

Watch how the shadows change as you move the light!

## 🎯 What You've Got

This project includes:

1. **game.py** - Complete working game with shadow mapping
2. **README.md** - Full documentation
3. **SHADER_GUIDE.md** - Deep dive into shader code
4. **requirements.txt** - Dependencies
5. **setup.sh** - One-click installer

## 🚀 Next Steps

### Immediate modifications you can make:

**Add a new cube:**
```python
# In game.py, inside create_scene() method:
self.cube4 = geometry.cube(size=(1.0, 4.0, 1.0))
self.cube4_pos = Vector3([5.0, 2.0, 0.0])
self.cube4_color = (0.9, 0.5, 0.2)  # Orange

self.objects.append(
    (self.cube4, self.cube4_pos, self.cube4_color)
)
```

**Change shadow quality:**
```python
# In game.py, change SHADOW_SIZE:
SHADOW_SIZE = 4096  # Sharper shadows (default is 2048)
```

**Make shadows softer:**
```python
# In game.py, find the fragment shader and adjust PCF:
for(int x = -2; x <= 2; ++x) {      # Was -1 to 1
    for(int y = -2; y <= 2; ++y) {  # More samples = softer
        // ...
    }
}
shadow /= 25.0;  # Was 9.0
```

### Use Claude Code to help!

Since everything is in Python code, Claude Code can help you:

```bash
# Ask Claude Code to add features:
claude "Add a sphere object to the scene at position (0, 2, -5)"
claude "Increase the shadow map resolution to 4096"
claude "Add mouse look controls to the camera"
```

## 🐛 Troubleshooting

### "No module named 'moderngl'"
```bash
pip install -r requirements.txt
```

### Window doesn't open
Your Python might be using Rosetta. Check:
```bash
python3 -c "import platform; print(platform.machine())"
# Should print: arm64
```

### Shadows look weird (striped pattern)
This is "shadow acne" - increase the bias:
```python
# In game.py fragment shader:
float bias = 0.01;  # Was 0.005
```

### Shadows are floating
This is "peter panning" - decrease the bias:
```python
float bias = 0.001;  # Was 0.005
```

### Performance is slow
```python
# Reduce shadow map size:
SHADOW_SIZE = 1024  # Was 2048

# Or disable soft shadows (in fragment shader):
# Comment out the PCF loop and use single sample:
float shadow = current_depth - bias > closest_depth ? 1.0 : 0.0;
```

## 📚 Learn More

- **README.md** - Complete documentation with examples
- **SHADER_GUIDE.md** - Understand the shadow mapping shaders
- [ModernGL Docs](https://moderngl.readthedocs.io/)
- [LearnOpenGL Shadows](https://learnopengl.com/Advanced-Lighting/Shadows/Shadow-Mapping)

## ✅ Verify It's Working

You should see:
1. A 3D scene with cubes on a ground plane
2. Shadows on the ground below each cube
3. Shadows move when you press arrow keys (moves light)
4. Camera moves smoothly with WASD

If you see all of the above - **congratulations!** 🎉 You have a working shadow-mapped 3D engine.

## 🎨 Make It Your Own

This is your starter project. Some ideas:

- Load 3D models (.obj files)
- Add textures to objects
- Implement collision detection
- Add a player character
- Create a game loop with objectives
- Add sound effects
- Implement day/night cycle (move light in circle)

**Remember:** Claude Code can help you implement any of these features. Just describe what you want, and it can modify the code!

---

**Happy coding!** 🚀

Got questions? The code is heavily commented - read through `game.py` to understand how everything works.
