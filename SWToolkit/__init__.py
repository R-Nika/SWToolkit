bl_info = {
    "name": "SW Toolkit",
    "blender": (3, 6, 0),  
    "category": "3D View",
    "author": "Nika",
    "version": (1, 0, 0),
    "description": "Blender Toolkit for the Stormworks modding workflow.",
}

# Import the modules (scripts)
import bpy
from . import matToVert
from . import vertexcolorsplitter
from . import interfaceManager

# Register the modules (functions, panels, etc.)
def register():
    matToVert.register()
    vertexcolorsplitter.register()
    interfaceManager.register()

def unregister():
    matToVert.unregister()
    vertexcolorsplitter.unregister()
    interfaceManager.unregister()

if __name__ == "__main__":
    register()
