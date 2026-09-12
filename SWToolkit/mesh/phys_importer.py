import bpy
import struct

from pathlib import Path

from bpy.props import StringProperty, CollectionProperty
from bpy.types import Operator, OperatorFileListElement


PHYS_FORMAT_VERSION = 2


class Reader:

    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read(self, fmt):
        size = struct.calcsize("<" + fmt)

        if self.pos + size > len(self.data):
            raise ValueError(
                f"Unexpected end of file at 0x{self.pos:X}; "
                f"needed {size} bytes, file size is {len(self.data)}."
            )

        value = struct.unpack_from(
            "<" + fmt,
            self.data,
            self.pos
        )

        self.pos += size

        return value[0] if len(value) == 1 else value

    def read_bytes(self, count):

        if self.pos + count > len(self.data):
            raise ValueError(
                f"Unexpected end of file at 0x{self.pos:X}; "
                f"needed {count} bytes, file size is {len(self.data)}."
            )

        value = self.data[
            self.pos:self.pos + count
        ]

        self.pos += count

        return value


def stormworks_to_blender(position):
    """Convert a Stormworks position to Blender coordinates."""

    sw_x, sw_y, sw_z = position

    return (
        -sw_x,
        -sw_z,
        sw_y
    )


def read_phys(filepath):

    data = Path(filepath).read_bytes()
    reader = Reader(data)

    # Magic
    if reader.read_bytes(4) != b"phys":
        raise ValueError(
            "Not a Stormworks physics file: "
            "expected 'phys' magic."
        )

    # Version
    version = reader.read("H")

    if version != PHYS_FORMAT_VERSION:
        raise ValueError(
            f"Unsupported .phys version {version}; "
            f"expected {PHYS_FORMAT_VERSION}."
        )

    # Collision mesh count
    mesh_count = reader.read("H")

    collision_meshes = []

    for mesh_index in range(mesh_count):

        vertex_count = reader.read("H")

        if vertex_count % 3 != 0:
            raise ValueError(
                f"Collision mesh {mesh_index} has "
                f"{vertex_count} vertices; "
                "the count must be divisible by 3."
            )

        vertices = [
            stormworks_to_blender(
                reader.read("3f")
            )
            for _ in range(vertex_count)
        ]

        trailing_zero = reader.read("H")

        if trailing_zero != 0:
            print(
                f"Stormworks .phys importer: "
                f"collision mesh {mesh_index} has "
                f"non-zero trailing field "
                f"{trailing_zero}."
            )

        collision_meshes.append({
            "vertices": vertices,
            "trailing_zero": trailing_zero,
        })

    # Check for unexpected trailing data
    if reader.pos != len(data):
        print(
            f"Stormworks .phys importer: "
            f"{len(data) - reader.pos} trailing bytes "
            "after collision meshes."
        )

    return version, collision_meshes


def create_collision_objects(
    filepath,
    collision_meshes
):

    base_name = Path(filepath).stem
    objects = []

    for mesh_index, collision_mesh in enumerate(
        collision_meshes
    ):

        vertices = collision_mesh["vertices"]

        faces = [
            (index, index + 1, index + 2)
            for index in range(
                0,
                len(vertices),
                3
            )
        ]

        name = (
            f"{base_name}_collision_"
            f"{mesh_index:02d}"
        )

        mesh = bpy.data.meshes.new(name)

        mesh.from_pydata(
            vertices,
            [],
            faces
        )

        mesh.update()

        obj = bpy.data.objects.new(
            name,
            mesh
        )

        bpy.context.collection.objects.link(obj)

        obj.display_type = 'SOLID'

        obj["stormworks_phys_mesh_index"] = (
            mesh_index
        )

        obj["stormworks_phys_trailing_zero"] = (
            collision_mesh["trailing_zero"]
        )

        objects.append(obj)

    return objects


class IMPORT_OT_stormworks_phys(Operator):

    bl_idname = "import_scene.stormworks_phys"
    bl_label = "Import Stormworks Physics"
    bl_description = "Import Stormworks .phys file(s)"
    bl_options = {'REGISTER', 'UNDO'}

    directory: StringProperty(
        subtype='DIR_PATH',
    )

    files: CollectionProperty(
        name="Files",
        type=OperatorFileListElement,
    )

    filter_glob: StringProperty(
        default="*.phys",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):

        self.files.clear()
        self.directory = ""

        context.window_manager.fileselect_add(self)

        return {'RUNNING_MODAL'}

    def execute(self, context):

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(
                mode='OBJECT'
            )

        if not self.files:
            self.report(
                {'ERROR'},
                "No .phys files selected."
            )

            return {'CANCELLED'}

        imported = 0
        total_collision_meshes = 0
        total_triangles = 0

        bpy.ops.object.select_all(
            action='DESELECT'
        )

        for file in self.files:

            filepath = (
                Path(self.directory) /
                file.name
            )

            try:

                _, collision_meshes = read_phys(
                    filepath
                )

                objects = create_collision_objects(
                    filepath,
                    collision_meshes
                )

                for obj in objects:
                    obj.select_set(True)

                total_collision_meshes += len(
                    objects
                )

                total_triangles += sum(
                    len(mesh["vertices"]) // 3
                    for mesh in collision_meshes
                )

                imported += 1

            except Exception as exc:

                self.report(
                    {'WARNING'},
                    f"Failed to import "
                    f"{file.name}: {exc}",
                )

                print(
                    f"Stormworks .phys import failed "
                    f"for {file.name}:",
                    exc,
                )

        if imported == 0:
            return {'CANCELLED'}

        # Make the first imported object active
        selected_objects = [
            obj
            for obj in context.selected_objects
            if obj.type == 'MESH'
        ]

        if selected_objects:
            context.view_layer.objects.active = (
                selected_objects[0]
            )

        self.report(
            {'INFO'},
            f"Imported {imported} .phys file(s): "
            f"{total_collision_meshes} collision meshes, "
            f"{total_triangles} triangles",
        )

        return {'FINISHED'}


def menu_func_import(self, context):

    self.layout.operator(
        IMPORT_OT_stormworks_phys.bl_idname,
        text="Stormworks Physics (.phys)",
    )


def register():

    bpy.utils.register_class(
        IMPORT_OT_stormworks_phys
    )

    bpy.types.TOPBAR_MT_file_import.append(
        menu_func_import
    )


def unregister():

    bpy.types.TOPBAR_MT_file_import.remove(
        menu_func_import
    )

    bpy.utils.unregister_class(
        IMPORT_OT_stormworks_phys
    )