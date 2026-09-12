import bpy
import struct

from pathlib import Path
from bpy.props import StringProperty, EnumProperty
from bpy.types import Operator


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


def stormworks_to_blender(vector):
    """Convert a Stormworks vector to Blender coordinates."""

    sw_x, sw_y, sw_z = vector

    return (
        -sw_x,
        -sw_z,
        sw_y
    )


def read_mesh(filepath):

    data = Path(filepath).read_bytes()

    r = Reader(data)

    magic = r.read_bytes(4)

    if magic != b"mesh":
        raise ValueError(
            f"Not a Stormworks mesh: magic is {magic!r}"
        )

    header_unknown = r.read("I")
    vertex_count = r.read("H")
    vertex_unknown = r.read("I")

    vertices = []
    colors = []
    normals = []

    for _ in range(vertex_count):

        pos = r.read("3f")
        color_i = r.read("I")
        normal = r.read("3f")

        color = (
            ((color_i >> 0) & 0xFF) / 255.0,
            ((color_i >> 8) & 0xFF) / 255.0,
            ((color_i >> 16) & 0xFF) / 255.0,
            ((color_i >> 24) & 0xFF) / 255.0,
        )

        vertices.append(
            stormworks_to_blender(pos)
        )

        colors.append(color)

        normals.append(
            stormworks_to_blender(normal)
        )

    index_count = r.read("I")

    if index_count % 3 != 0:
        raise ValueError(
            f"Index count {index_count} is not divisible by 3."
        )

    indices = [
        r.read("H")
        for _ in range(index_count)
    ]

    for i in indices:

        if i >= vertex_count:
            raise ValueError(
                f"Index {i} refers to vertex {i}, "
                f"but vertex count is {vertex_count}."
            )

    submesh_count = r.read("H")

    submeshes = []

    for _ in range(submesh_count):

        index_start = r.read("I")
        index_length = r.read("I")
        shader_id = r.read("I")

        bounds_min = stormworks_to_blender(
            r.read("3f")
        )

        bounds_max = stormworks_to_blender(
            r.read("3f")
        )

        unknown16 = r.read("H")
        name_length = r.read("H")

        raw_name = r.read_bytes(
            name_length
        )

        try:
            name = raw_name.decode("utf-8")
        except UnicodeDecodeError:
            name = raw_name.decode("latin-1")

        unknown_vec = stormworks_to_blender(
            r.read("3f")
        )

        submeshes.append({
            "index_start": index_start,
            "index_length": index_length,
            "shader_id": shader_id,
            "bounds_min": bounds_min,
            "bounds_max": bounds_max,
            "unknown16": unknown16,
            "name": name,
            "unknown_vec": unknown_vec,
        })

    if r.pos != len(data):

        print(
            f"Stormworks importer: "
            f"{len(data) - r.pos} trailing bytes after submeshes."
        )

    return {
        "vertices": vertices,
        "colors": colors,
        "normals": normals,
        "indices": indices,
        "submeshes": submeshes,
        "header_unknown": header_unknown,
        "vertex_unknown": vertex_unknown,
    }


def shader_material(shader_id, name):

    # Some meshes store the shader ID in the upper 16 bits.
    shader_kind = shader_id

    if shader_id > 0xFFFF and shader_id & 0xFFFF == 0:
        shader_kind = shader_id >> 16

    shader_names = {
        0: "Opaque",
        1: "Glass",
        2: "Emissive",
        3: "Lava",
    }

    label = shader_names.get(
        shader_kind,
        f"Shader {shader_id}"
    )

    mat = bpy.data.materials.get(label)

    if mat is None:

        mat = bpy.data.materials.new(label)
        mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()

        out = nodes.new(
            "ShaderNodeOutputMaterial"
        )

        if shader_kind == 2:

            shader = nodes.new(
                "ShaderNodeEmission"
            )

            shader.inputs["Color"].default_value = (
                1,
                1,
                1,
                1
            )

            shader.inputs["Strength"].default_value = 3.0

        elif shader_kind == 1:

            shader = nodes.new(
                "ShaderNodeBsdfPrincipled"
            )

            shader.inputs["Base Color"].default_value = (
                1,
                1,
                1,
                1
            )

            shader.inputs["Roughness"].default_value = 0.5

            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = 'DITHERED'

            elif hasattr(mat, "blend_method"):
                mat.blend_method = 'BLEND'

        elif shader_kind == 3:

            shader = nodes.new(
                "ShaderNodeEmission"
            )

            shader.inputs["Color"].default_value = (
                1,
                0.12,
                0.01,
                1
            )

            shader.inputs["Strength"].default_value = 5.0

        else:

            shader = nodes.new(
                "ShaderNodeBsdfPrincipled"
            )

            shader.inputs["Base Color"].default_value = (
                1,
                1,
                1,
                1
            )

            shader.inputs["Roughness"].default_value = 0.5

        links.new(
            shader.outputs[0],
            out.inputs["Surface"]
        )

    return mat


def shader_name_from_id(shader_id):

    shader_kind = shader_id

    if shader_id > 0xFFFF and shader_id & 0xFFFF == 0:
        shader_kind = shader_id >> 16

    return {
        0: "Opaque",
        1: "Glass",
        2: "Emissive",
        3: "Lava",
    }.get(
        shader_kind,
        f"Shader {shader_id}"
    )


def create_shader_vertex_groups(obj, mesh, indices, submeshes):

    shader_groups = {}

    for sm in submeshes:

        shader_name = shader_name_from_id(
            sm["shader_id"]
        )

        # Create the group once.
        if shader_name not in shader_groups:

            shader_groups[shader_name] = (
                obj.vertex_groups.new(
                    name=shader_name
                )
            )

        group = shader_groups[shader_name]

        start = sm["index_start"]
        end = start + sm["index_length"]

        submesh_indices = indices[start:end]

        # Remove duplicates while preserving order.
        vertex_indices = list(
            dict.fromkeys(submesh_indices)
        )

        if vertex_indices:

            group.add(
                vertex_indices,
                1.0,
                'REPLACE'
            )


def create_object(
    filepath,
    mesh_data,
    shader_source
):

    vertices = mesh_data["vertices"]
    colors = mesh_data["colors"]
    normals = mesh_data["normals"]
    indices = mesh_data["indices"]
    submeshes = mesh_data["submeshes"]

    faces = [
        (
            indices[i],
            indices[i + 1],
            indices[i + 2]
        )
        for i in range(
            0,
            len(indices),
            3
        )
    ]

    mesh_name = Path(filepath).stem

    mesh = bpy.data.meshes.new(
        mesh_name
    )

    mesh.from_pydata(
        vertices,
        [],
        faces
    )

    mesh.update()

    obj = bpy.data.objects.new(
        mesh_name,
        mesh
    )

    bpy.context.collection.objects.link(obj)

    # --------------------------------------------------------
    # Custom Normals
    # --------------------------------------------------------

    try:

        mesh.normals_split_custom_set_from_vertices(
            normals
        )

        mesh.use_auto_smooth = True

    except Exception as exc:

        print(
            "Stormworks importer: "
            "could not apply custom normals:",
            exc
        )

    # --------------------------------------------------------
    # Vertex Colors
    # --------------------------------------------------------

    try:

        color_attr = mesh.color_attributes.new(
            name="Col",
            type='FLOAT_COLOR',
            domain='POINT'
        )

        for vertex_index, color in enumerate(colors):

            color_attr.data[
                vertex_index
            ].color = color

    except Exception as exc:

        print(
            "Stormworks importer: "
            "could not create color attribute:",
            exc
        )

    # --------------------------------------------------------
    # Materials
    # --------------------------------------------------------

    materials = {}

    if shader_source in {
        'MATERIALS',
        'BOTH'
    }:

        for sm in submeshes:

            sid = sm["shader_id"]

            if sid not in materials:

                materials[sid] = shader_material(
                    sid,
                    sm["name"]
                )

                mesh.materials.append(
                    materials[sid]
                )

    # --------------------------------------------------------
    # Assign Materials to Faces
    # --------------------------------------------------------

    if shader_source in {
        'MATERIALS',
        'BOTH'
    }:

        for sm in submeshes:

            sid = sm["shader_id"]

            material_index = list(
                materials.keys()
            ).index(sid)

            start = sm["index_start"]
            end = start + sm["index_length"]

            if start % 3 != 0 or end % 3 != 0:

                print(
                    f"Stormworks importer: "
                    f"submesh '{sm['name']}' has "
                    f"non-triangle-aligned index range "
                    f"{start}:{end}"
                )

            for face_index in range(
                start // 3,
                min(
                    end // 3,
                    len(mesh.polygons)
                )
            ):

                mesh.polygons[
                    face_index
                ].material_index = material_index

    # --------------------------------------------------------
    # Vertex Group Shaders
    # --------------------------------------------------------

    if shader_source in {
        'VERTEX_GROUPS',
        'BOTH'
    }:

        create_shader_vertex_groups(
            obj,
            mesh,
            indices,
            submeshes
        )

    # --------------------------------------------------------
    # Stormworks Metadata
    # --------------------------------------------------------

    obj["stormworks_header_unknown"] = (
        mesh_data["header_unknown"]
    )

    obj["stormworks_vertex_unknown"] = (
        mesh_data["vertex_unknown"]
    )

    for i, sm in enumerate(submeshes):

        obj[
            f"submesh_{i}_name"
        ] = sm["name"]

        obj[
            f"submesh_{i}_shader_id"
        ] = sm["shader_id"]

    return obj


class IMPORT_OT_stormworks_mesh(Operator):

    bl_idname = "import_scene.stormworks_mesh"
    bl_label = "Import Stormworks .mesh"
    bl_description = "Import .mesh file(s)"
    bl_options = {'REGISTER', 'UNDO'}

    directory: StringProperty(
        subtype='DIR_PATH'
    )

    files: bpy.props.CollectionProperty(
        name="Files",
        type=bpy.types.OperatorFileListElement
    )

    filter_glob: StringProperty(
        default="*.mesh",
        options={'HIDDEN'}
    )

    shader_source: EnumProperty(
        name="Shader Source",
        description="Choose how Stormworks shader information is imported",
        items=[
            (
                'MATERIALS',
                "Materials",
                "Create and assign Blender materials from Stormworks shaders"
            ),
            (
                'VERTEX_GROUPS',
                "Vertex Groups",
                "Create Opaque, Glass, Emissive, and Lava vertex groups"
            ),
            (
                'BOTH',
                "Both",
                "Create both shader materials and shader vertex groups"
            ),
        ],
        default='MATERIALS'
    )

    def invoke(self, context, event):

        self.files.clear()
        self.directory = ""

        context.window_manager.fileselect_add(
            self
        )

        return {'RUNNING_MODAL'}

    def draw(self, context):

        layout = self.layout

        layout.prop(
            self,
            "shader_source"
        )

    def execute(self, context):

        if context.mode != 'OBJECT':

            bpy.ops.object.mode_set(
                mode='OBJECT'
            )

        print("====================================")
        print("Stormworks Mesh Import")
        print("Directory:", self.directory)
        print("Selected files:", len(self.files))
        print("Shader source:", self.shader_source)

        for file in self.files:

            print(
                "  -",
                file.name
            )

        print("====================================")

        if not self.files:

            self.report(
                {'ERROR'},
                "No mesh files selected."
            )

            return {'CANCELLED'}

        imported_objects = []
        failed_files = []

        for file in self.files:

            filepath = (
                Path(self.directory)
                / file.name
            )

            try:

                print(
                    f"Importing: {filepath}"
                )

                parsed = read_mesh(
                    filepath
                )

                obj = create_object(
                    filepath,
                    parsed,
                    self.shader_source
                )

                imported_objects.append(
                    obj
                )

                print(
                    f"Imported {filepath.name}: "
                    f"{len(parsed['vertices'])} vertices, "
                    f"{len(parsed['indices']) // 3} triangles"
                )

            except Exception as exc:

                failed_files.append(
                    f"{filepath.name}: {exc}"
                )

                print(
                    f"Failed to import "
                    f"{filepath.name}:",
                    exc
                )

        if not imported_objects:

            self.report(
                {'ERROR'},
                "Failed to import any mesh files."
            )

            return {'CANCELLED'}

        # Select all imported objects

        bpy.ops.object.select_all(
            action='DESELECT'
        )

        for obj in imported_objects:

            obj.select_set(True)

        context.view_layer.objects.active = (
            imported_objects[-1]
        )

        if failed_files:

            self.report(
                {'WARNING'},
                f"Imported "
                f"{len(imported_objects)} files, "
                f"{len(failed_files)} failed."
            )

        else:

            self.report(
                {'INFO'},
                f"Imported "
                f"{len(imported_objects)} mesh files."
            )

        return {'FINISHED'}


def menu_func_import(self, context):

    self.layout.operator(
        IMPORT_OT_stormworks_mesh.bl_idname,
        text="Stormworks Mesh (.mesh)"
    )


def register():

    bpy.utils.register_class(
        IMPORT_OT_stormworks_mesh
    )

    bpy.types.TOPBAR_MT_file_import.append(
        menu_func_import
    )


def unregister():

    bpy.types.TOPBAR_MT_file_import.remove(
        menu_func_import
    )

    bpy.utils.unregister_class(
        IMPORT_OT_stormworks_mesh
    )


if __name__ == "__main__":
    register()