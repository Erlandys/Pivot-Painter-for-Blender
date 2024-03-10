import inspect
import sys

import bpy.types

from . import Utils
from .Properties import *


# noinspection PyPep8Naming
class PivotPainter_OT_AddTexture(bpy.types.Operator):
    bl_label = "Add Texture"
    bl_idname = "pivot_painter.add_texture"
    bl_description = "Add Texture"

    def execute(self, context):
        properties = get_textures_list_settings(context)
        properties.add()
        return {'FINISHED'}


# noinspection PyPep8Naming
class PivotPainter_OT_RemoveTexture(bpy.types.Operator):
    bl_label = "Remove"
    bl_idname = "pivot_painter.remove_texture"
    bl_description = "Remove Texture"

    texture_index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        properties = get_textures_list_settings(context)
        if self.texture_index < 0 or self.texture_index >= len(properties):
            return {'CANCELLED'}

        properties.remove(self.texture_index)

        return {'FINISHED'}


# noinspection PyPep8Naming
class PivotPainter_OT_ExpandMenu(bpy.types.Operator):
    bl_label = "PivotPainter_OT_ExpandMenu"
    bl_idname = "pivot_painter.expand_menu"

    target_property_group_name: bpy.props.StringProperty(default='')
    target_property_name: bpy.props.StringProperty(default='')

    def execute(self, context):
        if len(self.target_property_group_name) < 0:
            return {'CANCELLED'}

        target_property_group = getattr(context.scene, self.target_property_group_name)
        if target_property_group is None or not isinstance(target_property_group, bpy.types.PropertyGroup):
            return {'CANCELLED'}

        target_property = getattr(target_property_group, self.target_property_name)
        if target_property is None or not isinstance(target_property, bool):
            return {'CANCELLED'}

        setattr(target_property_group, self.target_property_name, not target_property)
        return {'FINISHED'}


# noinspection PyPep8Naming
class PivotPainter_OT_CreateSelectOrder(bpy.types.Operator):
    bl_idname = "pivot_painter.create_select_order"
    bl_label = "Start selection order"
    bl_description = (""
                      "Press button, then start selecting objects with preferred order.\n"
                      "Press again to store order number in 'SelectionOrder' custom property.\n\n"
                      "You can select more than 1 object each time.\n"
                      "Press ESC to cancel. ")

    # Array with selected objects in order of selection
    order_array: list[bpy.types.Object] = []
    prev_len = 0

    @classmethod
    def poll(self, context):
        return bpy.context.mode == 'OBJECT'

    # Create the order_array
    def update(self, context):
        cur_len = len(context.selected_objects)

        # Selected more objects
        if cur_len > self.prev_len:
            for obj in context.selected_objects:
                # if obj are missing add to order_array
                if obj not in self.order_array:
                    self.order_array.append(obj)
        # Deselect objects
        elif cur_len < self.prev_len:
            for i, obj in enumerate(self.order_array):
                # if obj are deselected  remove from  order_array
                if obj not in context.selected_objects:
                    del self.order_array[i]

        # Store len to avoid calculation every update
        self.prev_len = len(self.order_array)

    # Used for panel draw. When button is pressed will hide operator from panel and in place will show selecting_objects bool
    def execute(self, context):
        properties = get_texture_settings(context)
        properties.selecting_objects = True

    def modal(self, context, event):
        properties = get_texture_settings(context)

        # Used to store order to objects when flip the boolean
        if not properties.selecting_objects:
            counter = properties.order_start
            for obj in self.order_array:
                # (order starts from 1 UE shader)
                obj["SelectionOrder"] = counter
                if not properties.dont_count:
                    counter = counter + 1
            return {'FINISHED'}
        # Cancel operation
        elif event.type == 'ESC':
            properties.selecting_objects = False

            # panel is lazy
            context.area.tag_redraw()
            return {'CANCELLED'}

        self.update(context)
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self.update(context)
        self.execute(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


# noinspection PyPep8Naming
class PivotPainter_OT_CreateTextures(bpy.types.Operator):
    bl_label = "Create Textures"
    bl_idname = "pivot_painter.create_textures"
    bl_description = "Save before use is advised.\n\nProgress report in system console. "
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Check that you are ready to rumble.
        return context.mode == 'OBJECT'  # and len(context.selected_objects) > 1 and context.active_object.type == 'MESH'

    def execute(self, context):
        import time
        from .core.CreateTextures import create_textures
        start_time = time.time()

        if not create_textures(self, context):
            return {'CANCELLED'}
        self.report({'INFO'}, "Textures created, total time: %.2fs" % (time.time() - start_time))
        return {'FINISHED'}


###########################################################
###########################################################
###########################################################


# noinspection PyPep8Naming
class PivotPainter_OT_PrepareMesh(bpy.types.Operator):
    bl_label = "Generate"
    bl_idname = "pivot_painter.generate_pivots_and_rotations"
    bl_description = "Will try to generate meshes pivots and rotations"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        import time
        from .core.PivotAndRotation import prepare_mesh

        if len(context.selected_objects) < 1:
            self.report({'ERROR'}, "No objects selected!")
            return {'CANCELLED'}

        # We want to select parents for edit mode
        selection = context.selected_objects

        start_time = time.time()

        from .Utils import reorder_selection_by_parents
        prepare_mesh(context, reorder_selection_by_parents(selection))

        self.report({'INFO'}, "Prepared %d meshes, total time: %.2fs" % (len(selection), time.time() - start_time))

        return {'FINISHED'}


###########################################################
###########################################################
###########################################################


# noinspection PyPep8Naming
class PivotPainter_OT_CopyUVs(bpy.types.Operator):
    bl_label = "Copy UVs"
    bl_idname = "pivot_painter.copy_uvs"
    bl_description = "Will try to copy UVs from split mesh into result mesh, by matching vertex coordinates"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        if len(context.selected_objects) < 1:
            self.report({'ERROR'}, "Atleast one object needs to be selected")
            return {'CANCELLED'}

        selection: list[bpy.types.Object] = []
        for obj in context.selected_objects:
            if obj is None or obj.type != 'MESH':
                continue
            selection.append(obj)

        import time
        from .core.MeshOperations import copy_uvs

        start_time = time.time()
        if not copy_uvs(self, context, selection):
            return {'CANCELLED'}

        self.report({'INFO'}, "UVs successfully copied, total time: %.2fs" % (time.time() - start_time))

        return {'FINISHED'}


###########################################################
###########################################################
###########################################################


# noinspection PyPep8Naming
class PivotPainter_OT_SplitMesh(bpy.types.Operator):
    bl_label = "Split Mesh"
    bl_idname = "pivot_painter.split_mesh"
    bl_description = "Will duplicate and split mesh by loose parts"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        if len(context.selected_objects) < 1:
            self.report({'ERROR'}, "Atleast one object needs to be selected")
            return {'CANCELLED'}

        selection: list[bpy.types.Object] = []
        for obj in context.selected_objects:
            if obj is None or obj.type != 'MESH':
                continue
            selection.append(obj)

        from .core.MeshOperations import split_mesh
        split_mesh(selection)

        if len(selection) == 1:
            properties = get_mesh_operations_settings(context)
            properties.copy_uvs_target = selection[0].name
        return {'FINISHED'}


###########################################################
###########################################################
###########################################################


# noinspection PyPep8Naming
class PivotPainter_OT_SelectBaseMeshes(bpy.types.Operator):
    bl_label = "Fill Base Meshes"
    bl_idname = "pivot_painter.fill_base_meshes_list"
    bl_description = "Will set base meshes from currently selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        if len(context.selected_objects) < 1:
            self.report({'ERROR'}, "Atleast one object needs to be selected")
            return {'CANCELLED'}

        selection: list[bpy.types.Object] = []
        for obj in context.selected_objects:
            if obj is None or obj.type != 'MESH':
                continue
            selection.append(obj)

        properties = get_mesh_operations_settings(context)
        properties.base_meshes.clear()

        for obj in selection:
            new_base_mesh = properties.base_meshes.add()
            new_base_mesh.name = obj.name

        self.report({'INFO'}, "Base meshes selection set")
        return {'FINISHED'}


###########################################################
###########################################################
###########################################################


# noinspection PyPep8Naming
class PivotPainter_OT_GenerateHierarchy(bpy.types.Operator):
    bl_label = "Generate Hierarchy"
    bl_idname = "pivot_painter.generate_hierarchy"
    bl_description = "Will try to setup hierarchy based on objects overlaps.\nThis is very experimental and slow.\nIf leaf overlaps with more than 1 object, it will fail to find its parent properly."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        if len(context.selected_objects) < 1:
            self.report({'ERROR'}, "Atleast one object needs to be selected")
            return {'CANCELLED'}

        selection: list[bpy.types.Object] = []
        for obj in context.selected_objects:
            if obj is None or obj.type != 'MESH':
                continue
            selection.append(obj)

        import time
        start_time = time.time()
        from .core.MeshOperations import generate_hierarchy
        if not generate_hierarchy(self, context, selection):
            # Reselect initially selected objects
            bpy.ops.object.select_all(action='DESELECT')

            for obj in selection:
                obj.select_set(True)

            return {'CANCELLED'}

        # Reselect initially selected objects
        bpy.ops.object.select_all(action='DESELECT')

        for obj in selection:
            obj.select_set(True)

        self.report({'INFO'}, "Hierarchy generated, took {:.2f} seconds".format(time.time() - start_time))
        return {'FINISHED'}


###########################################################
###########################################################
###########################################################


def register():
    Utils.register_classes_from_module(__name__, bpy.types.Operator)


def unregister():
    Utils.unregister_classes_from_module(__name__, bpy.types.Operator)
