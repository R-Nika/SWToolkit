import bpy
import bmesh

from .interfaceManager import _label_multiline

# Operator for splitting edges and setting vertex colors
class OBJECT_OT_split_edges_and_set_colors(bpy.types.Operator):
    bl_idname = "object.split_edges_and_set_colors"
    bl_label = "Split Edges and Set Vertex Colors"
    bl_description = "Convert materials to vertex colors and split edges to prevent color gradient"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.context.active_object
        if obj and obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')

            bm = bmesh.new()
            bm.from_mesh(obj.data)

            edges_to_split = [edge for edge in bm.edges if len(edge.link_faces) > 1]
            if edges_to_split:
                bmesh.ops.split_edges(bm, edges=edges_to_split)
                bm.to_mesh(obj.data)
                obj.data.update()
                self.report({'INFO'}, f"Split all edges for {obj.name}")

            bm.free()

            # Remove old vertex color layer if it exists
            if "Col" in obj.data.attributes:
                obj.data.attributes.remove(obj.data.attributes["Col"])

            # Force Blender to rebuild mesh after edge split
            obj.data.update()
            bpy.context.view_layer.update()

            # Create fresh vertex color layer
            color_attribute = obj.data.attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')
            materials = obj.data.materials

            # Make it active and display in viewport
            obj.data.color_attributes.active = color_attribute
            obj.data.color_attributes.active_color = color_attribute
            
            if materials:
                for poly in obj.data.polygons:
                    material_index = poly.material_index
                    if material_index < len(materials):
                        material = materials[material_index]
                        if material.use_nodes:
                            bsdf_node = material.node_tree.nodes.get("Principled BSDF")
                            diffuse_color = bsdf_node.inputs["Base Color"].default_value[:3] if bsdf_node else (1.0, 1.0, 1.0)
                        else:
                            diffuse_color = material.diffuse_color[:3] if hasattr(material, 'diffuse_color') else (1.0, 1.0, 1.0)

                        for loop_index in poly.loop_indices:
                            loop = obj.data.loops[loop_index]
                            color_attribute.data[loop.vertex_index].color = (*diffuse_color, 1.0)
            else:
                self.report({'WARNING'}, "No materials found on the object.")

            for obj in bpy.context.selected_objects:
                if obj.type == "MESH" and obj.data.color_attributes:
                    attrs = obj.data.color_attributes
                    for r in range(len(attrs) - 1, -1, -1):
                        if attrs[r].name != "Col":
                            attrs.remove(attrs[r])

            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No active mesh object found.")
            return {'CANCELLED'}

# Operator for converting vertex colors back to materials
class OBJECT_OT_vertex_color_to_materials(bpy.types.Operator):
    bl_idname = "object.vertex_color_to_materials"
    bl_label = "Vertex Colors to Materials"
    bl_description = "Convert vertex colors back to materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.context.active_object
        if obj and obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')

            if "Col" not in obj.data.attributes:
                self.report({'ERROR'}, f"Object '{obj.name}' has no vertex color attribute named 'Col'")
                return {'CANCELLED'}

            # Remove custom normals if enabled
            if context.scene.remove_custom_normals and "custom_normal" in obj.data.attributes:
                obj.data.attributes.remove(obj.data.attributes["custom_normal"])
                self.report({'INFO'}, "Removed custom normals for accurate material preview")

            color_attribute = obj.data.attributes["Col"]
            unique_colors = {}
            material_index = 0

            for poly in obj.data.polygons:
                # Average vertex colors across the polygon
                color = [0.0, 0.0, 0.0]
                for loop_index in poly.loop_indices:
                    loop = obj.data.loops[loop_index]
                    loop_color = color_attribute.data[loop.vertex_index].color
                    color = [color[i] + loop_color[i] for i in range(3)]

                color = [c / len(poly.loop_indices) for c in color]
                clamped_color = tuple(min(max(c, 0.0), 1.0) for c in color)

                if clamped_color not in unique_colors:
                    # Convert from linear to sRGB color space with precision handling
                    def linear_to_srgb(c):
                        # Handle exact 0.0 and 1.0 to avoid floating point errors
                        if c <= 0.0:
                            return 0.0
                        elif c >= 1.0:
                            return 1.0
                        elif c < 0.0031308:
                            return c * 12.92
                        else:
                            return 1.055 * (c ** (1.0/2.4)) - 0.055
                    
                    srgb_color = tuple(linear_to_srgb(c) for c in clamped_color)
                    
                    # Convert to 0-255 for RGB naming, with rounding to handle floating point precision
                    r, g, b = [round(c * 255) for c in srgb_color]
                    hex_color = f"#{r:02X}{g:02X}{b:02X}"
                    
                    # Auto name glass functionality
                    if context.scene.auto_name_glass and hex_color.upper() == "#A0A0C7":
                        mat_name = "MATERIALglass"
                    else:
                        mat_name = f"{hex_color} ({r},{g},{b})"

                    print(f"Creating material: {mat_name} (from linear {clamped_color} to sRGB {srgb_color})")

                    # Create new material - use SRGB color for the material
                    mat = bpy.data.materials.new(name=mat_name)
                    mat.use_nodes = True
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        bsdf.inputs["Base Color"].default_value = (*srgb_color, 1.0)
                        if "Roughness" in bsdf.inputs:
                            bsdf.inputs["Roughness"].default_value = 1.0
                        if "Specular" in bsdf.inputs:
                            bsdf.inputs["Specular"].default_value = 0.5
                        if "Metallic" in bsdf.inputs:
                            bsdf.inputs["Metallic"].default_value = 0.0

                    # Append material to object
                    obj.data.materials.append(mat)
                    unique_colors[clamped_color] = material_index
                    material_index += 1

                # Assign polygon to the correct material
                poly.material_index = unique_colors[clamped_color]

            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No active mesh object found.")
            return {'CANCELLED'}

# Panel for SW Toolkit
class SWToolkitSplitPanel(bpy.types.Panel):
    bl_label = "Color Type Converter"
    bl_idname = "VIEW3D_PT_add_vertex_color_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SW Toolkit"

    def draw(self, context):
        layout = self.layout

        # Main outer box
        outer_box = layout.box()
        
        # Buttons inside inner box
        inner_box = outer_box.box()
        inner_box.operator("object.split_edges_and_set_colors", text="Materials to Vertex Color")
        inner_box.operator("object.vertex_color_to_materials", text="Vertex Colors to Materials")
        
        # Settings collapsible area INSIDE the outer box
        settings_box = outer_box.box()
        row = settings_box.row()
        icon = "TRIA_DOWN" if context.scene.settings_color_type_converter else "TRIA_RIGHT"
        row.prop(context.scene, "settings_color_type_converter", text="", icon=icon, emboss=False)
        row.label(text="Settings")

        if context.scene.settings_color_type_converter:
            nested_box = settings_box.box()
            nested_box.prop(context.scene, "remove_custom_normals", text="Remove Custom Normals")
            nested_box.prop(context.scene, "auto_name_glass", text="Auto Name Glass")

# Register and unregister functions
def register():
    bpy.utils.register_class(OBJECT_OT_split_edges_and_set_colors)
    bpy.utils.register_class(OBJECT_OT_vertex_color_to_materials)
    bpy.utils.register_class(SWToolkitSplitPanel)

    # Add custom properties
    bpy.types.Scene.settings_color_type_converter = bpy.props.BoolProperty(
        name="Show Tool Settings",
        description="Expand or collapse settings for separation",
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

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_split_edges_and_set_colors)
    bpy.utils.unregister_class(OBJECT_OT_vertex_color_to_materials)
    bpy.utils.unregister_class(SWToolkitSplitPanel)
    
    # Remove custom properties
    del bpy.types.Scene.settings_color_type_converter
    del bpy.types.Scene.remove_custom_normals
    del bpy.types.Scene.auto_name_glass

if __name__ == "__main__":
    register()