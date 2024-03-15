import sys
import time
from ctypes import POINTER, pointer, c_int, cast, c_float

import bpy
import mathutils
import numpy
import numpy as np


def pack_texture_bits(index):
    """ Store Int to float """
    # Not sure why is this necessary , and doesn't simply put the integer bits into the float directly. but it gets reverse in shader custom code. I include it for consistency, and ease of use.
    index = int(index)

    # Need to check how the change from 32 float to 16(the exponent is the suspect) when saving affects the bits, if it does, probably the reason for this function. Otherwise I don't understand why cannot put int as float(and use 2^8 precision).
    index = index + 1024
    sign = (index & 0x8000) << 16

    if (index & 0x7fff) == 0:
        exponent = 0
    else:
        exponent = index >> 10
        exponent = exponent & 0x1f
        exponent = exponent - 15
        exponent = exponent + 127
        exponent = exponent << 23

    mantissa = index & 0x3ff
    mantissa = mantissa << 13

    index = sign | exponent | mantissa

    # make this into a c integer
    # cp points to the index (c_int conversion is needed from ctypes for point there to work)
    index_ptr = pointer(c_int(index))

    # cast the int pointer to a float pointer
    # cast(obj, type) returns new instance that point to the same memory block, as type c_float by using POINTER(type)
    float_ptr = cast(index_ptr, POINTER(c_float))
    return float_ptr.contents.value


def convert_blender_to_unreal_location(location):
    x = location[0] * 100
    y = location[1] * 100
    z = location[2] * 100
    return [x, -y, z]


def convert_blender_to_unreal_direction(direction):
    return [direction[0], -direction[1], direction[2]]


def convert_blender_to_unreal_rotation(rotation):
    return mathutils.Euler((-rotation[1], -rotation[2], rotation[0]))


def compact_normalized_direction(direction):
    return [
        (direction[0] + 1.0) / 2.0,
        (direction[1] + 1.0) / 2.0,
        (direction[2] + 1.0) / 2.0]


def compact_normalized_rgba(rgba):
    return [
        (rgba[0] + 1.0) / 2.0,
        (rgba[1] + 1.0) / 2.0,
        (rgba[2] + 1.0) / 2.0,
        (rgba[3] + 1.0) / 2.0]


def reorder_selection_by_parents(selection) -> list['bpy.types.Object']:
    import bpy

    selection_order: dict[int, list[bpy.types.Object]] = {}
    num_max_parents = 0

    obj: bpy.types.Object
    for obj in selection:
        if obj is None or obj.type != 'MESH':
            continue

        obj_parent = obj.parent
        num_parents = 0
        while obj_parent:
            num_parents += 1
            obj_parent = obj_parent.parent

        if num_max_parents < num_parents:
            num_max_parents = num_parents

        if num_parents in selection_order:
            selection_order[num_parents].append(obj)
        else:
            selection_order[num_parents] = [obj]

    result_order: list[bpy.types.Object] = []
    for idx in reversed(range(num_max_parents + 1)):
        if idx in selection_order:
            result_order.extend(selection_order[idx])

    return result_order


def apply_transform(ob, use_location=False, use_rotation=False, use_scale=False):
    import bpy
    import mathutils

    with bpy.context.temp_override(selected_editable_objects=[ob]):
        bpy.ops.object.transform_apply(location=use_location, rotation=use_rotation, scale=use_scale)


def get_xy_from_index(size: list[int], idx: int) -> tuple[int, int]:
    from math import floor
    return idx % size[0], size[1] - floor(idx / size[0]) - 1


def register_classes_from_module(module_name: str, class_type):
    import bpy
    import inspect

    for name, obj in inspect.getmembers(sys.modules[module_name]):
        if not inspect.isclass(obj):
            continue
        if not issubclass(obj, class_type):
            continue
        bpy.utils.register_class(obj)


def unregister_classes_from_module(module_name: str, class_type):
    import bpy
    import inspect

    for name, obj in inspect.getmembers(sys.modules[module_name]):
        if not inspect.isclass(obj):
            continue
        if not issubclass(obj, class_type):
            continue

        bpy.utils.unregister_class(obj)


class ProgressBar:
    __description: str
    __message: str
    __total_tasks: int
    __progress: float
    __width: int
    __stopped: bool = False
    __start_time: float
    __parent: 'ProgressBar' = None
    __parent_progress: float
    __window_manager: bpy.types.WindowManager | None = None

    def __init__(self, description: str, tasks: int, parent: 'ProgressBar' = None, width: int = 40, parent_progress: float = 0, show_cursor_progress: bool = True):
        self.__description = description
        self.__total_tasks = tasks
        self.__progress = 0
        self.__width = width
        self.__start_time = time.time()
        self.__parent = parent
        if parent is None:
            self.__update_message()
            self.__print_progress()
            if show_cursor_progress:
                self.__window_manager = bpy.context.window_manager
                self.__window_manager.progress_begin(0, 100)
        else:
            self.__parent_progress = parent_progress

    def new_sub_progress(self, description: str, tasks: int):
        sub_progress = ProgressBar(description, tasks, parent=self, parent_progress=self.__progress)
        return sub_progress

    def finish(self, success: bool = True):
        if self.__stopped:
            return

        if success:
            self.__progress = self.__total_tasks
        self.__update_message()

        self.__stopped = True

        if self.__parent is not None:
            if success:
                self.__parent._set_progress(self.__parent_progress + 1)
            return

        sys.stdout.write('\r' + self.__message + '\r\n')
        sys.stdout.flush()
        if self.__window_manager is not None:
            self.__window_manager.progress_end()

    def __print_progress(self):
        if self.__parent is not None:
            return

        sys.stdout.write('\r' + self.__message)
        sys.stdout.flush()

    def __update_message(self):
        alpha: float = self.__progress / float(self.__total_tasks)

        alpha = numpy.clip(alpha, 0, 1)

        if self.__parent is not None:
            self.__parent._set_progress(self.__parent_progress + alpha)
            return

        from math import floor
        self.__message = self.__description.format(self.__total_tasks, floor(self.__progress)) + ': \t'

        if alpha * 100 < 10:
            self.__message += '  '
        elif alpha * 100 < 100:
            self.__message += ' '

        if self.__window_manager is not None:
            self.__window_manager.progress_update(alpha * 100)

        self.__message += '{:.2f}% '.format(alpha * 100)
        self.__message += '['
        self.__message += '#' * (round(alpha * self.__width))
        self.__message += '-' * (round((1.0 - alpha) * self.__width))
        self.__message += '] ' + self.__get_duration()

    def __get_duration(self) -> str:
        elapsed_time = time.time() - self.__start_time
        minutes, seconds = divmod(elapsed_time, 60)
        return '{:02}:{:02}.{:03}'.format(int(minutes), int(seconds), int((seconds % 1) * 1000))

    def __del__(self):
        self.finish()

    def __add__(self, other):
        return self

    def _set_progress(self, progress: float):
        self.__progress = progress
        self.__update_message()
        self.__print_progress()

    def __iadd__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            self.__progress = np.clip(self.__progress + other, 0, self.__total_tasks)
            self.__update_message()
            if self.__parent is None:
                self.__print_progress()
        return self

    def __str__(self):
        return self.__message
