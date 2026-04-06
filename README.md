# SW Toolkit Addon for Blender (v4.5+ LTS)

The **SW Toolkit** is a Blender add-on built specifically for **Stormworks modding**, focused on speeding up workflow and simplifying common tasks like color conversion and mesh preparation.

---

## 🚀 Quick Start / Use Cases

* **.anim Tools:**
  Allows modification of mesh geometry in `.anim` files, such as characters, armor, and animals. 

* **Separate by Vertex Color:**
  Ideal for cleaning up exported vehicles for use as meshes.

* **Color Conversion Tools:**
  Streamlines the coloring process for map building, props, and component modeling.

> Note: This addon only edits the mesh, not animations.

## ✨ Features

### 🎞️ .anim Tools*

* Import mesh geometry and armature from .anim files, and export it back to .anim

---

### 🎨 Color Conversion Tools

#### Separate by Vertex Color

Splits a mesh into separate objects based on vertex colors, with optional cleanup tools.

#### Color Converting Tool

Convert between materials and vertex colors.

* **Material → Vertex Color** — Converts material color into vertex colors
* **Vertex Color → Material** — Generates materials from vertex colors

---

## 🛠️ Planned Features

### Map Editing *(Planned)*

* Road editing tools

---

## ⚠️ Important Notes for .anim Editing

### Creating Glass

To create glass, selected faces **must** be assigned to a material called `glass` with the color `#E7E7E7FF`.

### Vertex Groups

All vertices **must** be assigned to a vertex group of the armature.
If this is not done, the mesh will be invisible in-game.

### Animations

This addon **does not support editing animations**, only geometry.
There are **no plans** to add animation support at this time.


## 📦 Installation

1. Download `SWToolkit.zip`
2. Open Blender
3. Go to **Edit → Preferences → Add-ons → Install**
4. Select `SWToolkit.zip`
5. Enable the addon in the Add-ons list

---

## 💬 Feedback & Support

Got suggestions or issues?
Join the **[SMF Discord](https://discord.gg/mFY8Wuk)**

---

## ❤️ Support

If you like the addon, you can support me here:
👉 http://www.buymeacoffee.com/nika_cheese
