import bpy
import struct
import mathutils
import math
import os
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty


# --------------------------
# Helper functions
# --------------------------
def safe_unpack(fmt, data, offset):
    size = struct.calcsize(fmt)
    if offset + size > len(data):
        return None, offset
    return struct.unpack_from(fmt, data, offset), offset + size


def srgb_to_linear(c):
    """Convert a single sRGB channel (0.0–1.0) to linear light.
    The .anim file stores raw sRGB bytes; Blender FLOAT_COLOR attributes are
    linear, so we must un-gamma on import and re-gamma on export."""
    c = max(0.0, min(1.0, c))
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def safe_decode(data, offset, length, encoding='ascii'):
    try:
        return data[offset:offset + length].decode(encoding)
    except UnicodeDecodeError:
        return data[offset:offset + length].decode('latin-1')


# --------------------------
# Core import logic
# --------------------------
def import_anim(anim_path, context):
    with open(anim_path, 'rb') as f:
        data = f.read()

    offset = 0

    # --- File header ---
    magic = data[offset:offset + 4]
    offset += 4
    if magic != b'anim':
        raise ValueError("Not a valid .anim file")

    res, offset = safe_unpack("<I", data, offset)
    file_unknown = res[0]

    res, offset = safe_unpack("<I", data, offset)
    submesh_count = res[0]

    print(f"[AnimImporter] Header: unknown={file_unknown}, submesh_count={submesh_count}")

    # --- Submeshes ---
    all_vertices = []
    all_triangles = []
    vertex_global_offset = 0
    submesh_face_ranges = []
    submesh_unknown_headers = []

    for si in range(submesh_count):
        print(f"[AnimImporter] Parsing submesh {si} at offset {offset}")
        unknown_header = data[offset:offset + 10]
        submesh_unknown_headers.append(unknown_header)
        offset += 10

        res, offset = safe_unpack("<I", data, offset)
        vertex_section_size = res[0]
        vertex_section_start = offset
        vertex_section_end = vertex_section_start + vertex_section_size

        local_vertices = []
        while offset + 52 <= vertex_section_end:
            res, offset = safe_unpack("<3f", data, offset)
            x, y, z = res
            res, offset = safe_unpack("<4B", data, offset)
            r, g, b, a = res
            res, offset = safe_unpack("<2f", data, offset)
            u, v = res
            res, offset = safe_unpack("<3f", data, offset)
            nx, ny, nz = res
            res, offset = safe_unpack("<2f", data, offset)
            b1f, b2f = res
            res, offset = safe_unpack("<2f", data, offset)
            w1, w2 = res

            bone1 = int(b1f)
            bone2 = int(b2f)

            # SW → Blender: negate X and Y
            local_vertices.append({
                'pos': (-x, -y, z),
                'color': (
                    srgb_to_linear(r / 255.0),
                    srgb_to_linear(g / 255.0),
                    srgb_to_linear(b / 255.0),
                    a / 255.0,  # alpha is not gamma-corrected
                ),
                'uv': (u, v),
                'normal': (-nx, -ny, nz),
                'bones': (bone1, bone2),
                'weights': (w1, w2)
            })

        offset = vertex_section_end

        res, offset = safe_unpack("<I", data, offset)
        tri_section_size = res[0]
        tri_section_start = offset
        tri_section_end = tri_section_start + tri_section_size

        local_triangles = []
        while offset + 12 <= tri_section_end:
            res, offset = safe_unpack("<3I", data, offset)
            i1, i2, i3 = res
            local_triangles.append((
                i1 + vertex_global_offset,
                i2 + vertex_global_offset,
                i3 + vertex_global_offset
            ))

        offset = tri_section_end

        start_idx = len(all_triangles)
        all_triangles.extend(local_triangles)
        end_idx = len(all_triangles)
        submesh_face_ranges.append((si, start_idx, end_idx))

        all_vertices.extend(local_vertices)
        vertex_global_offset += len(local_vertices)

        print(f"[AnimImporter] Submesh {si}: {len(local_vertices)} verts, {len(local_triangles)} faces")

    # --- Bones ---
    res, offset = safe_unpack("<I", data, offset)
    total_bones = res[0] if res else 0
    bones = []

    for bi in range(total_bones):
        res, offset = safe_unpack("<H", data, offset)
        name_len = res[0]
        name = safe_decode(data, offset, name_len)
        offset += name_len
        res, offset = safe_unpack("<12f", data, offset)
        matrix = res
        res, offset = safe_unpack("<I", data, offset)
        parent_id = res[0]
        res, offset = safe_unpack("<I", data, offset)
        child_count = res[0]
        children = []
        for _ in range(child_count):
            res, offset = safe_unpack("<I", data, offset)
            children.append(res[0])
        bones.append({
            'name': name,
            'matrix': matrix,
            'parent': parent_id,
            'children': children
        })

    print(f"[AnimImporter] Total bones: {len(bones)}")

    # --- World positions ---
    world_positions = {}

    def get_world_position(idx):
        if idx in world_positions:
            return world_positions[idx]
        b = bones[idx]
        mat = b['matrix']
        # SW → Blender: negate X and Y
        head_local = mathutils.Vector((-mat[9], -mat[10], mat[11]))
        if b['parent'] == 0xFFFFFFFF:
            world_positions[idx] = head_local
        else:
            world_positions[idx] = get_world_position(b['parent']) + head_local
        return world_positions[idx]

    for idx in range(len(bones)):
        get_world_position(idx)

    # --- Cleanup old data ---
    base_name = os.path.splitext(os.path.basename(anim_path))[0]
    for datablock in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures):
        if base_name in datablock:
            datablock.remove(datablock[base_name])
    if f"{base_name}_Armature" in bpy.data.armatures:
        bpy.data.armatures.remove(bpy.data.armatures[f"{base_name}_Armature"])
    if f"{base_name}_ArmatureObj" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[f"{base_name}_ArmatureObj"])

    # --- Create Armature ---
    arm_data = bpy.data.armatures.new(f"{base_name}_Armature")
    arm_obj = bpy.data.objects.new(f"{base_name}_ArmatureObj", arm_data)
    context.collection.objects.link(arm_obj)
    context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    edit_bones = arm_obj.data.edit_bones
    bone_refs = {}
    for idx, b in enumerate(bones):
        eb = edit_bones.new(b['name'])
        bone_refs[idx] = eb
        head = world_positions[idx]
        eb.head = head
        if b['children']:
            cx = cy = cz = 0.0
            for cidx in b['children']:
                c = world_positions[cidx]
                cx += c.x
                cy += c.y
                cz += c.z
            n = len(b['children'])
            eb.tail = mathutils.Vector((cx / n, cy / n, cz / n))
        else:
            eb.tail = head + mathutils.Vector((0, 0, 0.05))

    for idx, b in enumerate(bones):
        if b['parent'] != 0xFFFFFFFF:
            bone_refs[idx].parent = bone_refs[b['parent']]

    bpy.ops.object.mode_set(mode='OBJECT')
    print("[AnimImporter] ✅ Armature created")

    # --- Create Mesh ---
    mesh_data = bpy.data.meshes.new(base_name)
    mesh_obj = bpy.data.objects.new(base_name, mesh_data)
    context.collection.objects.link(mesh_obj)

    verts = [v['pos'] for v in all_vertices]
    mesh_data.from_pydata(verts, [], all_triangles)
    mesh_data.update()
    print("[AnimImporter] ✅ Mesh created")

    # --- Materials per submesh ---
    # Submesh 0 is glass if there are multiple submeshes, otherwise default
    for si, start, end in submesh_face_ranges:
        if submesh_count > 1 and si == 0:
            mat_name = "glass"
            glass_mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
            glass_mat.use_nodes = True
            bsdf = glass_mat.node_tree.nodes.get("Principled BSDF")
            if bsdf and "Transmission" in bsdf.inputs:
                bsdf.inputs["Transmission"].default_value = 1.0
            mesh_data.materials.append(glass_mat)
        else:
            mat_name = f"submesh_{si}"
            mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
            mesh_data.materials.append(mat)

    for si, start, end in submesh_face_ranges:
        for fi in range(start, end):
            mesh_data.polygons[fi].material_index = si

    # --- Vertex colors ---
    if "Col" in mesh_data.color_attributes:
        color_layer = mesh_data.color_attributes["Col"]
    else:
        color_layer = mesh_data.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')

    for i, v in enumerate(all_vertices):
        color_layer.data[i].color = v['color']

    print("[AnimImporter] 🎨 Vertex colors applied")

    # --- Vertex groups & weights ---
    for idx, b in enumerate(bones):
        mesh_obj.vertex_groups.new(name=b['name'])

    for v_idx, v in enumerate(all_vertices):
        b1, b2 = v['bones']
        w1, w2 = v['weights']
        if 0 <= b1 < len(bones) and w1 > 0:
            mesh_obj.vertex_groups[bones[b1]['name']].add([v_idx], w1, 'REPLACE')
        if 0 <= b2 < len(bones) and w2 > 0:
            mesh_obj.vertex_groups[bones[b2]['name']].add([v_idx], w2, 'REPLACE')

    # --- Parent mesh to armature (object parent + armature modifier) ---
    mesh_obj.parent = arm_obj
    mesh_obj.parent_type = 'OBJECT'
    mod = mesh_obj.modifiers.new("ArmatureMod", 'ARMATURE')
    mod.object = arm_obj

    # --- Store metadata on the mesh object for export ---
    mesh_obj["anim_source_path"] = anim_path
    mesh_obj["anim_file_unknown"] = file_unknown
    mesh_obj["anim_submesh_count"] = submesh_count

    # Store per-submesh unknown headers as a flat byte string in custom props
    # (Blender custom props don't support bytes directly, store as list of ints)
    flat_headers = []
    for h in submesh_unknown_headers:
        flat_headers.extend(list(h))
    mesh_obj["anim_submesh_headers"] = flat_headers

    # --- Coordinate space correction ---
    # Set transforms on armature, then apply to both armature and mesh.
    arm_obj.scale.x = -1.0
    arm_obj.rotation_euler.x = math.radians(-90)
    arm_obj.rotation_euler.z = math.radians(180)

    # Apply armature transform
    context.view_layer.objects.active = arm_obj
    bpy.ops.object.select_all(action='DESELECT')
    arm_obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Apply mesh transform
    context.view_layer.objects.active = mesh_obj
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Flip normals on the mesh data (SW winding is opposite Blender)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode='OBJECT')

    # Restore active to armature
    context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    print("[AnimImporter] 🎉 Import complete!")
    return mesh_obj, arm_obj


# --------------------------
# Operator
# --------------------------
class ANIMIO_OT_import(bpy.types.Operator, ImportHelper):
    bl_idname = "animio.import_anim"
    bl_label = "Import .anim"
    bl_description = "Import a Stormworks .anim file into Blender"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".anim"
    filter_glob: StringProperty(default="*.anim", options={'HIDDEN'})

    def execute(self, context):
        try:
            mesh_obj, arm_obj = import_anim(self.filepath, context)
            self.report({'INFO'}, f"Imported: {os.path.basename(self.filepath)}")
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        return {'FINISHED'}


# --------------------------
# Registration
# --------------------------
classes = (ANIMIO_OT_import,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)