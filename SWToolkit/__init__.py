bl_info = {
    "name": "SW Toolkit",
    "blender": (4, 5, 0),
    "category": "Object",
    "author": "Nika",
    "version": (0, 3, 0),
    "description": "Blender Toolkit for the Stormworks modding workflow.",
}

DEBUG = False
CURRENT_VERSION = ".".join(str(x) for x in bl_info["version"])

import bpy
import sys

from . import infoPanel
from .tools import matToVert
from .tools import vertexcolorsplitter
from .tools import toolPanel

from .anim import animImporter
from .anim import animExporter
from .anim import animPanel

from .mesh import meshPanel
from .mesh import mesh_importer
from .mesh import mesh_exporter
from .mesh import phys_importer
from .mesh import phys_exporter


if DEBUG:
    import importlib

    modules_to_reload = [
        "infoPanel",
        "tools.matToVert",
        "tools.vertexcolorsplitter",
        "tools.toolPanel",
        "anim.animImporter",
        "anim.animExporter",
        "anim.animPanel",
        "mesh.meshPanel",
        "mesh.mesh_importer",
        "mesh.mesh_exporter",
        "mesh.phys_importer",
        "mesh.phys_exporter",
    ]

    for module_name in modules_to_reload:
        full_name = f"{__name__}.{module_name}"
        if full_name in sys.modules:
            importlib.reload(sys.modules[full_name])
            print(f"[SW Toolkit DEBUG] Reloaded {full_name}")


def menu_import(self, context):
    self.layout.operator(
        "animio.import_anim",
        text="Stormworks Animation (.anim)"
    )
    self.layout.operator(
        "import_scene.stormworks_mesh",
        text="Stormworks Mesh (.mesh)"
    )
    self.layout.operator(
        "import_scene.stormworks_phys",
        text="Stormworks Physics (.phys)"
    )


def menu_export(self, context):
    self.layout.operator(
        "animio.export_anim",
        text="Stormworks Animation (.anim)"
    )
    self.layout.operator(
        "export_scene.stormworks_mesh",
        text="Stormworks Mesh (.mesh)"
    )
    self.layout.operator(
        "export_scene.stormworks_phys",
        text="Stormworks Physics (.phys)"
    )


def register():
    infoPanel.register()
    meshPanel.register()
    animPanel.register()
    toolPanel.register()

    # Other non-panel modules
    matToVert.register()
    vertexcolorsplitter.register()
    animImporter.register()
    animExporter.register()
    mesh_importer.register()
    mesh_exporter.register()
    phys_importer.register()
    phys_exporter.register()

    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)

    if DEBUG:
        print("[SW Toolkit DEBUG] Addon registered")


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)

    phys_exporter.unregister()
    phys_importer.unregister()
    mesh_exporter.unregister()
    mesh_importer.unregister()
    meshPanel.unregister()
    toolPanel.unregister()
    animPanel.unregister()
    animExporter.unregister()
    animImporter.unregister()
    vertexcolorsplitter.unregister()
    matToVert.unregister()
    infoPanel.unregister()

    if DEBUG:
        print("[SW Toolkit DEBUG] Addon unregistered")


if __name__ == "__main__":
    register()