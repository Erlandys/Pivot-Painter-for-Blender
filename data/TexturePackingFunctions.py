from typing import Type

import bpy
import random
import mathutils
import numpy as np

from ..Utils import *


###########################################################
##################### ALPHA FUNCTIONS #####################
###########################################################

class TexturePacking:
    properties: 'Properties.PivotPainterTextureProperties'
    is_hdr: bool
    support_hdr: bool = True
    support_ldr: bool = True
    selection: list[bpy.types.Object] = []

    def __init__(self, properties: 'Properties.PivotPainterTextureProperties', selection: list[bpy.types.Object], is_hdr: bool):
        self.properties = properties
        self.selection = selection
        self.is_hdr = is_hdr

    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        pass

    def has_post_process(self) -> bool:
        return False

    def post_process(self, current_value: float | list[float]) -> float | list[float]:
        return current_value

    def support_type(self, hdr: bool):
        if hdr:
            return self.support_hdr
        return self.support_ldr


class TexturePackingGroup(TexturePacking):
    __dependencies: list['TexturePacking'] = []

    def add_dependency(self, dependency_type: Type['TexturePacking']):
        dep = TexturePacking.__new__(dependency_type)
        dep.__init__(self.properties, self.is_hdr)
        self.__dependencies.append(dep)

    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        result: list[float] = []
        for dep in self.__dependencies:
            result.append(dep.process_object(obj))
        return result

    def has_post_process(self) -> bool:
        for dep in self.__dependencies:
            if dep.has_post_process():
                return True
        return False

    def post_process(self, current_value: float | list[float]) -> float | list[float]:
        result: list[float] = []

        for dep in self.__dependencies:
            result.append(dep.post_process(current_value))

        return result


class PackObjectParentIndex(TexturePacking):
    support_ldr = False

    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        if obj.parent and obj.parent in self.selection:
            index: int = int(self.selection.index(obj.parent))
        else:
            index: int = int(self.selection.index(obj))
        # return index
        return pack_texture_bits(index)


class PackObjectParentsNum(TexturePacking):
    num_max_parent: int = 0

    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        num_parents = 0
        parent = obj.parent
        while parent is not None and parent.type == 'MESH':
            num_parents += 1
            parent = parent.parent

        if num_parents > self.num_max_parent:
            self.num_max_parent = num_parents

        return num_parents

    def post_process(self, current_value: float) -> float | list[float]:
        return current_value / self.num_max_parent


class PackNormalizedObjectParentsNum(TexturePacking):
    def has_post_process(self) -> bool:
        return True


class PackRandomFloat(TexturePacking):
    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        return random.random()


class PackDiagonalBoundBoxLength(TexturePacking):
    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        scale = self.get_scale(obj)

        # Vector from the origin point to the min vertex position of the boundbox, scaled
        vec1 = mathutils.Vector((obj.bound_box[0][0] * scale.x, obj.bound_box[0][1] * scale.y, obj.bound_box[0][2] * scale.z))
        vec2 = mathutils.Vector((obj.bound_box[6][0] * scale.x, obj.bound_box[6][1] * scale.y, obj.bound_box[6][2] * scale.z))

        diagonal_vector = vec1 - vec2
        length = diagonal_vector.length

        # Match Unreal length
        length *= 100

        if not self.is_hdr:
            length = length / 8
            length = np.clip(length, 1, 256)
            length = length / 256
        return length

    def get_scale(self, obj: bpy.types.Object) -> mathutils.Vector:
        return mathutils.Vector((1.0, 1.0, 1.0))


class PackDiagonalBoundBoxScaledLength(PackDiagonalBoundBoxLength):
    def get_scale(self, obj: bpy.types.Object) -> mathutils.Vector:
        return obj.matrix_world.to_scale()


class PackSelectionOrder(TexturePacking):
    support_ldr = False

    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        return pack_texture_bits(obj["SelectionOrder"])


class PackEmptyAlpha(TexturePacking):
    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        return 0


class PackExtent(TexturePacking):
    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        extent = self.get_extent(obj)

        # Convert to Unreal Measures
        extent *= 100

        if not self.is_hdr:
            extent /= 8
            extent = np.clip(extent, 1, 256) / 256
        return extent

    def get_extent(self, obj: bpy.types.Object) -> float:
        return 1


class PackXExtent(PackExtent):
    def get_extent(self, obj: bpy.types.Object) -> float:
        return obj.dimensions.x


class PackYExtent(PackExtent):
    def get_extent(self, obj: bpy.types.Object) -> float:
        return obj.dimensions.y


class PackZExtent(PackExtent):
    def get_extent(self, obj: bpy.types.Object) -> float:
        return obj.dimensions.z


###########################################################
###########################################################
###########################################################


class PackPivot(TexturePacking):
    support_ldr = False

    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        pivot = obj.matrix_world.to_translation()
        return convert_blender_to_unreal_location(pivot)


class PackAxis(TexturePacking):
    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        axis = self.get_axis(obj)
        rotation = obj.matrix_world.to_euler('XYZ')
        axis.rotate(rotation)

        axis = convert_blender_to_unreal_direction(axis.normalized())
        if self.is_hdr:
            return axis

        return compact_normalized_direction(axis)

    def get_axis(self, obj: bpy.types.Object) -> mathutils.Vector:
        return mathutils.Vector((0.0, 0.0, 0.0))


class PackXAxis(PackAxis):
    def get_axis(self, obj: bpy.types.Object) -> mathutils.Vector:
        return mathutils.Vector((1.0, 0.0, 0.0))


class PackYAxis(PackAxis):
    def get_axis(self, obj: bpy.types.Object) -> mathutils.Vector:
        return mathutils.Vector((0.0, 1.0, 0.0))


class PackZAxis(PackAxis):
    def get_axis(self, obj: bpy.types.Object) -> mathutils.Vector:
        return mathutils.Vector((0.0, 0.0, 1.0))


class PackOrigin(TexturePacking):
    support_ldr = False

    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        scale = obj.matrix_world.to_scale()

        vec1 = mathutils.Vector((obj.bound_box[0][0] * scale[0], obj.bound_box[0][1] * scale[1], obj.bound_box[0][2] * scale[2]))
        vec2 = mathutils.Vector((obj.bound_box[6][0] * scale[0], obj.bound_box[6][1] * scale[1], obj.bound_box[6][2] * scale[2]))

        center = vec1 + vec2
        center = center / 2

        wr = obj.matrix_world.to_euler('XYZ')
        center.rotate(wr)

        pivot = obj.matrix_world.to_translation()
        center = center + pivot

        return [center.x, center.y, center.z]


class PackExtents(TexturePacking):
    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        extents: mathutils.Vector = obj.dimensions

        # Convert to Unreal Measures
        extents = extents * 100

        if not self.is_hdr:
            extents = extents / 8
            extents.x = np.clip(extents.x, 1, 256) / 256
            extents.y = np.clip(extents.y, 1, 256) / 256
            extents.z = np.clip(extents.z, 1, 256) / 256

        return [extents.x, extents.y, extents.z]


class PackEmptyRGB(TexturePacking):
    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        return [0, 0, 0]


class PackQuaternion(TexturePacking):
    def process_object(self, obj: bpy.types.Object) -> float | list[float]:
        rotation = obj.matrix_world.to_euler('XYZ')
        rotation = convert_blender_to_unreal_rotation(rotation)
        quaternion = rotation.to_quaternion()

        if self.is_hdr:
            return [quaternion[0], quaternion[1], quaternion[2], quaternion[3]]

        return compact_normalized_rgba(quaternion)


class PackParentsNumRandomDiameter(TexturePackingGroup):
    def __init__(self, properties: 'Properties.PivotPainterTextureProperties', is_hdr: bool):
        super().__init__(properties, is_hdr)
        self.add_dependency(PackNormalizedObjectParentsNum)
        self.add_dependency(PackRandomFloat)
        self.add_dependency(PackDiagonalBoundBoxScaledLength)
