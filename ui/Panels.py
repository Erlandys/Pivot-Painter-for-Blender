import typing

import bpy.utils

from .. import Utils
from ..Properties import *
from ..data.TextureOptions import *


def expand_menu(layout, properties_group, target_property, text) -> bool:
    value = getattr(properties_group, target_property)
    row = layout.row()
    row.alignment = 'LEFT'
    op = row.operator("pivot_painter.expand_menu", icon='TRIA_DOWN' if value else 'TRIA_RIGHT', text=text, emboss=False)
    op.target_property_group_name = properties_group.get_group_name()
    op.target_property_name = target_property
    return value


# noinspection PyPep8Naming
class PIVOTPAINTER_PT_Texture(bpy.types.Panel):
    bl_idname = "PIVOTPAINTER_PT_Texture"
    bl_label = "Pivot Painter"
    bl_category = "Pivot Painter"
    bl_context = "objectmode"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_order = 0

    def draw(self, context):
        properties = get_texture_settings(context)
        textures_list_properties = get_textures_list_settings(context)

        if expand_menu(self.layout, properties, 'display_textures', 'Textures'):
            properties_box = self.layout.box()
            col = properties_box.column()
            for idx in range(len(textures_list_properties)):
                row = col.row()
                row.label(text="Texture " + str(idx + 1) + ":")
                op = row.operator("pivot_painter.remove_texture")
                op.texture_index = idx

                rgb_option: PivotPainterTextureTypeData = textures_list_properties[idx].get_rgb_option()

                col.prop(textures_list_properties[idx], "rgb")
                if not rgb_option.rgba():
                    col.prop(textures_list_properties[idx], "alpha")
                col.prop(textures_list_properties[idx], "generate_hdr")

                rgb_packer = rgb_option.packer(context, [], textures_list_properties[idx].generate_hdr)
                alpha_option: PivotPainterTextureTypeData = textures_list_properties[idx].get_alpha_option()
                alpha_packer = alpha_option.packer(context, [], textures_list_properties[idx].generate_hdr)

                if textures_list_properties[idx].generate_hdr:
                    col.label(text="OpenEXR, RGBA, Color Depth: Float(Half)", icon="INFO")
                    if not rgb_packer.support_hdr:
                        col.label(text="RGB - " + rgb_option.display_name() + " does not support HDR", icon="ERROR")
                    if not rgb_option.rgba() and not alpha_packer.support_hdr:
                        col.label(text="Alpha - " + alpha_option.display_name() + " does not support HDR", icon="ERROR")
                else:
                    col.label(text="PNG, RGBA, Color Depth: 8", icon="INFO")
                    if not rgb_packer.support_ldr:
                        col.label(text="RGB - " + rgb_option.display_name() + " does not support LDR", icon="ERROR")
                    if not rgb_option.rgba() and not alpha_packer.support_ldr:
                        col.label(text="Alpha - " + alpha_option.display_name() + " does not support LDR", icon="ERROR")
                col.label()
                col.separator()
            col.operator("pivot_painter.add_texture")

        if expand_menu(self.layout, properties, 'extra_options', 'Extra Options'):
            box = self.layout.box()

            row1 = box.column()
            row1.scale_y = 1.5

            # create select order (flip option to show operation running)
            if not properties.selecting_objects:
                row1.operator("pivot_painter.create_select_order")
            else:
                row1.prop(properties, "selecting_objects", toggle=True)

            row6 = box.row()
            row6.prop(properties, "order_start")
            row6.prop(properties, "dont_count")

        self.layout.separator()

        # File options
        col = self.layout.column()
        rows = col.row()
        rows.prop(properties, "create_new")
        rows.prop(properties, "save_textures")

        sub2 = self.layout.column()
        sub2.enabled = properties.save_textures
        sub2.prop(properties, "folder_path")

        row = self.layout.row()
        row.scale_y = 2
        row.operator("pivot_painter.create_textures")


# noinspection PyPep8Naming
class PIVOTPAINTER_PT_PivotAndRotations(bpy.types.Panel):
    bl_idname = "PIVOTPAINTER_PT_PivotAndRotations"
    bl_label = "Generate Pivots and Rotations"
    bl_category = "Pivot Painter"
    bl_context = "objectmode"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_order = 2

    def draw(self, context):
        pivot_properties = get_calculate_pivot_settings(context)
        rotation_properties = get_calculate_rotation_settings(context)

        if expand_menu(self.layout, pivot_properties, 'show', 'Pivots Generation'):
            box = self.layout.box()

            row = box.row()
            row.prop(pivot_properties, "enabled")

            row = box.row()
            row.enabled = pivot_properties.enabled
            row.prop(pivot_properties, "item_type")

            row = box.row()
            row.enabled = pivot_properties.enabled
            row.prop(pivot_properties, "calculation_type")

            per = box.column()
            per.enabled = pivot_properties.calculation_type == 'mean' and pivot_properties.enabled
            per.prop(pivot_properties, "max_distance", slider=True)

            box.separator()

            row = box.row()
            row.enabled = pivot_properties.enabled
            row.prop(pivot_properties, "no_parent_pivot_type")

            row = box.row()
            row.enabled = pivot_properties.enabled and pivot_properties.no_parent_pivot_type == 'axis_middle'
            row.prop(pivot_properties, "no_parent_axis")

            row = box.row()
            row.enabled = pivot_properties.enabled and pivot_properties.no_parent_pivot_type == 'axis_middle'
            row.prop(pivot_properties, "no_parent_max_axis_difference")

        self.layout.separator()

        if expand_menu(self.layout, rotation_properties, 'show', 'Rotations Generation'):
            box = self.layout.box()

            row = box.row()
            row.prop(rotation_properties, "enabled")

            row = box.row()
            row.enabled = rotation_properties.enabled
            row.prop(rotation_properties, "item_type")

            row = box.row()
            row.enabled = rotation_properties.enabled
            row.prop(rotation_properties, "calculation_type")

            per = box.column()
            per.enabled = rotation_properties.calculation_type == 'mean' and rotation_properties.enabled
            per.prop(rotation_properties, "max_distance", slider=True)

        row = self.layout.row()
        row.enabled = pivot_properties.enabled or rotation_properties.enabled
        row.scale_y = 2
        row.operator("pivot_painter.generate_pivots_and_rotations")


# noinspection PyPep8Naming
class PIVOTPAINTER_UL_BaseMeshesList(bpy.types.UIList):
    def draw_item(self,
                  context: typing.Optional['bpy.types.Context'],
                  layout: 'bpy.types.UILayout',
                  data: typing.Optional[typing.Any],
                  item: typing.Optional[typing.Any],
                  icon: typing.Optional[int],
                  active_data: typing.Any,
                  active_property: str,
                  index: typing.Optional[typing.Any] = 0,
                  flt_flag: typing.Optional[typing.Any] = 0):
        layout.prop(item, "name", text="", emboss=False, icon_value=layout.icon(item))


# noinspection PyPep8Naming
class PIVOTPAINTER_PT_MeshOperations(bpy.types.Panel):
    bl_idname = "PIVOTPAINTER_PT_MeshOperations"
    bl_label = "Mesh Operations"
    bl_category = "Pivot Painter"
    bl_context = "objectmode"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_order = 2

    def draw(self, context):
        properties = get_mesh_operations_settings(context)

        if expand_menu(self.layout, properties, 'show_split_mesh', 'Split Mesh'):
            row = self.layout.row()
            row.scale_y = 2
            row.operator("pivot_painter.split_mesh")

        if expand_menu(self.layout, properties, 'show_copy_uvs', 'Copy UVs'):
            box = self.layout.box()

            box.prop_search(properties, "copy_uvs_target", context.scene, "objects")
            box.prop(properties, "copy_uvs_uv_precision_lookup")

            row = box.row(align=True)
            row.alignment = 'EXPAND'
            row.label(text="Vertex positions will be " + format(pow(10, -properties.copy_uvs_uv_precision_lookup), '.' + str(properties.copy_uvs_uv_precision_lookup) + 'f') + " precision")
            row = box.row(align=True)
            row.alignment = 'EXPAND'
            row.label(text="If not found, will compare locations with " + format(pow(10, -(properties.copy_uvs_uv_precision_lookup - 1)), '.' + str(properties.copy_uvs_uv_precision_lookup - 1) + 'f') + " difference.")
            row = box.row(align=True)
            row.alignment = 'EXPAND'
            row.label(text="Higher precision produces more mismatches.")

            row = box.row()
            row.enabled = len(properties.copy_uvs_target) > 0
            row.scale_y = 2
            row.operator("pivot_painter.copy_uvs", )

        if expand_menu(self.layout, properties, 'show_generate_hierarchy', 'Generate Hierarchy'):
            box = self.layout.box()

            box.template_list("PIVOTPAINTER_UL_BaseMeshesList", "", properties, 'base_meshes', properties, 'base_mesh_index')

            box.operator("pivot_painter.fill_base_meshes_list")

            box.separator()

            row = box.row()
            row.scale_y = 2
            row.operator("pivot_painter.generate_hierarchy")


panels = [
    PIVOTPAINTER_PT_Texture,
    PIVOTPAINTER_PT_PivotAndRotations,
    PIVOTPAINTER_UL_BaseMeshesList,
    PIVOTPAINTER_PT_MeshOperations
]


def register():
    for panel in panels:
        bpy.utils.register_class(panel)


def unregister():
    for panel in panels:
        bpy.utils.unregister_class(panel)
