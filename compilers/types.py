import collections

import compilers.util as util
import compilers.errors as errs


class Type:
    def __init__(self, length: int):
        self.length = length

    def memory_length(self):
        return self.length

    def strong_convertible(self, left_tar_type):
        """
        This method returns True iff self can be converted to the 'left_tar_type' without warning.

        :param left_tar_type:
        :return:
        """
        return self == left_tar_type

    def weak_convertible(self, left_tar_type):
        """
        This method returns True iff self can be converted to the 'left_tar_type', but a warning is produced.

        Note that this method does not necessarily returns True if strong_convertible returns True.

        :param left_tar_type:
        :return:
        """
        return self.strong_convertible(left_tar_type)

    def convertible_to(self, left_tar_type, lf):
        """
        Returns True if strong_convertible or weak_convertible returns True.

        Prints warning message if strong_convertible returns False, but weak_convertible returns True.

        :param left_tar_type
        :param lf
        :return:
        """
        if self.strong_convertible(left_tar_type):
            return True
        elif self.weak_convertible(left_tar_type):
            print("Warning: implicit conversion from {} to {}. {}".format(self, left_tar_type, lf))
            return True
        else:
            return False

    def check_convertibility(self, left_tar_type, lf) -> None:
        if not self.convertible_to(left_tar_type, lf):
            raise errs.TplCompileError(f"Cannot convert '{self}' to '{left_tar_type}'. ", lf)

    def type_name(self):
        raise errs.TplCompileError(f"Type '{self}' does not have name.")

    def is_void(self):
        return self.length == 0

    def __str__(self):
        return "Type of length " + str(self.length)

    def __repr__(self):
        return self.__str__()


class PrimitiveType(Type):
    def __init__(self, type_name: str, length: int):
        super().__init__(length)

        self.t_name = type_name

    def weak_convertible(self, left_tar_type: Type):
        if self.t_name == "int" and isinstance(left_tar_type, PointerType):
            return True
        else:
            return super().weak_convertible(left_tar_type)

    def type_name(self):
        return self.t_name

    def __eq__(self, other):
        return isinstance(other, PrimitiveType) and other.t_name == self.t_name

    def __hash__(self):
        return hash(self.t_name)

    def __str__(self):
        return self.t_name


class PointerType(Type):
    def __init__(self, base: Type):
        super().__init__(util.PTR_LEN)

        self.base = base

    def strong_convertible(self, left_tar_type):
        if self == TYPE_VOID_PTR:
            return isinstance(left_tar_type, PointerType) or isinstance(left_tar_type, ArrayType)
        elif left_tar_type == TYPE_VOID_PTR:
            return True
        elif isinstance(left_tar_type, PointerType):
            return self.base.strong_convertible(left_tar_type.base)
        else:
            return super().strong_convertible(left_tar_type)

    def weak_convertible(self, left_tar_type):
        if isinstance(left_tar_type, PrimitiveType) and left_tar_type.t_name == "int":
            return True
        elif isinstance(left_tar_type, PointerType):
            return self.base.weak_convertible(left_tar_type.base)
        else:
            return super().weak_convertible(left_tar_type)

    def type_name(self):
        return "*" + self.base.type_name()

    def __eq__(self, other):
        return isinstance(other, PointerType) and self.base == other.base

    def __str__(self):
        return "*" + str(self.base)


class CompileTimeFunctionType(Type):
    def __init__(self, name, rtype: Type):
        super().__init__(0)

        self.name = name
        self.rtype = rtype

    def memory_length(self):
        raise errs.TplCompileError(f"Compile time function '{self.name}' does not occupy memory. ")

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name


class SpecialCtfType(CompileTimeFunctionType):
    def __init__(self, name):
        super().__init__(name, None)


class CallableType(Type):
    def __init__(self, param_types, rtype):
        super().__init__(util.PTR_LEN)

        self.param_types: [Type] = param_types
        self.rtype: Type = rtype

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.param_types == other.param_types and \
               self.rtype == other.rtype

    def __str__(self):
        return "{}({} -> {})".format(self.__class__.__name__, self.param_types, self.rtype)

    def __repr__(self):
        return self.__str__()


class FuncType(CallableType):
    def __init__(self, param_types, rtype):
        super().__init__(param_types, rtype)

    def strong_convertible(self, left_tar_type):
        if isinstance(left_tar_type, FuncType):
            if len(self.param_types) == len(left_tar_type.param_types):
                if self.rtype.strong_convertible(left_tar_type.rtype):
                    for i in range(len(self.param_types)):
                        if not self.param_types[i].strong_convertible(left_tar_type.param_types[i]):
                            return False
                    return True
        return False


class FunctionPlacer(Type):
    def __init__(self, first_t: CallableType, first_addr: int):
        super().__init__(0)

        self.poly = util.NaiveDict(params_eq)  # functions with same name | func_type: ptr

        self.add_poly(first_t, first_addr)

    def add_poly(self, type_: CallableType, addr: int):
        if type_ in self.poly:
            raise errs.TplEnvironmentError("Function already defined.")
        self.poly[type_] = addr
        # print(self.poly)

    def get_only(self):
        return self.poly.get_only()

    def get_type_and_ptr_call(self, arg_types: list, lf) -> (CallableType, int):
        return find_closet_func(self.poly, arg_types, "fn", False, lambda poly_d, i: poly_d.keys[i], lf)

    def get_type_and_ptr_def(self, param_types: list, lf) -> (CallableType, int):
        t_addr = self.poly.get_entry_by(param_types, func_eq_params)
        if t_addr is None:
            raise errs.TplEnvironmentError(f"Cannot resolve param {param_types}. ", lf)
        return t_addr

    def __str__(self):
        return "FunctionPlacer:" + str(self.poly)


class MethodType(FuncType):
    def __init__(self, param_types, rtype, def_class, abstract: bool, const: bool):
        super().__init__(param_types, rtype)

        self.defined_class = def_class
        self.abstract = abstract
        self.const = const

    def __str__(self):
        return ("abstract " if self.abstract else "") + "method " + super().__str__()

    def copy(self):
        return MethodType(self.param_types.copy(), self.rtype, self.defined_class, self.abstract, self.const)


class NativeFuncType(CallableType):
    def __init__(self, param_types, rtype):
        super().__init__(param_types, rtype)


class ClassType(Type):
    def __init__(self, name: str, class_ptr: int, file_path: str, direct_sc: list, templates: list,
                 super_generics_map: dict, abstract: bool):
        super().__init__(0)

        self.name = name
        self.class_ptr = class_ptr
        self.file_path = file_path  # where this class is defined, avoiding conflict struct def'ns in non-export part
        self.name_with_path = util.class_name_with_path(self.name, self.file_path)
        self.abstract = abstract
        self.direct_superclasses = direct_sc
        self.mro: list = None  # Method resolution order, ranked from closest to farthest
        self.templates = templates  # list of Generic
        self.method_rank = []  # keep track of all method names in order | (name, method_t)

        # this dict records all callable methods in this class, including methods in its superclass
        # methods with same name must have the same id, i.e. overriding methods have the same id
        # note that in each NaiveDict, the key is the type of the most super method, real type is in the values
        self.methods = {}  # name: NaiveDict{func_type: (method_id, func_ptr, func_type)}
        self.fields = collections.OrderedDict()  # OrderedDict, name: (position, type)

        # records mapping for superclass
        # e.g. class A<K, V>, class B<X>(A<X, Object>) => {A: {"K": "X", "V": Object}}
        self.super_generics_map = super_generics_map

        self.initializers = []  # nodes that will be executed in __new__

    def type_name(self):
        return self.name

    def full_name(self):
        return self.name_with_path

    def has_field(self, name: str) -> bool:
        for mro_t in self.mro:
            if name in mro_t.fields:
                return True
        return False

    def find_field(self, name: str, lf) -> (int, Type):
        for mro_t in self.mro:
            if name in mro_t.fields:
                return mro_t.fields[name]
        raise errs.TplCompileError(f"Class {self.name} does not have field '{name}'. ", lf)

    def _find_method(self, name, arg_types, lf):
        if name in self.methods:
            poly: util.NaiveDict = self.methods[name]
            return find_closet_func(poly, arg_types, name, True, lambda poly_d, i: poly_d.values[i][2], lf)[1]

        raise errs.TplCompileError(f"Class {self.name} does not have method '{name}'. ", lf)

    def find_method(self, name: str, arg_types: list, lf) -> (int, int, MethodType):
        if name == "__new__":
            return self.find_local_method(name, arg_types, lf)
        else:
            return self._find_method(name, arg_types, lf)

    def find_local_method(self, name: str, arg_types: list, lf) -> (int, int, MethodType):
        """
        Returns only the matching method that is defined in this class, not in superclasses.

        The mechanism is that, for example, the signature of 'hash' defined in 'Object' is 'hash(this: *Object) int',
        but in 'String' is 'hash(this: *String) int'. Checking the param type of 'this' should determine
        the method's definition class.

        :param name:
        :param arg_types:
        :param lf:
        :return:
        """
        method_id, method_ptr, method_t = self._find_method(name, arg_types, lf)
        def_this_t = method_t.param_types[0].base
        if def_this_t != self:
            raise errs.TplCompileError(f"Cannot resolve local method {name}{arg_types[1:]}. ", lf)
        return method_id, method_ptr, method_t

    def strong_convertible(self, left_tar_type):
        if isinstance(left_tar_type, Generic):
            return self.strong_convertible(left_tar_type.max_t)
        if isinstance(left_tar_type, ClassType):
            real_t = left_tar_type
        elif isinstance(left_tar_type, Generic):
            real_t = left_tar_type.max_t
        elif isinstance(left_tar_type, GenericClassType):
            real_t = left_tar_type.base
        else:
            return super().strong_convertible(left_tar_type)

        for t in self.mro:
            if t == real_t:
                return True
        else:
            return super().strong_convertible(left_tar_type)

    def superclass_of(self, child_t: Type):
        if isinstance(child_t, ClassType):
            real_t = child_t
        elif isinstance(child_t, Generic):
            real_t = child_t.max_t
        elif isinstance(child_t, GenericClassType):
            real_t = child_t.base
        else:
            return False
        for t in real_t.mro:
            if self == t:
                return True
        return False

    def __eq__(self, other):
        return isinstance(other, ClassType) and self.name == other.name and self.file_path == other.file_path

    def __str__(self):
        return "ClassType(" + util.class_name_with_path(self.name, self.file_path) + ")"

    def __hash__(self):
        return self.name_with_path.__hash__()

    def __repr__(self):
        return self.__str__()


class GenericType(Type):
    def __init__(self, base, generics: dict):
        super().__init__(base.length)

        self.base = base
        self.generics = generics

    def __str__(self):
        return f"Gen{self.base}<{self.generics}>"

    def strong_convertible(self, left_tar_type):
        # print("000", self)
        # print("112", left_tar_type)
        # print(self.base.super_generics_map)
        if isinstance(left_tar_type, GenericType):
            if self.base.strong_convertible(left_tar_type.base):
                # if len(self.generics) == len(left_tar_type.generics):
                for key in self.generics:
                    if key in left_tar_type.generics:  # same T
                        if self.generics[key].strong_convertible(left_tar_type.generics[key]):
                            continue
                    super_gen = dict_find_key(self.base.super_generics_map[left_tar_type.base], key)
                    if super_gen is not None:  # class A<T0> {...}  class B<T1>(A<T1>) {...}
                        if self.generics[key].strong_convertible(left_tar_type.generics[super_gen]):
                            continue
                    return False
                return True
        return False


class GenericClassType(GenericType):
    def __init__(self, base: ClassType, generic: dict):
        super().__init__(base, generic)

    def type_name(self):
        return self.base.type_name()


class Generic(Type):
    def __init__(self, name: str, max_t: ClassType):
        super().__init__(max_t.length)

        self._name = name
        self.max_t = max_t

    def strong_convertible(self, left_tar_type):
        return self.max_t.strong_convertible(left_tar_type)

    def simple_name(self):
        return self._name

    def type_name(self):
        return self.max_t.type_name()

    def __eq__(self, other):
        return isinstance(other, Generic) and self._name == other._name

    def __str__(self):
        return f"{self._name}: {self.max_t}"


class ArrayType(Type):
    def __init__(self, ele_type: Type):
        super().__init__(util.PTR_LEN)

        self.ele_type = ele_type

    def strong_convertible(self, left_tar_type):
        if left_tar_type == TYPE_VOID_PTR:
            return True
        else:
            return super().strong_convertible(left_tar_type)

    def type_name(self):
        return self.ele_type.type_name() + "[]"

    def __str__(self):
        return f"{self.ele_type}[]"

    def __hash__(self):
        return hash(self.ele_type) + 1

    def __eq__(self, other):
        return isinstance(other, ArrayType) and self.ele_type == other.ele_type


def is_object_ptr(t: Type) -> bool:
    return isinstance(t, PointerType) and isinstance(t.base, (ClassType, GenericClassType))


def is_generic(t: Type) -> bool:
    if isinstance(t, PointerType):
        return is_generic(t.base)
    return isinstance(t, Generic)


def replace_generic_with_real(t: Type, real_generics: dict) -> Type:
    if isinstance(t, PointerType):
        return PointerType(replace_generic_with_real(t.base, real_generics))
    elif isinstance(t, Generic):
        return real_generics[t.simple_name()]
    else:
        raise errs.TplCompileError("Unexpected error.")


def index_in_generic_list(name: str, generics: list) -> int:
    for i in range(len(generics)):
        if name == generics[i].simple_name():
            return i
    return -1


def dict_find_key(d: dict, value):
    for key in d:
        if d[key] == value:
            return key
    return None


def function_poly_name(simple_name: str, params_t: list, method: bool) -> str:
    res = []
    begin = 1 if method else 0
    for i in range(begin, len(params_t)):
        res.append(params_t[i].type_name())
    return simple_name + "(" + ",".join(res) + ")"


def params_eq(ft1: FuncType, ft2: FuncType) -> bool:
    if len(ft1.param_types) == len(ft2.param_types):
        for i in range(len(ft1.param_types)):
            if ft1.param_types[i] != ft2.param_types[i]:
                return False
        return True
    return False


def params_eq_methods(ft1: MethodType, ft2: MethodType) -> bool:
    if len(ft1.param_types) == len(ft2.param_types):
        for i in range(1, len(ft1.param_types)):
            if ft1.param_types[i] != ft2.param_types[i]:
                return False
        return True
    return False


def func_eq_params(ft: FuncType, param_types: list) -> bool:
    if len(ft.param_types) == len(param_types):
        for i in range(len(param_types)):
            if ft.param_types[i] != param_types[i]:
                return False
        return True
    return False


def func_convertible_params(ft: FuncType, param_types: list) -> bool:
    if len(ft.param_types) == len(param_types):
        for i in range(len(param_types)):
            if not param_types[i].strong_convertible(ft.param_types[i]):
                return False
        return True
    return False


def method_convertible_params(ft: MethodType, param_types: list) -> bool:
    # print(ft.param_types)
    # print(param_types)
    if len(ft.param_types) == len(param_types):
        for i in range(1, len(param_types)):
            if not param_types[i].strong_convertible(ft.param_types[i]):
                return False
        return True
    return False


def get_class_type(t) -> ClassType:
    if isinstance(t, ClassType):
        return t
    if isinstance(t, GenericClassType):
        return t.base
    if isinstance(t, Generic):
        return t.max_t
    raise errs.TplCompileError("Not a class type.")


def type_distance(left_type, right_real_type):
    """
    Precondition: right_real_type.strong_convertible(left_type)

    :param left_type:
    :param right_real_type:
    :return:
    """
    if isinstance(left_type, PointerType) and isinstance(right_real_type, PointerType):
        if right_real_type == TYPE_VOID_PTR:  # NULL
            return 0
        left = get_class_type(left_type.base)
        right = get_class_type(right_real_type.base)
        for i in range(len(right.mro)):
            if left == right.mro[i]:
                # print(left, right.mro, i)
                return i

    return 0


def find_closet_func(poly: util.NaiveDict, arg_types: [Type], name: str, is_method: bool,
                     get_type_func, lf) -> (FuncType, object):
    """
    Returns the closet method.

    The closet means the minimum sum of distance.

    :param poly:
    :param arg_types:
    :param name: the simple name of function
    :param is_method:
    :param get_type_func: a function that extract the function type from a unit in poly dict
    :param lf:
    :return: anything that gets from the poly dict.
        usually (method_key_type, (method_id, method_ptr, method_type)) for method,
        (fn_type, (fn_type, fn_ptr)) for function
    """
    param_begin = 1 if is_method else 0
    matched = {}
    for i in range(len(poly)):
        # fn_t = poly.keys[i]
        tup = poly.values[i]
        # print(name, fn_t)
        fn_t: CallableType = get_type_func(poly, i)
        if len(arg_types) == len(fn_t.param_types):
            sum_dt = 0
            match = True
            for j in range(param_begin, len(arg_types)):
                arg = arg_types[j]
                param = fn_t.param_types[j]
                if arg.strong_convertible(param):
                    # print(arg, param, type_distance(arg, param))
                    sum_dt += type_distance(param, arg)
                else:
                    match = False
                    break
            if match:
                if sum_dt in matched:
                    raise errs.TplCompileError(
                        f"Ambiguous call: {function_poly_name(name, arg_types, is_method)}. ", lf)
                matched[sum_dt] = (fn_t, tup)
    min_dt = 65536
    min_tup = None
    for dt in matched:
        if dt < min_dt:
            min_dt = dt
            min_tup = matched[dt]
    if min_tup is None:
        raise errs.TplCompileError(f"Cannot resolve call: {function_poly_name(name, arg_types, is_method)}. ", lf)
    return min_tup


TYPE_INT = PrimitiveType("int", util.INT_LEN)
TYPE_FLOAT = PrimitiveType("float", util.FLOAT_LEN)
TYPE_CHAR = PrimitiveType("char", util.CHAR_LEN)
TYPE_BYTE = PrimitiveType("byte", 1)
TYPE_VOID = PrimitiveType("void", 0)

TYPE_CHAR_ARR = ArrayType(TYPE_CHAR)
TYPE_STRING_ARR = ArrayType(TYPE_CHAR_ARR)
TYPE_VOID_PTR = PointerType(TYPE_VOID)

PRIMITIVE_TYPES = {"int": TYPE_INT, "float": TYPE_FLOAT, "char": TYPE_CHAR, "byte": TYPE_BYTE, "void": TYPE_VOID}

NATIVE_FUNCTIONS = {
    "print_int": (1, NativeFuncType([TYPE_INT], TYPE_VOID)),
    "println_int": (2, NativeFuncType([TYPE_INT], TYPE_VOID)),
    "clock": (3, NativeFuncType([], TYPE_INT)),
    "print_char": (4, NativeFuncType([TYPE_CHAR], TYPE_VOID)),
    "println_char": (5, NativeFuncType([TYPE_CHAR], TYPE_VOID)),
    "print_float": (6, NativeFuncType([TYPE_FLOAT], TYPE_VOID)),
    "println_float": (7, NativeFuncType([TYPE_FLOAT], TYPE_VOID)),
    "print_str": (8, NativeFuncType([TYPE_CHAR_ARR], TYPE_VOID)),
    "println_str": (9, NativeFuncType([TYPE_CHAR_ARR], TYPE_VOID)),
    "malloc": (10, NativeFuncType([TYPE_INT], TYPE_VOID_PTR)),
    "free": (11, NativeFuncType([TYPE_VOID_PTR], TYPE_VOID)),
    "heap_array": (12, NativeFuncType([TYPE_INT, ArrayType(TYPE_INT)], TYPE_VOID_PTR)),
    "nat_cos": (13, NativeFuncType([TYPE_FLOAT], TYPE_FLOAT)),
    "nat_log": (14, NativeFuncType([TYPE_FLOAT], TYPE_FLOAT)),
    "print_byte": (15, NativeFuncType([TYPE_BYTE], TYPE_VOID)),
    "println_byte": (16, NativeFuncType([TYPE_BYTE], TYPE_VOID))
}
