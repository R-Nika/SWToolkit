import bpy
import struct
import math
import os
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty


# --------------------------
# Helper
# --------------------------
def linear_to_srgb(c):
    """Convert a linear light channel (0.0–1.0) to a sRGB byte (0–255).
    Blender FLOAT_COLOR attributes are linear; the .anim file expects sRGB bytes."""
    c = max(0.0, min(1.0, c))
    if c <= 0.0031308:
        srgb = c * 12.92
    else:
        srgb = 1.055 * (c ** (1.0 / 2.4)) - 0.055
    return int(srgb * 255 + 0.5)


# --------------------------
# Core export logic
# --------------------------
def export_anim(mesh_obj, output_path, context):
    """
    Export the selected mesh object back to a .anim file.

    The mesh object must have been imported via AnimImporter (so it carries
    the custom properties anim_source_path, anim_file_unknown,
    anim_submesh_count, anim_submesh_headers).

    The skeleton/animation tail of the original file is preserved verbatim.
    """

    # --- Recover metadata stored at import time ---
    source_path = mesh_obj.get("anim_source_path", None)
    file_unknown = mesh_obj.get("anim_file_unknown", 0)
    submesh_count = mesh_obj.get("anim_submesh_count", 1)
    flat_headers = mesh_obj.get("anim_submesh_headers", None)

    if source_path is None or not os.path.isfile(source_path):
        raise FileNotFoundError(
            "Could not find the original .anim source file. "
            "Make sure the object was imported with the AnimImporter and that "
            "the original file still exists at the same path."
        )

    # Rebuild per-submesh 10-byte unknown headers
    if flat_headers and len(flat_headers) == submesh_count * 10:
        submesh_unknown_headers = []
        for si in range(submesh_count):
            start = si * 10
            submesh_unknown_headers.append(bytes(flat_headers[start:start + 10]))
    else:
        # Fallback: read them fresh from the source file
        submesh_unknown_headers = _read_unknown_headers(source_path, submesh_count)

    # Read the skeleton+animation tail from the original file
    rest_data = _read_rest_data(source_path, submesh_count)

    mesh = mesh_obj.data

    # --- Vertex color layer ---
    color_layer = None
    if mesh.color_attributes:
        color_layer = mesh.color_attributes.active_color
        if color_layer and color_layer.domain != 'POINT':
            color_layer = None

    # --- Group polygons by submesh index, ignoring non-anim materials ---
    # Build a mapping from Blender material slot index -> anim submesh index.
    # Only materials named "glass" or "submesh_N" are recognised.
    # Everything else (e.g. colour materials from matToVert) maps to submesh 0
    # so the geometry is still exported rather than silently dropped.
    materials = mesh_obj.data.materials
    slot_to_submesh = {}
    for slot_idx, mat in enumerate(materials):
        if mat is None:
            slot_to_submesh[slot_idx] = 0
            continue
        name = mat.name.lower()
        if name == "glass":
            slot_to_submesh[slot_idx] = 0  # glass is always submesh 0
        elif name.startswith("submesh_"):
            try:
                slot_to_submesh[slot_idx] = int(name.split("_", 1)[1])
            except ValueError:
                slot_to_submesh[slot_idx] = 0
        else:
            slot_to_submesh[slot_idx] = 0  # unrecognised → default submesh

    material_polygons = {}
    for poly in mesh.polygons:
        si = slot_to_submesh.get(poly.material_index, 0)
        if si not in material_polygons:
            material_polygons[si] = []
        material_polygons[si].append(poly)

    # --- Build per-submesh vertex + triangle bytes ---
    new_submesh_data = []

    for si in range(submesh_count):
        polygons = material_polygons.get(si, [])

        if not polygons:
            new_submesh_data.append({'vertices': b'', 'triangles': b''})
            continue

        # Collect unique vertex indices used by this submesh's faces
        used_vertices = set()
        for poly in polygons:
            used_vertices.update(poly.vertices)

        # Build a local index mapping: global vertex idx -> submesh-local idx
        vertex_remap = {}
        ordered_vertices = []
        for gvi in used_vertices:
            vertex_remap[gvi] = len(ordered_vertices)
            ordered_vertices.append(gvi)

        vertices_bytes = b""
        for gvi in ordered_vertices:
            v = mesh.vertices[gvi]
            co = mesh_obj.matrix_world @ v.co
            normal = v.normal

            # Export transform: rotate X 90deg then scale X -1.
            # Verified: sw_x = -co.x, sw_y = -co.z, sw_z = co.y
            sw_x = -co.x
            sw_y = co.z
            sw_z = -co.y

            sw_nx = normal.x
            sw_ny = -normal.z
            sw_nz = normal.y

            # Vertex color
            if color_layer:
                c = color_layer.data[gvi].color
                color = (
                    linear_to_srgb(c[0]),
                    linear_to_srgb(c[1]),
                    linear_to_srgb(c[2]),
                    int(max(0.0, min(1.0, c[3])) * 255 + 0.5) if len(c) >= 4 else 255,  # alpha: no gamma
                )
            else:
                color = (255, 255, 255, 255)

            # UV — use first UV layer if present, else (0, 0)
            uv = (0.0, 0.0)
            if mesh.uv_layers.active:
                # UV is per-loop; use the first loop that references this vertex
                for poly in polygons:
                    for li, vi in zip(poly.loop_indices, poly.vertices):
                        if vi == gvi:
                            uv_data = mesh.uv_layers.active.data[li].uv
                            uv = (uv_data[0], uv_data[1])
                            break
                    else:
                        continue
                    break

            # Bone weights from vertex groups
            b1, b2, w1, w2 = 0, 0, 1.0, 0.0
            groups = sorted(v.groups, key=lambda g: g.weight, reverse=True)
            if len(groups) > 0:
                b1 = groups[0].group
                w1 = groups[0].weight
            if len(groups) > 1:
                b2 = groups[1].group
                w2 = groups[1].weight

            vertices_bytes += struct.pack(
                "<3f4B2f3f4f",
                sw_x, sw_y, sw_z,
                color[0], color[1], color[2], color[3],
                uv[0], uv[1],
                sw_nx, sw_ny, sw_nz,
                float(b1), float(b2),
                w1, w2,
            )

        tri_bytes = b""
        for poly in polygons:
            if len(poly.vertices) == 3:
                remapped = [vertex_remap[vi] for vi in poly.vertices]
                tri_bytes += struct.pack("<3I", *remapped)

        new_submesh_data.append({'vertices': vertices_bytes, 'triangles': tri_bytes})
        print(f"[AnimExporter] Submesh {si}: {len(ordered_vertices)} verts, {len(polygons)} tris")

    # --- Assemble the new file ---
    new_data = b'anim'
    new_data += struct.pack("<I", file_unknown)
    new_data += struct.pack("<I", submesh_count)

    for si in range(submesh_count):
        sd = new_submesh_data[si]
        new_data += submesh_unknown_headers[si]
        new_data += struct.pack("<I", len(sd['vertices']))
        new_data += sd['vertices']
        new_data += struct.pack("<I", len(sd['triangles']))
        new_data += sd['triangles']

    new_data += rest_data

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(new_data)

    print(f"[AnimExporter] ✅ Exported to: {output_path}")


# --------------------------
# Read helpers (parse source file minimally)
# --------------------------
def _read_unknown_headers(source_path, submesh_count):
    """Re-read only the 10-byte unknown headers from the source file."""
    with open(source_path, 'rb') as f:
        data = f.read()

    offset = 4  # skip magic
    offset += 4  # file_unknown
    offset += 4  # submesh_count

    headers = []
    for _ in range(submesh_count):
        headers.append(data[offset:offset + 10])
        offset += 10
        (vsz,) = struct.unpack_from("<I", data, offset)
        offset += 4 + vsz
        (tsz,) = struct.unpack_from("<I", data, offset)
        offset += 4 + tsz

    return headers


def _read_rest_data(source_path, submesh_count):
    """Return everything after the last submesh (bones + animation data)."""
    with open(source_path, 'rb') as f:
        data = f.read()

    offset = 4  # skip magic
    offset += 4  # file_unknown
    offset += 4  # submesh_count

    for _ in range(submesh_count):
        offset += 10  # unknown header
        (vsz,) = struct.unpack_from("<I", data, offset)
        offset += 4 + vsz
        (tsz,) = struct.unpack_from("<I", data, offset)
        offset += 4 + tsz

    return data[offset:]


# --------------------------
# Operator
# --------------------------
class ANIMIO_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = "animio.export_anim"
    bl_label = "Export .anim"
    bl_description = "Export the active mesh object back to a Stormworks .anim file"
    bl_options = {'REGISTER'}

    filename_ext = ".anim"
    filter_glob: StringProperty(default="*.anim", options={'HIDDEN'})

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Please select the imported mesh object before exporting.")
            return {'CANCELLED'}

        try:
            export_anim(obj, self.filepath, context)
            self.report({'INFO'}, f"Exported: {os.path.basename(self.filepath)}")
        except FileNotFoundError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        return {'FINISHED'}


# --------------------------
# Registration
# --------------------------
classes = (ANIMIO_OT_export,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)