import bpy
import os

from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper


# --------------------------
# Operator: manually pick a source .anim file
# --------------------------
class ANIMIO_OT_set_source(bpy.types.Operator, ImportHelper):
    bl_idname = "animio.set_source"
    bl_label = "Select Source .anim"
    bl_description = (
        "Manually link a source .anim file to this object "
        "(used to preserve skeleton & animation data on export)"
    )
    filename_ext = ".anim"

    filter_glob: StringProperty(
        default="*.anim",
        options={'HIDDEN'}
    )

    def execute(self, context):
        obj = context.active_object

        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object.")
            return {'CANCELLED'}

        obj["anim_source_path"] = self.filepath

        self.report(
            {'INFO'},
            f"Source linked: {os.path.basename(self.filepath)}"
        )

        return {'FINISHED'}


# --------------------------
# Panel
# --------------------------
class VIEW3D_PT_anim_io(bpy.types.Panel):
    bl_label = "Character Tools"
    bl_idname = "VIEW3D_PT_anim_io"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SW Toolkit"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        # --------------------------
        # .anim
        # --------------------------
        box = layout.box()
        inner_box = box.box()

        row = inner_box.row()
        row.label(text=".anim files", icon='IMPORT')

        # Import
        inner_box.operator(
            "animio.import_anim",
            text="Import .anim",
            icon='FILE_FOLDER'
        )

        # Export / source
        if obj and obj.type == 'MESH':
            source = obj.get("anim_source_path", None)

            if source:
                row = inner_box.row()
                row.label(
                    text=f"Source: {os.path.basename(source)}",
                    icon='FILE_TICK'
                )

                row = inner_box.row()

                row.operator(
                    "animio.export_anim",
                    text="Export .anim",
                    icon='EXPORT'
                )

                row.operator(
                    "animio.set_source",
                    text="",
                    icon='FILEBROWSER'
                )

            else:
                inner_box.label(
                    text="No source .anim linked.",
                    icon='ERROR'
                )

                inner_box.operator(
                    "animio.set_source",
                    text="Select Source .anim",
                    icon='FILEBROWSER'
                )

        else:
            inner_box.label(
                text="Select a mesh object.",
                icon='INFO'
            )


# --------------------------
# Registration
# --------------------------
classes = (
    ANIMIO_OT_set_source,
    VIEW3D_PT_anim_io,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)