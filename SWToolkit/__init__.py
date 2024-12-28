bl_info = {
    "name": "SW Toolkit",
    "blender": (3, 6, 0),  
    "category": "Object",
    "author": "Nika",
    "version": (1, 0, 0),
    "description": "Blender Toolkit for the Stormworks modding workflow.",
}

import bpy
from . import interfaceManager
from . import matToVert
from . import vertexcolorsplitter

# Registering and Unregistering functions
def register():
    interfaceManager.register()
    matToVert.register()
    vertexcolorsplitter.register()

def unregister():
    interfaceManager.unregister()
    matToVert.unregister()
    vertexcolorsplitter.unregister()

if __name__ == "__main__":
    register()
