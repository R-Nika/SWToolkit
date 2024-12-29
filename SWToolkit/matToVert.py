import bpy
import bmesh

from .interfaceManager import _label_multiline



# Operator for splitting edges and setting vertex colors
class OBJECT_OT_split_edges_and_set_colors(bpy.types.Operator):
    bl_idname = "object.split_edges_and_set_colors"
    bl_label = "Split Edges and Set Vertex Colors"

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

            color_attribute = obj.data.attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')
            materials = obj.data.materials

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

    def execute(self, context):
        obj = bpy.context.active_object
        if obj and obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')

            if "Col" not in obj.data.attributes:
                self.report({'ERROR'}, f"Object '{obj.name}' has no vertex color attribute named 'Col'")
                return {'CANCELLED'}

            color_attribute = obj.data.attributes["Col"]
            unique_colors = {}
            material_index = 0

            for poly in obj.data.polygons:
                color = [0.0, 0.0, 0.0, 0.0]
                for loop_index in poly.loop_indices:
                    loop = obj.data.loops[loop_index]
                    loop_color = color_attribute.data[loop.vertex_index].color
                    color = [color[i] + loop_color[i] for i in range(3)]

                color = [c / len(poly.loop_indices) for c in color]
                clamped_color = tuple(min(max(c, 0.0), 1.0) for c in color)

                if clamped_color not in unique_colors:
                    mat = bpy.data.materials.new(name=f"Material_{len(unique_colors)}")
                    mat.use_nodes = True
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        bsdf.inputs["Base Color"].default_value = (*clamped_color, 1.0)
                        bsdf.inputs["Roughness"].default_value = 1.0
                        bsdf.inputs["Specular"].default_value = 0.5
                    obj.data.materials.append(mat)
                    unique_colors[clamped_color] = material_index
                    material_index += 1

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

        # Collapsible area with tool info
        col = layout.column()
        col.prop(context.scene, "tool_info_expand", text="", icon="INFO")
        
        if context.scene.tool_info_expand:
            # Creates a box with some padding for multiline text
            box = col.box()  # We use 'col' here instead of 'layout'
            description_text = '''The Color Converting Tool allows you to convert materials to vertex colors and vice versa. When converting from material to vertex color, edges are automatically split to prevent vertex colors from becoming gradients.'''

            # Call the _label_multiline function to handle the dynamic wrapping of the text
            _label_multiline(context=context, text=description_text, parent=box)

        # Buttons inside nested boxes
        outer_box = layout.box()  # Outer box
        inner_box = outer_box.box()  # Inner box
        inner_box.operator("object.split_edges_and_set_colors", text="Materials to Vertex Color")
        inner_box.operator("object.vertex_color_to_materials", text="Vertex Colors to Materials")

# Register and unregister functions
def register():
    bpy.utils.register_class(OBJECT_OT_split_edges_and_set_colors)
    bpy.utils.register_class(OBJECT_OT_vertex_color_to_materials)
    bpy.utils.register_class(SWToolkitSplitPanel)

    # Add a custom property to toggle the collapsible area
    bpy.types.Scene.tool_info_expand = bpy.props.BoolProperty(
        name="Expand Tool Info",
        description="Toggle tool info visibility",
        default=False
    )

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_split_edges_and_set_colors)
    bpy.utils.unregister_class(OBJECT_OT_vertex_color_to_materials)
    bpy.utils.unregister_class(SWToolkitSplitPanel)

    # Remove the custom property
    del bpy.types.Scene.tool_info_expand

if __name__ == "__main__":
    register()
