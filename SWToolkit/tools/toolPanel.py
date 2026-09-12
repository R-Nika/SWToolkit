import bpy


# ============================================================
# Color Type Converter
# ============================================================

class VIEW3D_PT_sw_color_type_converter(bpy.types.Panel):
    bl_label = "Color Type Converter"
    bl_idname = "VIEW3D_PT_sw_color_type_converter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SW Toolkit"
    bl_order = 5

    def draw(self, context):
        layout = self.layout

        # Main outer box
        outer_box = layout.box()

        # Buttons
        inner_box = outer_box.box()

        inner_box.operator(
            "object.set_vertex_colors",
            text="Materials to Vertex Color"
        )

        inner_box.operator(
            "object.vertex_color_to_materials",
            text="Vertex Colors to Materials"
        )

        # Settings
        settings_box = outer_box.box()

        row = settings_box.row()

        icon = (
            "TRIA_DOWN"
            if context.scene.settings_color_type_converter
            else "TRIA_RIGHT"
        )

        row.prop(
            context.scene,
            "settings_color_type_converter",
            text="",
            icon=icon,
            emboss=False
        )

        row.label(text="Settings")

        if context.scene.settings_color_type_converter:
            nested_box = settings_box.box()

            nested_box.prop(
                context.scene,
                "remove_custom_normals",
                text="Remove Custom Normals"
            )

            nested_box.prop(
                context.scene,
                "auto_name_glass",
                text="Auto Name Glass"
            )


# ============================================================
# Separate by Vertex Color
# ============================================================

class VIEW3D_PT_separate_by_vertex_color_panel(bpy.types.Panel):
    bl_label = "Separate by Vertex Color"
    bl_idname = "VIEW3D_PT_separate_by_vertex_color"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SW Toolkit'
    bl_order = 6

    def draw(self, context):
        layout = self.layout

        # Main outer box
        outer_box = layout.box()

        # Operator
        inner_box = outer_box.box()

        inner_box.operator(
            "object.separate_by_vertex_color",
            text="Separate by Vertex Color",
            icon="MESH_CUBE"
        )

        # Settings
        settings_box = outer_box.box()

        row = settings_box.row()

        icon = (
            "TRIA_DOWN"
            if context.scene.show_separate_settings
            else "TRIA_RIGHT"
        )

        row.prop(
            context.scene,
            "show_separate_settings",
            text="",
            icon=icon,
            emboss=False
        )

        row.label(text="Settings")

        if context.scene.show_separate_settings:

            # -------------------------
            # Color Settings
            # -------------------------

            domain_box = settings_box.box()

            header_row = domain_box.row()
            header_row.alignment = 'CENTER'
            header_row.label(text="Color Settings")

            domain_box.prop(
                context.scene,
                "vertex_color_domain",
                text="Domain"
            )

            domain_box.prop(
                context.scene,
                "transfer_materials",
                text="Transfer Materials"
            )

            if context.scene.transfer_materials:
                domain_box.prop(
                    context.scene,
                    "link_materials",
                    text="Link Materials"
                )

            # -------------------------
            # Geometry Processing
            # -------------------------

            geometry_box = settings_box.box()

            header_row = geometry_box.row()
            header_row.alignment = 'CENTER'
            header_row.label(text="Geometry Processing")

            geometry_box.prop(
                context.scene,
                "join_after_separate",
                text="Join Resulting Objects"
            )

            geometry_box.prop(
                context.scene,
                "triangulate_after_separate",
                text="Triangulate"
            )

            geometry_box.prop(
                context.scene,
                "edgesplit_after_separate",
                text="Edge Split"
            )

            geometry_box.prop(
                context.scene,
                "merge_by_distance_after_separate",
                text="Merge by Distance"
            )

            geometry_box.prop(
                context.scene,
                "limited_dissolve_after_separate",
                text="Limited Dissolve"
            )


# ============================================================
# Registration
# ============================================================

classes = (
    VIEW3D_PT_sw_color_type_converter,
    VIEW3D_PT_separate_by_vertex_color_panel,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    # --------------------------------------------------------
    # Color Type Converter settings
    # --------------------------------------------------------

    bpy.types.Scene.settings_color_type_converter = bpy.props.BoolProperty(
        name="Show Tool Settings",
        description="Expand or collapse settings for the color type converter",
        default=False
    )

    bpy.types.Scene.remove_custom_normals = bpy.props.BoolProperty(
        name="Remove Custom Normals",
        description="Remove custom normals for accurate material preview during conversion",
        default=True
    )

    bpy.types.Scene.auto_name_glass = bpy.props.BoolProperty(
        name="Auto Name Glass",
        description="Name materials with hex color #A0A0C7 as 'MATERIALglass'",
        default=False
    )

    # --------------------------------------------------------
    # Separate by Vertex Color settings
    # --------------------------------------------------------

    bpy.types.Scene.vertex_color_domain = bpy.props.EnumProperty(
        name="Domain",
        description="Vertex color domain to use for separation",
        items=[
            (
                'CORNER',
                "Corner",
                "Use corner domain (per-face vertex colors)"
            ),
            (
                'POINT',
                "Point",
                "Use point domain (per-vertex colors)"
            )
        ],
        default='CORNER'
    )

    bpy.types.Scene.transfer_materials = bpy.props.BoolProperty(
        name="Transfer Materials",
        description="Copy materials from original to separated objects",
        default=False
    )

    bpy.types.Scene.link_materials = bpy.props.BoolProperty(
        name="Link Materials",
        description="Share materials between original and separated objects",
        default=True
    )

    bpy.types.Scene.join_after_separate = bpy.props.BoolProperty(
        name="Join Resulting Objects",
        description="Join all separated objects into one after splitting",
        default=False
    )

    bpy.types.Scene.triangulate_after_separate = bpy.props.BoolProperty(
        name="Triangulate",
        description="Triangulate resulting meshes after separation",
        default=False
    )

    bpy.types.Scene.edgesplit_after_separate = bpy.props.BoolProperty(
        name="Edge Split",
        description="Split faces by edges shared by multiple faces",
        default=False
    )

    bpy.types.Scene.merge_by_distance_after_separate = bpy.props.BoolProperty(
        name="Merge by Distance",
        description="Merge overlapping vertices after separation",
        default=False
    )

    bpy.types.Scene.limited_dissolve_after_separate = bpy.props.BoolProperty(
        name="Limited Dissolve",
        description="Perform limited dissolve on resulting meshes",
        default=False
    )

    bpy.types.Scene.show_separate_settings = bpy.props.BoolProperty(
        name="Show Tool Settings",
        description="Expand or collapse settings for separation",
        default=False
    )


def unregister():

    # --------------------------------------------------------
    # Remove Scene properties
    # --------------------------------------------------------

    del bpy.types.Scene.settings_color_type_converter
    del bpy.types.Scene.remove_custom_normals
    del bpy.types.Scene.auto_name_glass

    del bpy.types.Scene.vertex_color_domain
    del bpy.types.Scene.transfer_materials
    del bpy.types.Scene.link_materials
    del bpy.types.Scene.join_after_separate
    del bpy.types.Scene.triangulate_after_separate
    del bpy.types.Scene.edgesplit_after_separate
    del bpy.types.Scene.merge_by_distance_after_separate
    del bpy.types.Scene.limited_dissolve_after_separate
    del bpy.types.Scene.show_separate_settings

    # Unregister panels
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()