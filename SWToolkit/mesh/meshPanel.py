import bpy


class VIEW3D_PT_sw_mesh_tools(bpy.types.Panel):
    bl_label = "Import / Export"
    bl_idname = "VIEW3D_PT_sw_mesh_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SW Toolkit"
    bl_order = 1

    def draw(self, context):
        layout = self.layout

        # Main outer box
        box = layout.box()

        # --------------------------
        # .mesh
        # --------------------------
        mesh_box = box.box()

        row = mesh_box.row()
        row.label(text=".mesh files", icon='IMPORT')

        mesh_box.operator(
            "import_scene.stormworks_mesh",
            text="Import .mesh",
            icon='FILE_FOLDER',
        )

        mesh_box.operator(
            "export_scene.stormworks_mesh",
            text="Export .mesh",
            icon='EXPORT',
        )

        # --------------------------
        # .phys
        # --------------------------
        phys_box = box.box()

        row = phys_box.row()
        row.label(text=".phys files", icon='IMPORT')

        phys_box.operator(
            "import_scene.stormworks_phys",
            text="Import .phys",
            icon='FILE_FOLDER',
        )

        phys_box.operator(
            "export_scene.stormworks_phys",
            text="Export .phys",
            icon='EXPORT',
        )


def register():
    bpy.utils.register_class(VIEW3D_PT_sw_mesh_tools)


def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_sw_mesh_tools)