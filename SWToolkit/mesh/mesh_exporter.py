import bpy
import struct

from collections import OrderedDict
from pathlib import Path

from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
)
from bpy.types import Operator


# Stormworks multiplies material lighting by its per-vertex color.
# Leave this False for normal model exports.
EXPORT_VERTEX_COLORS = True


# Stormworks shader IDs
SHADER_IDS = {
    "opaque": 0x00000000,
    "glass": 0x00010000,
    "emissive": 0x00020000,
    "lava": 0x00030000,
}


# Verified from current Stormworks meshes.
MESH_FORMAT_VERSION = 0x00010007
MESH_SECONDARY_HEADER = 0x00000013


def blender_to_stormworks(vector):
    """Apply the verified Stormworks export transform."""
    x, y, z = vector
    return (-x, z, -y)


def blender_normal_to_stormworks(normal):
    """Convert normals using the verified Stormworks normal convention."""
    x, y, z = normal
    return (-x, z, -y)


def shader_id_for_material(material):
    """Return the Stormworks shader ID based on material name."""
    if material is None:
        return None

    name = material.name.strip().casefold()
    return SHADER_IDS.get(name)


def color_for_loop(mesh, loop_index):
    """Read the active color attribute from either CORNER or POINT domain."""
    color_attr = mesh.color_attributes.active_color

    if not color_attr:
        return (1.0, 1.0, 1.0, 1.0)

    loop = mesh.loops[loop_index]

    if color_attr.domain == 'CORNER':
        return tuple(color_attr.data[loop_index].color)

    if color_attr.domain == 'POINT':
        return tuple(
            color_attr.data[loop.vertex_index].color
        )

    return (1.0, 1.0, 1.0, 1.0)


def pack_color(color):
    rgba = [
        max(0, min(255, round(component * 255.0)))
        for component in color
    ]

    return (
        rgba[0]
        | (rgba[1] << 8)
        | (rgba[2] << 16)
        | (rgba[3] << 24)
    )


def exported_color(mesh, loop_index):
    if not EXPORT_VERTEX_COLORS:
        return 0xFFFFFFFF

    return pack_color(
        color_for_loop(mesh, loop_index)
    )


def bounds_for_vertices(vertices):
    if not vertices:
        return (
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0)
        )

    return (
        tuple(
            min(vertex[axis] for vertex in vertices)
            for axis in range(3)
        ),
        tuple(
            max(vertex[axis] for vertex in vertices)
            for axis in range(3)
        ),
    )


def shader_id_for_vertex_group(obj, vertex_index):
    """
    Determine the Stormworks shader for a vertex.

    The vertex must belong to exactly one of the shader groups:
    Opaque, Glass, Emissive, Lava.
    """

    shader_group_names = {
        "Opaque": SHADER_IDS["opaque"],
        "Glass": SHADER_IDS["glass"],
        "Emissive": SHADER_IDS["emissive"],
        "Lava": SHADER_IDS["lava"],
    }

    matches = []

    for group_name, shader_id in shader_group_names.items():

        group = obj.vertex_groups.get(group_name)

        if group is None:
            continue

        try:
            weight = group.weight(vertex_index)
        except RuntimeError:
            weight = 0.0

        if weight > 0.0:
            matches.append(
                (group_name, shader_id)
            )

    if len(matches) == 0:
        raise ValueError(
            f"Vertex {vertex_index} does not belong to a shader "
            "vertex group. Expected Opaque, Glass, Emissive, or Lava."
        )

    if len(matches) > 1:
        names = ", ".join(
            match[0]
            for match in matches
        )

        raise ValueError(
            f"Vertex {vertex_index} belongs to multiple shader "
            f"vertex groups: {names}. "
            "Each vertex must belong to exactly one shader group."
        )

    return matches[0][1], matches[0][0]


def build_mesh_data(obj, use_shaders, shader_source):
    if obj.type != 'MESH':
        raise ValueError("The active object must be a mesh.")

    mesh = obj.data

    vertices = []
    vertex_lookup = {}

    submesh_indices = OrderedDict()

    # ------------------------------------------------------------
    # MATERIAL SHADER MODE
    # ------------------------------------------------------------

    if use_shaders and shader_source == 'MATERIALS':

        # Pre-create groups in Blender material-slot order.
        for material in mesh.materials:

            shader_id = shader_id_for_material(material)

            if shader_id is not None:
                submesh_indices.setdefault(
                    (shader_id, material.name),
                    {
                        "shader_id": shader_id,
                        "name": material.name,
                        "indices": []
                    },
                )

    # ------------------------------------------------------------
    # VERTEX GROUP SHADER MODE
    # ------------------------------------------------------------

    elif use_shaders and shader_source == 'VERTEX_GROUPS':

        # Groups are created when encountered during polygon processing.
        # This preserves the order in which shader types are encountered.
        pass

    # ------------------------------------------------------------
    # NO SHADERS
    # ------------------------------------------------------------

    else:

        # Everything goes into one Opaque submesh.
        submesh_indices.setdefault(
            (SHADER_IDS["opaque"], "Opaque"),
            {
                "shader_id": SHADER_IDS["opaque"],
                "name": "Opaque",
                "indices": []
            },
        )

    # ------------------------------------------------------------
    # PROCESS POLYGONS
    # ------------------------------------------------------------

    for polygon in mesh.polygons:

        if len(polygon.loop_indices) != 3:
            raise ValueError(
                f"Polygon {polygon.index} has "
                f"{len(polygon.loop_indices)} sides. "
                "Triangulate the mesh before exporting."
            )

        # --------------------------------------------------------
        # Determine shader for this triangle
        # --------------------------------------------------------

        if not use_shaders:

            shader_id = SHADER_IDS["opaque"]
            shader_name = "Opaque"

        elif shader_source == 'MATERIALS':

            material = (
                mesh.materials[polygon.material_index]
                if polygon.material_index < len(mesh.materials)
                else None
            )

            shader_id = shader_id_for_material(material)

            if shader_id is None:
                continue

            shader_name = material.name

        else:

            # Vertex Groups mode.
            #
            # All three vertices of the triangle must resolve to
            # the same shader group.

            triangle_shader_ids = []
            triangle_shader_names = []

            for loop_index in polygon.loop_indices:

                loop = mesh.loops[loop_index]

                vertex_shader_id, vertex_shader_name = (
                    shader_id_for_vertex_group(
                        obj,
                        loop.vertex_index
                    )
                )

                triangle_shader_ids.append(
                    vertex_shader_id
                )

                triangle_shader_names.append(
                    vertex_shader_name
                )

            if len(set(triangle_shader_ids)) != 1:
                raise ValueError(
                    f"Triangle {polygon.index} has vertices assigned "
                    "to different shader groups: "
                    f"{', '.join(triangle_shader_names)}. "
                    "All three vertices of a triangle must use "
                    "the same shader group."
                )

            shader_id = triangle_shader_ids[0]
            shader_name = triangle_shader_names[0]

        # --------------------------------------------------------
        # Get/create submesh
        # --------------------------------------------------------

        group_key = (
            shader_id,
            shader_name
        )

        if group_key not in submesh_indices:

            submesh_indices[group_key] = {
                "shader_id": shader_id,
                "name": shader_name,
                "indices": []
            }

        group = submesh_indices[group_key]

        # --------------------------------------------------------
        # Build triangle
        # --------------------------------------------------------

        triangle = []

        for loop_index in polygon.loop_indices:

            loop = mesh.loops[loop_index]

            loop_normal = mesh.vertices[
                loop.vertex_index
            ].normal

            vertex_index = vertex_lookup.get(
                loop.vertex_index
            )

            if vertex_index is None:

                vertex_index = len(vertices)

                vertex_lookup[
                    loop.vertex_index
                ] = vertex_index

                vertices.append(
                    (
                        blender_to_stormworks(
                            mesh.vertices[
                                loop.vertex_index
                            ].co
                        ),

                        exported_color(
                            mesh,
                            loop_index
                        ),

                        blender_normal_to_stormworks(
                            loop_normal
                        ),
                    )
                )

            triangle.append(vertex_index)

        # Keep Blender's loop order.
        group["indices"].extend(triangle)

    if len(vertices) > 0xFFFF:
        raise ValueError(
            f"Mesh has {len(vertices)} exported vertices; "
            ".mesh supports at most 65535."
        )

    return vertices, submesh_indices


def write_mesh(
    filepath,
    obj,
    use_shaders,
    shader_source
):

    vertices, submesh_groups = build_mesh_data(
        obj,
        use_shaders,
        shader_source
    )

    if not submesh_groups:
        raise ValueError(
            "No geometry was found to export."
        )

    ordered_groups = [
        group
        for group in submesh_groups.values()
        if group["indices"]
    ]

    if not ordered_groups:
        raise ValueError(
            "No geometry was found to export."
        )

    indices = [
        index
        for group in ordered_groups
        for index in group["indices"]
    ]

    if len(indices) > 0xFFFFFFFF:
        raise ValueError(
            "Too many indices for the .mesh format."
        )

    if len(ordered_groups) > 0xFFFF:
        raise ValueError(
            "Too many submeshes for the .mesh format."
        )

    output = bytearray()

    # Magic
    output += b"mesh"

    # Header
    output += struct.pack(
        "<IHI",
        MESH_FORMAT_VERSION,
        len(vertices),
        MESH_SECONDARY_HEADER
    )

    # Vertex data
    for position, color, normal in vertices:

        output += struct.pack(
            "<3fI3f",
            *position,
            color,
            *normal
        )

    # Index count
    output += struct.pack(
        "<I",
        len(indices)
    )

    # Indices
    output += (
        struct.pack(
            f"<{len(indices)}H",
            *indices
        )
        if indices
        else b""
    )

    # Submesh count
    output += struct.pack(
        "<H",
        len(ordered_groups)
    )

    index_start = 0

    for group in ordered_groups:

        shader_id = group["shader_id"]
        group_indices = group["indices"]

        referenced_vertices = [
            vertices[index][0]
            for index in group_indices
        ]

        bounds_min, bounds_max = bounds_for_vertices(
            referenced_vertices
        )

        # Stormworks uses an empty submesh-name field.
        raw_name = b""

        output += struct.pack(
            "<III",
            index_start,
            len(group_indices),
            shader_id
        )

        output += struct.pack(
            "<3f3fHH",
            *bounds_min,
            *bounds_max,
            0,
            len(raw_name)
        )

        output += raw_name

        # Per-submesh values
        output += struct.pack(
            "<3f",
            1.0,
            1.0,
            1.0
        )

        index_start += len(group_indices)

    # Required file footer
    output += struct.pack(
        "<H",
        0
    )

    Path(filepath).write_bytes(output)

    return (
        len(vertices),
        len(indices) // 3,
        len(ordered_groups)
    )


class EXPORT_OT_stormworks_mesh(Operator):

    bl_idname = "export_scene.stormworks_mesh"
    bl_label = "Export Stormworks Mesh"
    bl_description = "Export the selected object as .mesh file(s)"
    bl_options = {'REGISTER'}

    filename_ext = ".mesh"

    filter_glob: StringProperty(
        default="*.mesh",
        options={'HIDDEN'}
    )

    filepath: StringProperty(
        name="Mesh file path",
        description="Output path for the Stormworks .mesh file",
        subtype='FILE_PATH'
    )

    use_shaders: BoolProperty(
        name="Use Shaders",
        description=(
            "Use shader information when determining Stormworks "
            "submeshes"
        ),
        default=True
    )

    shader_source: EnumProperty(
        name="Shader Source",
        description="Where to get Stormworks shader information from",
        items=[
            (
                'MATERIALS',
                "Materials",
                "Get shader information from material names"
            ),
            (
                'VERTEX_GROUPS',
                "Vertex Groups",
                (
                    "Get shader information from Opaque, Glass, "
                    "Emissive, and Lava vertex groups"
                )
            ),
        ],
        default='MATERIALS'
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):

        layout = self.layout

        layout.prop(
            self,
            "use_shaders"
        )

        if self.use_shaders:

            layout.prop(
                self,
                "shader_source"
            )

    def execute(self, context):

        filepath = self.filepath.strip()

        if not filepath:
            self.report(
                {'ERROR'},
                "Enter an output .mesh file path."
            )
            return {'CANCELLED'}

        if context.active_object is None:
            self.report(
                {'ERROR'},
                "Select the mesh object to export."
            )
            return {'CANCELLED'}

        if context.active_object.type != 'MESH':
            self.report(
                {'ERROR'},
                "The active object must be a mesh."
            )
            return {'CANCELLED'}

        path = Path(filepath)

        if path.suffix.casefold() != ".mesh":
            path = path.with_suffix(".mesh")

        try:

            vertex_count, triangle_count, submesh_count = write_mesh(
                path,
                context.active_object,
                self.use_shaders,
                self.shader_source
            )

            self.report(
                {'INFO'},
                f"Exported {path.name}: "
                f"{vertex_count} vertices, "
                f"{triangle_count} triangles, "
                f"{submesh_count} submeshes"
            )

            return {'FINISHED'}

        except Exception as exc:

            self.report(
                {'ERROR'},
                str(exc)
            )

            print(
                "Stormworks mesh export failed:",
                exc
            )

            return {'CANCELLED'}


def menu_func_export(self, context):
    self.layout.operator(
        EXPORT_OT_stormworks_mesh.bl_idname,
        text="Stormworks Mesh (.mesh)"
    )


def register():

    bpy.utils.register_class(
        EXPORT_OT_stormworks_mesh
    )

    bpy.types.TOPBAR_MT_file_export.append(
        menu_func_export
    )


def unregister():

    bpy.types.TOPBAR_MT_file_export.remove(
        menu_func_export
    )

    bpy.utils.unregister_class(
        EXPORT_OT_stormworks_mesh
    )