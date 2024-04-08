import os
import time
from math import ceil, floor, sqrt

import numpy

from ..Utils import *
from ..Properties import *
from ..data.TexturePackingFunctions import TexturePacking


def find_texture_dimensions(selection: list[bpy.types.Object]) -> list[int]:
    num_objects = len(selection)

    decrement_total = 256

    half_even_number = ((num_objects / 2) % 2)
    half_number = ceil(num_objects / 2)

    if half_number < decrement_total:
        new_denominator_total = half_number
    else:
        new_denominator_total = decrement_total

    if half_even_number == 0:
        decrement_amount = 2
    else:
        decrement_amount = 1

    complete = False
    while not complete:
        mod_result = num_objects % new_denominator_total
        if mod_result == 0 or new_denominator_total < 1:
            complete = True
        if not complete:
            new_denominator_total -= decrement_amount
        if new_denominator_total < 1:
            new_denominator_total = 1

    if new_denominator_total == 1 or ((num_objects / new_denominator_total) > decrement_total):
        y = floor(sqrt(num_objects))
        x = ceil(num_objects / floor(y))
        size = [x, y]
    else:
        size = [new_denominator_total, (num_objects // new_denominator_total)]

    return size


def create_uv_map(context: bpy.types.Context, selection: list[bpy.types.Object], size: list[int]):
    properties = get_texture_settings(context)

    num = 0

    bpy.ops.object.select_all(action='DESELECT')

    half_pixel_x = 1.0 / size[0]
    half_pixel_y = 1.0 / size[1]

    progress = ProgressBar('Creating UV Maps', len(selection))

    step = ceil(len(selection) * 0.01)
    for idx, obj in enumerate(selection):
        if obj is None or obj.data is None or obj.type != 'MESH':
            if idx % step == step - 1:
                progress += step
            continue

        obj.select_set(True)

        obj_mesh: bpy.types.Mesh = obj.data

        # print("Create UV Map for object %i of %i" % (idx, len(selection)))

        uv_layer: bpy.types.MeshUVLoopLayer | None = None
        for uv in obj_mesh.uv_layers:
            if uv.name == properties.uv_map_name:
                uv_layer = uv

        if uv_layer is None:
            uv_layer = obj_mesh.uv_layers.new(name=properties.uv_map_name)

        obj_mesh.uv_layers.active = uv_layer

        if not uv_layer.active:
            obj.select_set(False)
            return

        uv_layer.active_render = True

        x, y = get_xy_from_index(size, idx)

        x += 0.5
        y += 0.5

        x *= half_pixel_x
        y *= half_pixel_y

        for poly in obj_mesh.polygons:
            for loopId in poly.loop_indices:
                uv_layer.data[loopId].uv = (x, y)

        num += 1
        obj.select_set(False)
        if idx % step == step - 1:
            progress += step

    bpy.ops.object.select_all(action='DESELECT')
    for idx, obj in enumerate(selection):
        obj.select_set(True)


def create_texture(operator: bpy.types.Operator, context: bpy.types.Context, selection: list[bpy.types.Object], progress_bar: ProgressBar, size: list[int], texture_idx: int):
    properties = get_texture_settings(context)
    textures_list = get_textures_list_settings(context)

    is_hdr = textures_list[texture_idx].generate_hdr

    # Select variables between the textures in the UIPanel
    rgb_option = textures_list[texture_idx].get_rgb_option()
    alpha_option = textures_list[texture_idx].get_alpha_option()

    from ..data.TexturePackingFunctions import TexturePacking
    rgb_packer: TexturePacking = rgb_option.packer(context, selection, is_hdr)
    alpha_packer: TexturePacking = alpha_option.packer(context, selection, is_hdr)

    if not rgb_packer.support_type(is_hdr) or (not rgb_option.rgba() and not alpha_packer.support_type(is_hdr)):
        operator.report({'ERROR'}, 'Texture ' + str(texture_idx) + ' has HDR mismatches.')
        return

    texture_name = selection[0].name + '_' + rgb_option.suffix()
    if not rgb_option.rgba():
        texture_name += '_' + alpha_option.suffix()
    if is_hdr:
        texture_name += '_HDR'

    # Check if there is already the texture, else create new.
    if not properties.create_new:
        for img in bpy.data.images:
            if img.name == texture_name:
                bpy.data.images.remove(img)

    image = bpy.data.images.new(name=texture_name, width=size[0], height=size[1], float_buffer=is_hdr, is_data=True)
    image.pixels = set_pixels(selection, rgb_packer, alpha_packer, rgb_option.rgba(), progress_bar, size)

    if not properties.save_textures:
        return

    image_settings = bpy.context.scene.render.image_settings
    image_settings.color_mode = 'RGBA'
    if is_hdr:
        image_path = bpy.path.abspath(properties.folder_path) + image.name + '.exr'
        image_settings.file_format = 'OPEN_EXR'
        image_settings.color_depth = '16'
    else:
        image_path = bpy.path.abspath(properties.folder_path) + image.name + '.png'
        image_settings.file_format = 'PNG'
        image_settings.color_depth = '8'

    image.save_render(image_path)


def set_pixels(selection: list[bpy.types.Object], rgb_packer: TexturePacking, alpha_packer: TexturePacking, rgba: bool, progress_bar: ProgressBar, size: list[int]) -> list[float]:
    pixels: list[float] = numpy.ones(size[0] * size[1] * 4, dtype=float).tolist()

    if rgba:
        has_post_process = rgb_packer.has_post_process()
    else:
        has_post_process = rgb_packer.has_post_process() or alpha_packer.has_post_process()

    local_progress_bar = progress_bar.new_sub_progress('Preparing pixel data {1} of {0} pixels', len(selection) + ((size[0] * size[1] / 4) if has_post_process else 0))

    step = ceil(len(selection) * 0.01)
    for idx in range(len(selection)):
        obj = selection[idx]

        rgb_values = rgb_packer.process_object(obj)
        if not rgba:
            alpha_value = alpha_packer.process_object(obj)
        else:
            alpha_value = rgb_values[3]

        x, y = get_xy_from_index(size, idx)
        pixel_index = x + (y * size[0])

        pixels[pixel_index * 4 + 0] = rgb_values[0]
        pixels[pixel_index * 4 + 1] = rgb_values[1]
        pixels[pixel_index * 4 + 2] = rgb_values[2]
        pixels[pixel_index * 4 + 3] = alpha_value
        if idx % step == step - 1:
            local_progress_bar += step

    step = ceil((size[0] * size[1] / 4) * 0.01)
    step_idx = 0

    if has_post_process:
        for idx in range(0, size[0] * size[1], 4):
            if rgba:
                if rgb_packer.has_post_process():
                    pixels[idx:idx + 3] = rgb_packer.post_process(pixels[idx:idx + 3])
            else:
                if rgb_packer.has_post_process():
                    pixels[idx:idx + 2] = rgb_packer.post_process(pixels[idx:idx + 2])
                if alpha_packer.has_post_process():
                    pixels[idx + 3] = alpha_packer.post_process(pixels[idx + 3])
            step_idx += 1
            if step_idx % step == step - 1:
                local_progress_bar += step

    local_progress_bar.finish()

    return pixels


def create_textures(operator: bpy.types.Operator, context: bpy.types.Context):
    properties = get_texture_settings(context)
    textures_list = get_textures_list_settings(context)
    units = context.scene.unit_settings

    selection: list[bpy.types.Object] = []
    for obj in context.selected_objects:
        if obj is None or obj.type != 'MESH':
            continue
        selection.append(obj)

    # Check that saving texture to file is possible
    if properties.save_textures:
        if not os.path.exists(bpy.path.abspath(properties.folder_path)):
            operator.report({'ERROR'}, 'Incorrect Save location ' + str(properties.folder_path))
            return False

    not_supported_texture = -1
    test_selection_order = False

    for idx in range(len(textures_list)):
        if textures_list[idx].rgb == 'None' and textures_list[idx].alpha == 'None':
            continue

        # Find if rgb and alpha use HDR and what the alpha channel is set to store
        rgb_option = textures_list[idx].get_rgb_option()
        rgb_packer = rgb_option.packer(context, selection, textures_list[idx].generate_hdr)
        alpha_option = textures_list[idx].get_alpha_option()
        alpha_packer = alpha_option.packer(context, selection, textures_list[idx].generate_hdr)

        if textures_list[idx].generate_hdr:
            if not rgb_packer.support_hdr:
                not_supported_texture = idx
                break
            if not rgb_option.rgba() and not alpha_packer.support_hdr:
                not_supported_texture = idx
                break
        else:
            if not rgb_packer.support_ldr:
                not_supported_texture = idx
                break
            if not rgb_option.rgba() and not alpha_packer.support_ldr:
                not_supported_texture = idx
                break

        if rgb_option.test_selection_order() or (not rgb_option.rgba() and alpha_option.test_selection_order()):
            test_selection_order = True

    objects_without_order = []
    if test_selection_order:
        for obj in selection:
            try:
                obj["SelectionOrder"]
            except Exception:
                objects_without_order.append(obj.name)

        if len(objects_without_order) > 0:
            if len(objects_without_order) < 4:
                operator.report({'ERROR'}, "Object " + str(objects_without_order) + " missing 'SelectionOrder' property")
            else:
                operator.report({'INFO'}, " Objects missing 'SelectionOrder' property : " + str(objects_without_order))
                operator.report({'ERROR'}, str(len(objects_without_order)) + " Objects missing 'SelectionOrder' property\nList of the objects in the console. ")
            return False

    # Numerous checks that everything is fine
    if units.system != 'METRIC' or units.scale_length != 1.0:
        operator.report({'ERROR'}, "Scene units must be Metric with a Unit Scale of 1.0, now its " + str(units.scale_length) + "!")
        return False
    if len(selection) < 2:
        operator.report({'ERROR'}, "2 or more object must be selected!")
        return False
    if properties.save_textures and properties.folder_path == '':
        operator.report({'ERROR'}, "No specified folder path")
        return False
    if not_supported_texture != -1:
        operator.report({'ERROR'}, "Texture " + str(not_supported_texture + 1) + " has errors")
        return False

    textures_list = get_textures_list_settings(context)

    if len(textures_list) == 0:
        operator.report({'ERROR'}, "No textures configured for export")
        return

    size = find_texture_dimensions(selection)
    create_uv_map(context, selection, size)

    progress = ProgressBar('Creating textures {1} of {0}', len(textures_list))

    # Start the texture creation for each one set
    for idx in range(len(textures_list)):
        if textures_list[idx].rgb == 'none' and textures_list[idx].alpha == 'none':
            progress += 1
            continue
        create_texture(operator, context, selection, progress, size, idx)

    progress.finish()

    bpy.ops.object.select_all(action='DESELECT')

    for obj in selection:
        obj.select_set(True)

    return True
