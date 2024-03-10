import bmesh
import mathutils
import numpy
import numpy as np

from ..Properties import *


def __set_origin(obj: bpy.types.Object, global_origin=mathutils.Vector((0, 0, 0))):
    bpy.context.scene.cursor.location = global_origin

    with bpy.context.temp_override(selected_editable_objects=[obj]):
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')


def __find_pivot(context, obj):
    pivot_properties = get_calculate_pivot_settings(context)
    item_type = pivot_properties.item_type

    if item_type == 'overlap':
        from mathutils.bvhtree import BVHTree

        def create_bvh_tree_from_object(obj) -> tuple[bmesh.types.BMesh, BVHTree]:
            bm: bmesh.types.BMesh = bmesh.new()
            bm.from_mesh(obj.data)
            bm.transform(obj.matrix_world)
            bm.faces.ensure_lookup_table()
            bvh = BVHTree.FromBMesh(bm)
            return bm, bvh

        def check_bvh_intersection(obj_1, obj_2) -> tuple[bool, mathutils.Vector]:
            bm1, bvh1 = create_bvh_tree_from_object(obj_1)
            bm2, bvh2 = create_bvh_tree_from_object(obj_2)

            overlapping_faces: list[tuple[int, int]] = bvh1.overlap(bvh2)

            if len(overlapping_faces) == 0:
                bm1.free()
                bm2.free()
                return False, mathutils.Vector((0, 0, 0))

            overlapping_face_positions = np.array([])
            overlapping_face_positions.shape = (0, 3)
            for face in overlapping_faces:
                face_position = bm1.faces[face[0]].calc_center_median()
                overlapping_face_positions = numpy.append(overlapping_face_positions, [[face_position[0], face_position[1], face_position[2]]], axis=0)

            bm1.free()
            bm2.free()

            result = mathutils.Vector((overlapping_face_positions.mean(axis=0)))

            return True, result

        success, result = check_bvh_intersection(obj, obj.parent)
        if success:
            return obj.matrix_world.inverted() @ result
        item_type = 'vertex'

    parent_obj = obj.parent
    parent_matrix_world_inverted = parent_obj.matrix_world.inverted()

    obj_data: bpy.types.Mesh = obj.data

    min_distance = 99999999999
    closest_item_position = (0, 0, 0)

    dtype = [('distance', float), ('x', float), ('y', float), ('z', float)]
    closest_items: numpy.array = np.array([], dtype=dtype)

    def process_pivot_position(item_local_position):
        nonlocal min_distance
        nonlocal closest_item_position
        nonlocal closest_items

        item_world_position = obj.matrix_world @ item_local_position
        parent_relative_pos = parent_matrix_world_inverted @ item_world_position

        (_, closest_point_on_mesh, _, _) = parent_obj.closest_point_on_mesh(origin=parent_relative_pos)

        world_point_on_mesh = parent_obj.matrix_world @ closest_point_on_mesh

        distance = (world_point_on_mesh - item_world_position).length

        if min_distance > distance:
            min_distance = distance
            closest_item_position = item_local_position

        closest_items = numpy.append(closest_items, np.array([(distance, item_local_position[0], item_local_position[1], item_local_position[2])], dtype=dtype), axis=0)

    if item_type == 'vertex':
        vertex: bpy.types.MeshVertex
        for vertex in obj_data.vertices:
            vertex_position = vertex.co
            process_pivot_position(vertex_position)
    else:
        bm = bmesh.new()
        bm.from_mesh(obj_data)

        face: bmesh.types.BMFace
        for face in bm.faces:
            face_center = face.calc_center_median()
            process_pivot_position(face_center)

    if pivot_properties.calculation_type == 'mean':
        closest_items = np.sort(closest_items, axis=0, order="distance")

        closest_included_positions: numpy.array = np.array([])
        closest_included_positions.shape = (0, 3)

        for item in closest_items:
            if abs(item[0] - min_distance) <= pivot_properties.max_distance:
                closest_included_positions = numpy.append(closest_included_positions, [[item[1], item[2], item[3]]], axis=0)
            else:
                break

        closest_item_position = mathutils.Vector((closest_included_positions.mean(axis=0)))

    return closest_item_position


def __find_parentless_pivot(context, obj):
    pivot_properties = get_calculate_pivot_settings(context)
    if pivot_properties.no_parent_pivot_type == 'origin':
        return mathutils.Vector((0, 0, 0))

    obj_data: bpy.types.Mesh = obj.data

    dtype = [('world_z', float), ('x', float), ('y', float), ('z', float)]
    lowest_items: numpy.array = np.array([], dtype=dtype)

    vertex: bpy.types.MeshVertex
    for vertex in obj_data.vertices:
        vertex_position = vertex.co
        world_position = obj.matrix_world @ vertex_position
        lowest_items = numpy.append(lowest_items, np.array([(world_position[2], vertex_position[0], vertex_position[1], vertex_position[2])], dtype=dtype), axis=0)

    lowest_items = np.sort(lowest_items, axis=0, order="world_z")

    closest_included_positions: numpy.array = np.array([])
    closest_included_positions.shape = (0, 3)

    min_distance = lowest_items[0][0]
    for item in lowest_items:
        if abs(item[0] - min_distance) <= pivot_properties.max_z_difference:
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

    __set_rotation(obj, (obj.matrix_world @ furthest_location) - (obj.matrix_world @ pivot))


def prepare_mesh(context, selection):
    pivot_properties = get_calculate_pivot_settings(context)
    rotation_properties = get_calculate_rotation_settings(context)

    obj: bpy.types.Object

    # Cache current cursor location
    cached_cursor_location = bpy.context.scene.cursor.location

    from ..Utils import ProgressBar
    progress = ProgressBar('Processing meshes {1} of {0}', len(selection))

    idx = 0
    for obj in selection:
        idx += 1
        if obj.type != 'MESH':
            progress += 1
            continue

        if pivot_properties.enabled:
            if obj.parent is not None and obj.parent.type == 'MESH':
                pivot = __find_pivot(context, obj)
            else:
                pivot = __find_parentless_pivot(context, obj)
            __set_origin(obj, obj.matrix_world @ pivot)
        else:
            pivot = obj.matrix_world.inverted() @ obj.matrix_world.translation

        if not rotation_properties.enabled:
            progress += 1
            continue

        with bpy.context.temp_override(selected_editable_objects=[obj]):
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

        __find_rotation(context, obj, pivot)
        progress += 1

    progress.finish()

    # Set back cursor location to cached
    bpy.context.scene.cursor.location = cached_cursor_location
