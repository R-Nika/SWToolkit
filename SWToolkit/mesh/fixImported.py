import bpy
import bmesh

from bpy.props import BoolProperty
from bpy.types import Operator

FIX_VERSION = 1
FIX_KEY = "sw_import_fix"
SW_MARKER = "stormworks_header_unknown"


def srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def fix_colors(mesh):
    attr = mesh.color_attributes.get("Col")

    if attr is None:
        return False

    for item in attr.data:
        r, g, b, a = item.color
        item.color = (
            srgb_to_linear(r),
            srgb_to_linear(g),
            srgb_to_linear(b),
            a,
        )

    return True


def fix_winding(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()


def fix_shading(obj, mesh):
    # The old custom normals were wrong, drop them and shade by angle.
    try:
        with bpy.context.temp_override(
            object=obj,
            active_object=obj,
            selected_objects=[obj],
        ):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass

    mesh.polygons.foreach_set(
        "use_smooth",
        [True] * len(mesh.polygons)
    )

    if hasattr(mesh, "use_auto_smooth"):
        mesh.use_auto_smooth = True
        mesh.auto_smooth_angle = 0.785398
    elif hasattr(bpy.ops.object, "shade_smooth_by_angle"):
        try:
            with bpy.context.temp_override(
                object=obj,
                active_object=obj,
                selected_objects=[obj],
            ):
                bpy.ops.object.shade_smooth_by_angle(angle=0.785398)
        except Exception as exc:
            print("Stormworks fix: shade by angle failed:", exc)

    mesh.update()


def fix_materials(mesh):
    for mat in mesh.materials:
        if mat is None or not mat.use_nodes:
            continue

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        if any(n.bl_idname == "ShaderNodeVertexColor" for n in nodes):
            continue

        if mat.name.startswith("Lava"):
            continue

        target = None
        socket = None

        for n in nodes:
            if n.bl_idname == "ShaderNodeBsdfPrincipled":
                target, socket = n, "Base Color"
            elif n.bl_idname == "ShaderNodeEmission":
                target, socket = n, "Color"

        if target is None:
            continue

        vcol = nodes.new("ShaderNodeVertexColor")
        vcol.layer_name = "Col"
        links.new(vcol.outputs["Color"], target.inputs[socket])


def show_vertex_colors(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D' and space.shading.type == 'SOLID':
                    space.shading.color_type = 'VERTEX'


class SWTOOLKIT_OT_fix_imported(Operator):

    bl_idname = "sw_toolkit.fix_imported_meshes"
    bl_label = "Fix Imported Meshes"
    bl_description = (
        "Fix colors, face direction, shading and materials of "
        ".mesh objects that were imported with an older version"
    )
    bl_options = {'REGISTER', 'UNDO'}

    only_selected: BoolProperty(
        name="Only Selected",
        description="Only fix selected objects, otherwise the whole project",
        default=False,
    )

    def execute(self, context):

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        pool = (
            context.selected_objects
            if self.only_selected
            else bpy.data.objects
        )

        fixed = 0
        skipped = 0

        for obj in pool:

            if obj.type != 'MESH' or SW_MARKER not in obj:
                continue

            if obj.get(FIX_KEY, 0) >= FIX_VERSION:
                skipped += 1
                continue

            mesh = obj.data

            if mesh.users > 1 and mesh.get(FIX_KEY, 0) >= FIX_VERSION:
                obj[FIX_KEY] = FIX_VERSION
                skipped += 1
                continue

            fix_colors(mesh)
            fix_winding(mesh)
            fix_shading(obj, mesh)
            fix_materials(mesh)

            mesh[FIX_KEY] = FIX_VERSION
            obj[FIX_KEY] = FIX_VERSION
            fixed += 1

        show_vertex_colors(context)

        self.report(
            {'INFO'},
            f"Fixed {fixed} objects, {skipped} already fine."
        )

        return {'FINISHED'}


def register():
    bpy.utils.register_class(SWTOOLKIT_OT_fix_imported)


def unregister():
    bpy.utils.unregister_class(SWTOOLKIT_OT_fix_imported)
