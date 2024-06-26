import bmesh
import mathutils
import numpy
import numpy as np

from ..Properties import *


def __set_origin(obj: bpy.types.Object, global_origin=mathutils.Vector((0, 0, 0))):
    bpy.context.scene.cursor.location = global_origin

    with bpy.context.temp_override(selected_editable_objects=[obj]):
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')


def __find_pivot(context, obj, obj_structs: tuple[mathutils.kdtree.KDTree, mathutils.bvhtree.BVHTree, bmesh.types.BMesh], parent_structs: tuple[mathutils.kdtree.KDTree, mathutils.bvhtree.BVHTree, bmesh.types.BMesh]):
    pivot_properties = get_calculate_pivot_settings(context)
    item_type = pivot_properties.item_type

    if item_type == 'overlap':
        def check_bvh_intersection(obj_1: tuple[mathutils.kdtree.KDTree, mathutils.bvhtree.BVHTree, bmesh.types.BMesh], obj_2: tuple[mathutils.kdtree.KDTree, mathutils.bvhtree.BVHTree, bmesh.types.BMesh]) -> tuple[bool, mathutils.Vector]:
            overlapping_faces: list[tuple[int, int]] = obj_1[1].overlap(obj_2[1])

            if len(overlapping_faces) == 0:
                return False, mathutils.Vector((0, 0, 0))

            overlapping_face_positions = np.array([])
            overlapping_face_positions.shape = (0, 3)
            for face in overlapping_faces:
                face_position = obj_1[2].faces[face[0]].calc_center_median()
                overlapping_face_positions = numpy.append(overlapping_face_positions, [[face_position[0], face_position[1], face_position[2]]], axis=0)

            result = mathutils.Vector((overlapping_face_positions.mean(axis=0)))

            return True, result

        success, result = check_bvh_intersection(obj_structs, parent_structs)
        if success:
            return result

    closest_distance = 1e9
    closest_vertex = mathutils.Vector()
    for vertex in obj.data.vertices:
        world_vertex = obj.matrix_world @ vertex.co
        data = parent_structs[0].find_n(world_vertex, 1)
        if closest_distance > data[0][2]:
            closest_distance = data[0][2]
            closest_vertex = vertex.co

    if pivot_properties.calculation_type == 'mean':
        closest_included_positions: numpy.array = np.array([])
        closest_included_positions.shape = (0, 3)

        for vertex in obj.parent.data.vertices:
            world_vertex = obj.parent.matrix_world @ vertex.co
            data = obj_structs[0].find_range(world_vertex, closest_distance + pivot_properties.max_distance)
            for x in data:
                closest_included_positions = numpy.append(closest_included_positions, [[x[0][0], x[0][1], x[0][2]]], axis=0)
        closest_vertex = mathutils.Vector((closest_included_positions.mean(axis=0)))

    return closest_vertex


def __find_parentless_pivot(context, obj):
    pivot_properties = get_calculate_pivot_settings(context)
    if pivot_properties.no_parent_pivot_type == 'origin':
        return mathutils.Vector((0, 0, 0))

    obj_data: bpy.types.Mesh = obj.data

    dtype = [('axis', float), ('x', float), ('y', float), ('z', float)]
    lowest_items: numpy.array = np.array([], dtype=dtype)

    vertex: bpy.types.MeshVertex
    for vertex in obj_data.vertices:
        vertex_position = vertex.co
        world_position = obj.matrix_world @ vertex_position
        axis_value = 0.0
        if pivot_properties.no_parent_axis == 'x_pos':
            axis_value = -world_position[0]
        elif pivot_properties.no_parent_axis == 'x_neg':
            axis_value = world_position[0]
        elif pivot_properties.no_parent_axis == 'y_pos':
            axis_value = -world_position[1]
        elif pivot_properties.no_parent_axis == 'y_neg':
            axis_value = world_position[1]
        elif pivot_properties.no_parent_axis == 'z_pos':
            axis_value = -world_position[2]
        elif pivot_properties.no_parent_axis == 'z_neg':
            axis_value = world_position[2]
        lowest_items = numpy.append(lowest_items, np.array([(axis_value, vertex_position[0], vertex_position[1], vertex_position[2])], dtype=dtype), axis=0)

    lowest_items = np.sort(lowest_items, axis=0, order="axis")

    closest_included_positions: numpy.array = np.array([])
    closest_included_positions.shape = (0, 3)

    min_distance = lowest_items[0][0]
    for item in lowest_items:
        if abs(item[0] - min_distance) <= pivot_properties.no_parent_max_axis_difference:
            closest_included_positions = numpy.append(closest_included_positions, [[item[1], item[2], item[3]]], axis=0)
        else:
            break

    return mathutils.Vector((closest_included_positions.mean(axis=0)))


def __set_rotation(obj: bpy.types.Object, axis=mathutils.Vector((0, 0, 1))):
    axis = axis.normalized()

    current_rotation_mode = obj.rotation_mode
    obj.rotation_mode = "QUATERNION"

    quat = obj.matrix_world.to_quaternion().inverted() @ axis.to_track_quat('X', 'Z')

    inverted_quat = quat.inverted()
    obj.rotation_quaternion = inverted_quat

    with bpy.context.temp_override(selected_editable_objects=[obj]):
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    obj.rotation_quaternion = quat

    obj.rotation_mode = current_rotation_mode


def __find_rotation(context, obj, pivot):
    properties = get_calculate_rotation_settings(context)

    obj_data: bpy.types.Mesh = obj.data

    if properties.item_type == 'vertex':
        coords = np.zeros(len(obj_data.vertices) * 3, dtype=float)
        obj_data.vertices.foreach_get('co', coords)

    else:
        coords = np.zeros(8 * 3)
        scale = obj.matrix_world.to_scale()
        for idx in range(8):
            coords[idx * 3 + 0] = obj.bound_box[idx][0] * scale[0]
            coords[idx * 3 + 1] = obj.bound_box[idx][1] * scale[1]
            coords[idx * 3 + 2] = obj.bound_box[idx][2] * scale[2]

    coords = coords.reshape(int(len(coords) / 3), 3)

    distances = np.sqrt(np.sum(np.power(np.subtract(coords, [pivot[0], pivot[1], pivot[2]]), 2), axis=1))
    max_dist = np.max(distances)
    distances = np.absolute(np.subtract(distances, max_dist))
    furthest_location = coords[np.where(distances < properties.max_distance)].mean(axis=0)
    furthest_location = mathutils.Vector((furthest_location[0], furthest_location[1], furthest_location[2]))

    return (obj.matrix_world @ furthest_location) - (obj.matrix_world @ pivot)


def prepare_mesh(context, selection):
    from math import ceil
    from ..Utils import ProgressBar

    pivot_properties = get_calculate_pivot_settings(context)
    rotation_properties = get_calculate_rotation_settings(context)

    obj: bpy.types.Object

    with bpy.context.temp_override(selected_editable_objects=selection):
        bpy.ops.object.transform_apply(location=pivot_properties.enabled, rotation=rotation_properties.enabled, scale=True)

    progress = ProgressBar('Arranging meshes {1} of {0}', len(selection))

    obj_by_levels: list[list[bpy.types.Object]] = []

    def create_mesh_data(obj: bpy.types.Object):
        kd = mathutils.kdtree.KDTree(len(obj.data.vertices))
        for idx, vertex in enumerate(obj.data.vertices):
            kd.insert(obj.matrix_world @ vertex.co, idx)
        kd.balance()

        bm: bmesh.types.BMesh = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        bm.faces.ensure_lookup_table()
        bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

        return kd, bvh, bm

    step = ceil(len(selection) / 100)
    idx = 0
    for obj in selection:
        num_parents = 0
        parent = obj.parent
        while parent is not None:
            parent = parent.parent
            num_parents += 1
        for i in range(len(obj_by_levels), num_parents + 1):
            obj_by_levels.append([])
        obj_by_levels[num_parents].append(obj)

        idx += 1

        if idx % step == step - 1:
            progress += step

    progress.finish()

    progress = ProgressBar('Processing meshes {1} of {0}', len(selection))
    target_idx = len(obj_by_levels) - 1
    while target_idx >= 0:
        obj_to_data: dict[bpy.types.Object, tuple[mathutils.kdtree.KDTree, mathutils.bvhtree.BVHTree, bmesh.types.BMesh]] = {}
        obj_to_rot_data: dict[bpy.types.Object, tuple[mathutils.Quaternion, str]] = {}

        step = ceil(len(obj_by_levels[target_idx]) / 100)

        idx = 0
        for obj in obj_by_levels[target_idx]:
            if pivot_properties.enabled:
                if obj.parent is not None and obj.parent.type == 'MESH':
                    mesh_data = create_mesh_data(obj)

                    if obj.parent not in obj_to_data:
                        obj_to_data[obj.parent] = create_mesh_data(obj.parent)

                    parent_data = obj_to_data[obj.parent]
                    pivot = __find_pivot(context, obj, mesh_data, parent_data)
                else:
                    pivot = __find_parentless_pivot(context, obj)

                obj.data.transform(mathutils.Matrix.Translation(-pivot))
                obj.location += pivot
                for c in obj.children:
                    c.matrix_parent_inverse.translation -= pivot

            if rotation_properties.enabled:
                rotation = __find_rotation(context, obj, mathutils.Vector((0, 0, 0))).normalized()

                current_rotation_mode = obj.rotation_mode
                obj.rotation_mode = "QUATERNION"

                quat = obj.matrix_world.to_quaternion().inverted() @ rotation.to_track_quat('X', 'Z')

                obj.rotation_quaternion = quat.inverted()
                obj_to_rot_data[obj] = quat, current_rotation_mode

            idx += 1

            if idx % step == step - 1:
                progress += step

        if rotation_properties.enabled:
            idx = 0
            with bpy.context.temp_override(selected_editable_objects=obj_by_levels[target_idx]):
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            for obj, data in obj_to_rot_data.items():
                obj.rotation_quaternion = data[0]
                obj.rotation_mode = data[1]
                idx += 1

        if len(obj_by_levels[target_idx]) > 0:
            bpy.context.view_layer.update()

        target_idx -= 1

    progress.finish()
