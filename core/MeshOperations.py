import time

import bpy
import mathutils.kdtree


def split_mesh(selection: list[bpy.types.Object]):
    collection: bpy.types.Collection = None
    new_collection_name: str = None
    for obj in selection:
        if obj.users_collection is None or obj.users_collection[0] is None:
            new_collection_name = obj.name
            continue
        collection = obj.users_collection[0]
        new_collection_name = obj.name
        break

    if new_collection_name is None:
        return False

    new_collection = bpy.data.collections.new("PivotPainter_" + new_collection_name)

    if new_collection is not None:
        collection.children.link(new_collection)

    bpy.ops.object.duplicate(linked=False)

    bpy.ops.mesh.separate(type='LOOSE')

    new_selection = bpy.context.selected_objects
    for obj in new_selection:
        if obj.users_collection is not None:
            for obj_collection in obj.users_collection:
                if obj_collection is not None:
                    obj_collection.objects.unlink(obj)
        new_collection.objects.link(obj)

    for obj in selection:
        obj.hide_set(True)


def generate_hierarchy(operator: bpy.types.Operator, context: bpy.types.Context, selection: list[bpy.types.Object]):
    from ..Properties import get_mesh_operations_settings

    properties = get_mesh_operations_settings(context)

    if len(properties.base_meshes) == 0:
        operator.report({'ERROR'}, 'No base meshes were selected')
        return False

    base_mesh_objects = set()
    for base_mesh in properties.base_meshes:
        if bpy.data.objects.find(base_mesh.name) == -1:
            operator.report({'ERROR'}, "Base mesh '" + base_mesh.name + "' does not exist.\nRecreate base meshes list.")
            return False
        base_mesh_obj: bpy.types.Object = bpy.data.objects[base_mesh.name]
        if base_mesh_obj.type != 'MESH':
            operator.report({'ERROR'}, "Base mesh '" + base_mesh.name + "' is not a mesh.\nRecreate base meshes list.")
            return False
        base_mesh_objects.add(base_mesh_obj)

    leaves_selection = selection
    for obj in base_mesh_objects:
        if obj in leaves_selection:
            leaves_selection.remove(obj)

    if len(leaves_selection) == 0:
        operator.report({'ERROR'}, "Only base mesh objects selected. Possible children objects must be selected.")
        return False

    generate_hierarchy_from_base_meshes(base_mesh_objects, leaves_selection)
    return True


def generate_hierarchy_from_base_meshes(base_mesh_objects: set[bpy.types.Object], leaves_selection: list[bpy.types.Object]):
    obj_to_overlaps: dict[bpy.types.Object, set[bpy.types.Object]] = create_overlaps_dict(list(base_mesh_objects) + leaves_selection)

    def remove_overlap(obj: bpy.types.Object, obj2: bpy.types.Object):
        nonlocal obj_to_overlaps

        if obj in obj_to_overlaps:
            if obj2 in obj_to_overlaps[obj]:
                obj_to_overlaps[obj].remove(obj2)
        if obj2 in obj_to_overlaps:
            if obj in obj_to_overlaps[obj2]:
                obj_to_overlaps[obj2].remove(obj)

    def set_parent(parent: bpy.types.Object, child: bpy.types.Object):
        nonlocal obj_to_overlaps

        remove_overlap(child, parent)

        bpy.ops.object.select_all(action='DESELECT')
        child.select_set(True)
        parent.select_set(True)
        bpy.context.view_layer.objects.active = parent
        bpy.ops.object.parent_set()
        child.select_set(False)
        parent.select_set(False)

    # All base meshes must be in iterated objects from the beginning
    iterated_objects: set[bpy.types.Object] = base_mesh_objects

    # First iteration goes through base meshes, then goes through added children
    objects_to_iterate = list(iterated_objects)

    idx = 0
    from ..Utils import ProgressBar

    while len(objects_to_iterate) > 0:
        new_objects_to_iterate = []
        progress_bar = ProgressBar(str(idx + 1) + " iteration, on {1} of {0} objects", len(objects_to_iterate))
        for obj in objects_to_iterate:
            if obj not in obj_to_overlaps:
                progress_bar += 1
                continue

            overlapping_objects = obj_to_overlaps[obj].copy()
            if len(overlapping_objects) < 1:
                progress_bar += 1
                continue
            for overlapped_obj in overlapping_objects:
                if overlapped_obj in iterated_objects:
                    remove_overlap(obj, overlapped_obj)
                    continue
                set_parent(obj, overlapped_obj)
                iterated_objects.add(overlapped_obj)
                new_objects_to_iterate.append(overlapped_obj)
            progress_bar += 1

        # Add all added children as next layer objects
        objects_to_iterate = new_objects_to_iterate
        idx += 1
        progress_bar.finish()


def create_overlaps_dict(objects: list[bpy.types.Object]) -> dict[bpy.types.Object, set[bpy.types.Object]]:
    import bmesh
    from mathutils.bvhtree import BVHTree
    from ..Utils import ProgressBar

    def create_bvh_tree_from_object(obj_to_read: bpy.types.Object) -> BVHTree:
        bm: bmesh.types.BMesh = bmesh.new()
        bm.from_mesh(obj_to_read.data)
        bm.transform(obj_to_read.matrix_world)
        bm.faces.ensure_lookup_table()
        bvh = BVHTree.FromBMesh(bmesh=bm, epsilon=0.1)
        bm.free()
        return bvh

    progress_bar = ProgressBar("Generating overlaps", len(objects) * 2)
    obj_to_bvh_tree: dict[bpy.types.Object, BVHTree] = {}
    for obj in objects:
        obj_to_bvh_tree[obj] = create_bvh_tree_from_object(obj)
        progress_bar += 1

    obj_to_overlaps: dict[bpy.types.Object, set[bpy.types.Object]] = {}
    for obj in objects:
        first_bvh = obj_to_bvh_tree[obj]
        for obj2 in objects:
            if obj == obj2:
                continue
            second_bvh = obj_to_bvh_tree[obj2]
            if len(first_bvh.overlap(second_bvh)) == 0:
                continue

            if obj not in obj_to_overlaps:
                obj_to_overlaps[obj] = {obj2}
            else:
                if obj2 not in obj_to_overlaps[obj]:
                    obj_to_overlaps[obj].add(obj2)

            if obj2 not in obj_to_overlaps:
                obj_to_overlaps[obj2] = {obj}
            else:
                if obj not in obj_to_overlaps[obj2]:
                    obj_to_overlaps[obj2].add(obj)
        progress_bar += 1

    return obj_to_overlaps


def copy_uvs(operator: bpy.types.Operator, context: bpy.types.Context, selection: list[bpy.types.Object]):
    from ..core.CreateTextures import find_texture_dimensions, create_uv_map

    size = find_texture_dimensions(selection)
    create_uv_map(context, selection, size)

    from ..Properties import get_mesh_operations_settings, get_texture_settings
    from ..Utils import ProgressBar

    texture_properties = get_texture_settings(context)
    properties = get_mesh_operations_settings(context)
    if bpy.data.objects.find(properties.copy_uvs_target) == -1:
        operator.report({'ERROR'}, 'Object ' + properties.copy_uvs_target + ' does not exist. Failed to copy UVs!')
        return
    target_obj: bpy.types.Object = bpy.data.objects[properties.copy_uvs_target]
    if target_obj.type != 'MESH':
        operator.report({'ERROR'}, 'Object ' + properties.copy_uvs_target + ' is not mesh. Failed to copy UVs!')
        return

    target_obj_data: bpy.types.Mesh = target_obj.data

    uv_map = texture_properties.uv_map_name

    context.view_layer.objects.active = target_obj
    target_obj.select_set(True)

    bpy.ops.object.select_all(action='DESELECT')
    num_loops = 0
    for obj in selection:
        obj.select_set(True)
        num_loops += len(obj.data.loops)

    if uv_map not in target_obj_data.uv_layers:
        target_obj_data.uv_layers.new(name=uv_map, do_init=False)

    progress = ProgressBar('Copying UVs {1} of {0}', num_loops)

    tolerance = pow(10, -(properties.copy_uvs_uv_precision_lookup))

    target_obj_data.uv_layers[texture_properties.uv_map_name].active = True

    kd = mathutils.kdtree.KDTree(len(target_obj_data.vertices))
    for idx, vertex in enumerate(target_obj_data.vertices):
        kd.insert(target_obj.matrix_world @ vertex.co, idx)
    kd.balance()

    vertex_index_to_loops: dict[int, list[int]] = {}
    for loop in target_obj_data.loops:
        if loop.vertex_index in vertex_index_to_loops:
            vertex_index_to_loops[loop.vertex_index].append(loop.index)
        else:
            vertex_index_to_loops[loop.vertex_index] = [loop.index]

    num_found_none = 0
    num_missing = 0
    for obj in selection:
        obj_data: bpy.types.Mesh = obj.data

        for loop in obj_data.loops:
            vertex = obj.matrix_world @ obj_data.vertices[loop.vertex_index].co
            uv = obj_data.uv_layers[texture_properties.uv_map_name].data[loop.index].uv
            found_vertices = kd.find_range(vertex, tolerance)
            if len(found_vertices) == 0:
                num_found_none += 1
            elif len(found_vertices) > 1:
                for found_vertex in found_vertices:
                    vertex_index = found_vertex[1]
                    if vertex_index in vertex_index_to_loops:
                        for loop_index in vertex_index_to_loops[vertex_index]:
                            target_obj_data.uv_layers[texture_properties.uv_map_name].data[loop_index].uv = uv
                    else:
                        num_missing += 1
            else:
                vertex_index = found_vertices[0][1]
                if vertex_index in vertex_index_to_loops:
                    for loop_index in vertex_index_to_loops[vertex_index]:
                        target_obj_data.uv_layers[texture_properties.uv_map_name].data[loop_index].uv = uv
                else:
                    num_missing += 1

        obj_data.uv_layers[texture_properties.uv_map_name].active = False

        progress += len(obj_data.loops)

    target_obj_data.uv_layers[texture_properties.uv_map_name].active = True

    progress.finish(True)

    success: bool = num_missing + num_found_none == 0
    if not success:
        print('Missing ' + str(num_found_none + num_missing) + ' of ' + str(len(target_obj_data.loops)) + '.')
        operator.report({'WARNING'}, 'Failed to fully match vertices. Missing ' + str(num_found_none + num_missing) + ' of ' + str(len(target_obj_data.loops)) + '.')

    return success
