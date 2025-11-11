bl_info = {
    "name": "SW Toolkit",
    "blender": (4, 5, 0),
    "category": "Object",
    "author": "Nika",
    "version": (0, 1, 2),
    "description": "Blender Toolkit for the Stormworks modding workflow. (ALPHA)",
}

DEBUG = True  

import bpy
import sys
from . import interfaceManager
from . import matToVert
from . import vertexcolorsplitter

# -------------------------------
# Hot-reload submodules in debug
# -------------------------------
if DEBUG:
    import importlib
    modules_to_reload = [
        "interfaceManager",
        "matToVert",
        "vertexcolorsplitter"
    ]
    for mod_name in modules_to_reload:
        full_name = f"{__name__}.{mod_name}"
        if full_name in sys.modules:
            importlib.reload(sys.modules[full_name])
            print(f"[SW Toolkit DEBUG] Reloaded {full_name}")

# -------------------------------
# Register / Unregister
# -------------------------------
def register():
    interfaceManager.register()
    matToVert.register()
    vertexcolorsplitter.register()
    if DEBUG:
        print("[SW Toolkit DEBUG] Addon registered")

def unregister():
    interfaceManager.unregister()
    matToVert.unregister()
    vertexcolorsplitter.unregister()
    if DEBUG:
        print("[SW Toolkit DEBUG] Addon unregistered")

if __name__ == "__main__":
    register()
