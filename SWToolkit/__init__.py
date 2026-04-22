bl_info = {
    "name": "SW Toolkit",
    "blender": (4, 5, 0),
    "category": "Object",
    "author": "Nika",
    "version": (0, 2, 2),
    "description": "Blender Toolkit for the Stormworks modding workflow.",
}

DEBUG = True
CURRENT_VERSION = ".".join(str(x) for x in bl_info["version"])

import bpy
import sys
from . import interfaceManager
from . import matToVert
from . import vertexcolorsplitter
from . import animImporter
from . import animExporter
from . import animPanel

# -------------------------------
# Hot-reload submodules in debug
# -------------------------------
if DEBUG:
    import importlib
    modules_to_reload = [
        "interfaceManager",
        "matToVert",
        "vertexcolorsplitter",
        "animImporter",
        "animExporter",
        "animPanel",
    ]
    for mod_name in modules_to_reload:
        full_name = f"{__name__}.{mod_name}"
        if full_name in sys.modules:
            importlib.reload(sys.modules[full_name])
            print(f"[SW Toolkit DEBUG] Reloaded {full_name}")

# -------------------------------
# File menu entries
# -------------------------------
def menu_import(self, context):
    self.layout.operator("animio.import_anim", text="Stormworks Animation (.anim)")

def menu_export(self, context):
    self.layout.operator("animio.export_anim", text="Stormworks Animation (.anim)")

# -------------------------------
# Register / Unregister
# -------------------------------
def register():
    interfaceManager.register()
    matToVert.register()
    vertexcolorsplitter.register()
    animImporter.register()
    animExporter.register()
    animPanel.register()

    # Add to File > Import and File > Export menus
    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)

    if DEBUG:
        print("[SW Toolkit DEBUG] Addon registered")


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)

    animPanel.unregister()
    animExporter.unregister()
    animImporter.unregister()
    vertexcolorsplitter.unregister()
    matToVert.unregister()
    interfaceManager.unregister()

    if DEBUG:
        print("[SW Toolkit DEBUG] Addon unregistered")


if __name__ == "__main__":
    register()
