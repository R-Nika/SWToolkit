import bpy
import struct

from pathlib import Path

from bpy.props import StringProperty
from bpy.types import Operator


PHYS_FORMAT_VERSION = 2


def blender_to_stormworks(position):
    """Convert Blender position coordinates to Stormworks .phys axes.

    sw_x = -blender_x
    sw_y =  blender_z
    sw_z = -blender_y
    """
    x, y, z = position
    return (-x, z, -y)


def selected_mesh_objects(context):
    return [
        obj
        for obj in context.selected_objects
        if obj.type == 'MESH'
    ]


def collision_vertices(obj):
    """Return unindexed Stormworks triangle-list positions for one object."""

    mesh = obj.data
    vertices = []

    for polygon in mesh.polygons:

        if len(polygon.loop_indices) != 3:
            raise ValueError(
                f"{obj.name}: polygon {polygon.index} has "
                f"{len(polygon.loop_indices)} sides. "
                "Triangulate the mesh before exporting."
            )

        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index

            # .phys has no object transforms, so bake each selected
            # object's current world-space transform into the positions.
            world_position = (
                obj.matrix_world
                @ mesh.vertices[vertex_index].co
            )

            vertices.append(
                blender_to_stormworks(world_position)
            )

    if len(vertices) > 0xFFFF:
        raise ValueError(
            f"{obj.name}: {len(vertices)} collision vertices; "
            ".phys supports at most 65535 per mesh."
        )

    return vertices


def write_phys(filepath, objects):
    """Write selected mesh objects to a Stormworks .phys file."""

    if not objects:
        raise ValueError(
            "Select at least one mesh object to export."
        )

    if len(objects) > 0xFFFF:
        raise ValueError(
            "Too many selected collision meshes for the .phys format."
        )

    collision_meshes = [
        (obj.name, collision_vertices(obj))
        for obj in objects
    ]

    # Make sure none of the selected meshes are empty.
    if any(not vertices for _, vertices in collision_meshes):
        empty_names = ", ".join(
            name
            for name, vertices in collision_meshes
            if not vertices
        )

        raise ValueError(
            f"Selected mesh has no triangles: {empty_names}"
        )

    output = bytearray(b"phys")

    # Header:
    # magic
    # version
    # collision mesh count
    output += struct.pack(
        "<HH",
        PHYS_FORMAT_VERSION,
        len(collision_meshes)
    )

    for _, vertices in collision_meshes:

        # Vertex count
        output += struct.pack(
            "<H",
            len(vertices)
        )

        # Vertex positions
        for position in vertices:
            output += struct.pack(
                "<3f",
                *position
            )

        # Trailing value
        output += struct.pack(
            "<H",
            0
        )

    Path(filepath).write_bytes(output)

    return (
        len(collision_meshes),
        sum(
            len(vertices) // 3
            for _, vertices in collision_meshes
        )
    )


class EXPORT_OT_stormworks_phys(Operator):
    bl_idname = "export_scene.stormworks_phys"
    bl_label = "Export Stormworks Physics"
    bl_description = "Export the selected object as .phys file(s)"
    bl_options = {'REGISTER'}

    filepath: StringProperty(
        name="Physics file path",
        description="Output path for the Stormworks .phys file",
        subtype='FILE_PATH',
        default="",
    )

    filter_glob: StringProperty(
        default="*.phys",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):
        # Open Blender's normal save-file browser.
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        # Make sure a filepath was selected.
        filepath = self.filepath.strip()

        if not filepath:
            self.report(
                {'ERROR'},
                "No output .phys file selected."
            )
            return {'CANCELLED'}

        path = Path(filepath)

        # Always use .phys extension.
        if path.suffix.casefold() != ".phys":
            path = path.with_suffix(".phys")

        objects = selected_mesh_objects(context)

        if not objects:
            self.report(
                {'ERROR'},
                "Select at least one mesh object to export."
            )
            return {'CANCELLED'}

        try:
            mesh_count, triangle_count = write_phys(
                path,
                objects
            )

            self.report(
                {'INFO'},
                f"Exported {path.name}: "
                f"{mesh_count} collision meshes, "
                f"{triangle_count} triangles"
            )

            return {'FINISHED'}

        except Exception as exc:
            self.report(
                {'ERROR'},
                str(exc)
            )

            print(
                "Stormworks .phys export failed:",
                exc
            )

            return {'CANCELLED'}


def menu_func_export(self, context):
    self.layout.operator(
        EXPORT_OT_stormworks_phys.bl_idname,
        text="Stormworks Physics (.phys)",
    )


def register():
    bpy.utils.register_class(
        EXPORT_OT_stormworks_phys
    )

    bpy.types.TOPBAR_MT_file_export.append(
        menu_func_export
    )


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(
        menu_func_export
    )

    bpy.utils.unregister_class(
        EXPORT_OT_stormworks_phys
    )


if __name__ == "__main__":
    register()